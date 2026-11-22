"""Per-scene work: views (full frame, tiles), object mapping, zoomed crops, coverage.

Every image Claude looks at is a *view*: a region of the source file, resized.
work/scene-NN/views.json records each view's offset and scale, so a box drawn
on any view converts back to source pixels exactly.
"""

from __future__ import annotations

import math
import shutil
from pathlib import Path
from typing import Any

from .config import Book, read_json, write_json
from .geometry import area, clamp_box, containment, intersection, iou, pad_box, view_to_source
from .hebrew import normalize
from .imaging import OBJECT_COLOR, draw_boxes, fit_scale, open_rgb, resize, save_png, sha256
from .taxonomy import OBJECT_CODES

STAGES = ["mapping", "checking", "verifying", "classified", "done"]


# Views ------------------------------------------------------------------

def load_views(book: Book, sid: str) -> dict[str, Any]:
    return read_json(book.scene_work(sid) / "views.json", {}) or {}


def save_views(book: Book, sid: str, views: dict[str, Any]) -> None:
    write_json(book.scene_work(sid) / "views.json", views)


def _render_view(book: Book, sid: str, img, name: str, region: list[int], scale: float, kind: str, views: dict[str, Any], folder: str = "") -> dict[str, Any]:
    crop = img.crop(tuple(region))
    view = resize(crop, scale)
    rel_dir = book.scene_work(sid) / folder if folder else book.scene_work(sid)
    path = rel_dir / f"{name}.png"
    save_png(view, path)
    entry = {
        "file": book.rel(path),
        "kind": kind,
        "region": region,
        "offset": [region[0], region[1]],
        "scale": round(scale, 6),
        "view_size": [view.width, view.height],
    }
    views[name] = entry
    return entry


def to_source(book: Book, sid: str, view_name: str, box: list[float]) -> list[int]:
    views = load_views(book, sid)
    if view_name not in views:
        raise KeyError(f"Unknown view {view_name!r} for scene {sid}. Known: {', '.join(sorted(views))}")
    v = views[view_name]
    doc = read_json(book.scene_json(sid), {})
    w, h = doc["size_px"]
    return clamp_box(view_to_source(box, v["offset"], v["scale"]), w, h)


# Scan -------------------------------------------------------------------

def new_doc(book: Book, sid: str, path: Path, digest: str, size: tuple[int, int]) -> dict[str, Any]:
    return {
        "scene_id": sid,
        "source_file": book.rel(path),
        "sha256": digest,
        "size_px": list(size),
        "stage": "mapping",
        "reviewed_at_px": None,
        "coverage_pct": None,
        "summary": "",
        "objects": [],
        "scene_checks": {},
        "counts": [],
        "findings": [],
        "gaps_reviewed": [],
        "previous": None,
    }


def prepare(book: Book, sid: str, force: bool = False) -> tuple[str, dict[str, Any]]:
    """Make the full view and tiles. Returns (state, doc). state: skipped|new|changed|resumed."""
    path = book.scene_map()[sid]
    digest = sha256(path)
    doc_path = book.scene_json(sid)
    doc = read_json(doc_path)
    state = "new"
    if doc:
        if doc.get("sha256") == digest and not force:
            if doc.get("stage") == "done":
                return "skipped", doc
            if (book.scene_work(sid) / "views.json").is_file():
                return "resumed", doc
            state = "resumed"
        elif doc.get("sha256") != digest:
            history = book.work / "history"
            history.mkdir(parents=True, exist_ok=True)
            archived = history / f"scene-{sid}-{doc['sha256'][:12]}.json"
            write_json(archived, doc)
            state = "changed"
            prev_rel = book.rel(archived)
            doc = None
    img = open_rgb(path)
    work = book.scene_work(sid)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    if doc is None or force:
        old_prev = doc.get("previous") if doc else None
        doc = new_doc(book, sid, path, digest, img.size)
        doc["previous"] = prev_rel if state == "changed" else old_prev
    views: dict[str, Any] = {}
    scan = book.scan
    w, h = img.size
    _render_view(book, sid, img, "full", [0, 0, w, h], fit_scale(w, h, scan["view_max_side"]), "full", views)
    rows, cols = scan["tiles"][0], scan["tiles"][1]
    overlap = float(scan["tile_overlap"])
    tile_w = w / (cols - (cols - 1) * overlap) if cols > 1 else w
    tile_h = h / (rows - (rows - 1) * overlap) if rows > 1 else h
    for r in range(rows):
        for c in range(cols):
            x1 = c * tile_w * (1 - overlap)
            y1 = r * tile_h * (1 - overlap)
            region = clamp_box([x1, y1, x1 + tile_w, y1 + tile_h], w, h)
            rw, rh = region[2] - region[0], region[3] - region[1]
            scale = fit_scale(rw, rh, scan["view_max_side"])
            _render_view(book, sid, img, f"r{r + 1}c{c + 1}", region, scale, "tile", views, "tiles")
    save_views(book, sid, views)
    write_json(doc_path, doc)
    if not (work / "candidates.json").exists():
        write_json(work / "candidates.json", [])
    return state, doc


# Mapping ----------------------------------------------------------------

def _touches_tile_edge(view: dict[str, Any], box: list[float], width: int, height: int) -> bool:
    if view["kind"] != "tile":
        return False
    rx1, ry1, rx2, ry2 = view["region"]
    tol_x = (rx2 - rx1) * 0.02
    tol_y = (ry2 - ry1) * 0.02
    return (
        (box[0] - rx1 < tol_x and rx1 > 0)
        or (rx2 - box[2] < tol_x and rx2 < width)
        or (box[1] - ry1 < tol_y and ry1 > 0)
        or (ry2 - box[3] < tol_y and ry2 < height)
    )


def map_objects(book: Book, sid: str) -> dict[str, Any]:
    doc = read_json(book.scene_json(sid))
    if not doc:
        raise FileNotFoundError(f"Scene {sid} has not been scanned. Run `scene-audit scan --scene {sid}`.")
    views = load_views(book, sid)
    w, h = doc["size_px"]
    candidates = read_json(book.scene_work(sid) / "candidates.json", []) or []
    problems: list[str] = []
    items: list[dict[str, Any]] = []
    for index, cand in enumerate(candidates):
        view_name = cand.get("view", "full")
        if view_name not in views:
            problems.append(f"candidate {index}: unknown view {view_name!r}")
            continue
        box = cand.get("bbox")
        if not (isinstance(box, list) and len(box) == 4):
            problems.append(f"candidate {index}: bbox must be [x1, y1, x2, y2] in view pixels")
            continue
        src = clamp_box(view_to_source(box, views[view_name]["offset"], views[view_name]["scale"]), w, h)
        if area(src) <= 0:
            problems.append(f"candidate {index}: empty box after conversion")
            continue
        items.append(
            {
                "kind": cand.get("kind", "object"),
                "label": (cand.get("label") or "").strip(),
                "spec_ref": cand.get("spec_ref", ""),
                "note": cand.get("note", ""),
                "bbox": src,
                "partial": _touches_tile_edge(views[view_name], src, w, h),
                "sources": [view_name],
            }
        )
    threshold = float(book.scan["dedupe_iou"])
    merged: list[dict[str, Any]] = []
    for item in sorted(items, key=lambda i: -area(i["bbox"])):
        target = None
        for existing in merged:
            same = existing["kind"] == item["kind"] and normalize(existing["label"]) == normalize(item["label"])
            if not same:
                continue
            overlap_iou = iou(existing["bbox"], item["bbox"])
            contained = containment(existing["bbox"], item["bbox"])
            joined = (item["partial"] or existing["partial"]) and intersection(existing["bbox"], item["bbox"]) > 0
            if overlap_iou >= threshold or contained >= 0.6 or joined:
                target = existing
                break
        if target is None:
            merged.append(dict(item))
            continue
        a, b = target["bbox"], item["bbox"]
        target["bbox"] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
        target["partial"] = target["partial"] and item["partial"]
        target["sources"] = sorted(set(target["sources"]) | set(item["sources"]))
        for key in ("spec_ref", "note"):
            if not target.get(key) and item.get(key):
                target[key] = item[key]
    merged.sort(key=lambda i: (i["bbox"][1] // max(1, h // 6), i["bbox"][0]))
    old_objects = doc.get("objects", [])
    objects = []
    for number, item in enumerate(merged, start=1):
        obj = {
            "object_id": f"{sid}-{number:02d}",
            "kind": item["kind"],
            "label": item["label"],
            "spec_ref": item["spec_ref"],
            "bbox": item["bbox"],
            "found_in": item["sources"],
            "action": {"who": "", "does": "", "with": "", "toward": ""} if item["kind"] == "character" else None,
            "checks": {},
            "notes": item["note"],
        }
        for old in old_objects:
            if normalize(old.get("label", "")) == normalize(obj["label"]) and iou(old["bbox"], obj["bbox"]) >= 0.7:
                for key in ("action", "checks", "notes"):
                    if old.get(key):
                        obj[key] = old[key]
                break
        objects.append(obj)
    doc["objects"] = objects
    if doc.get("stage") == "mapping" and objects:
        doc["stage"] = "checking"
    write_json(book.scene_json(sid), doc)
    # A marked overview so the mapping itself can be checked by eye.
    img = open_rgb(book.root / doc["source_file"])
    scale = fit_scale(w, h, book.scan["view_max_side"])
    small = resize(img, scale)
    marked = draw_boxes(small, [(o["bbox"], o["object_id"].split("-")[-1], OBJECT_COLOR) for o in objects], scale)
    save_png(marked, book.scene_work(sid) / "objects-marked.png")
    duplicates = []
    for i, a in enumerate(objects):
        for b in objects[i + 1 :]:
            if a["kind"] == "character" and b["kind"] == "character" and normalize(a["label"]) == normalize(b["label"]):
                duplicates.append(f"{a['object_id']} and {b['object_id']} share the label {a['label']!r}: check DU")
    return {"objects": len(objects), "candidates": len(items), "problems": problems, "duplicates": duplicates, "expected_missing": expected_missing(book, sid, objects)}


def expected_missing(book: Book, sid: str, objects: list[dict[str, Any]]) -> list[str]:
    from .rules import load_rules

    rules = load_rules(book) or {}
    labels = {normalize(o["label"]) for o in objects}
    missing = []
    for scene in rules.get("scenes") or []:
        if str(scene.get("scene_id", "")).zfill(2) != sid and str(scene.get("scene_id", "")) != sid:
            continue
        for expected in scene.get("expected_objects") or []:
            if expected and not any(normalize(str(expected)) in label or label in normalize(str(expected)) for label in labels if label):
                missing.append(str(expected))
    return missing


# Crops ------------------------------------------------------------------

def _crop_scale(rw: int, rh: int, scan: dict[str, Any]) -> float:
    short, long = min(rw, rh), max(rw, rh)
    scale = max(1.0, scan["crop_min_short_side"] / short) if short else 1.0
    scale = min(scale, float(scan["crop_max_scale"]))
    if long * scale > scan["crop_max_long_side"]:
        scale = scan["crop_max_long_side"] / long
    return scale


def _split(region: list[int], max_side: int) -> list[list[int]]:
    rw, rh = region[2] - region[0], region[3] - region[1]
    cols = max(1, math.ceil(rw / max_side))
    rows = max(1, math.ceil(rh / max_side))
    if cols == 1 and rows == 1:
        return []
    parts = []
    pw, ph = rw / cols, rh / rows
    ox, oy = pw * 0.1, ph * 0.1
    for r in range(rows):
        for c in range(cols):
            parts.append(
                [
                    round(max(region[0], region[0] + c * pw - ox)),
                    round(max(region[1], region[1] + r * ph - oy)),
                    round(min(region[2], region[0] + (c + 1) * pw + ox)),
                    round(min(region[3], region[1] + (r + 1) * ph + oy)),
                ]
            )
    return parts


def make_crops(book: Book, sid: str) -> dict[str, Any]:
    doc = read_json(book.scene_json(sid))
    if not doc or not doc.get("objects"):
        raise ValueError(f"Scene {sid} has no mapped objects. Write candidates.json and run `scene-audit map --scene {sid}`.")
    img = open_rgb(book.root / doc["source_file"])
    w, h = img.size
    scan = book.scan
    views = load_views(book, sid)
    for name in [n for n, v in views.items() if v["kind"] in ("object", "context", "part", "gap")]:
        del views[name]
    for folder in ("crops", "gaps"):
        shutil.rmtree(book.scene_work(sid) / folder, ignore_errors=True)
    tasks = []
    for obj in doc["objects"]:
        oid = obj["object_id"]
        region = pad_box(obj["bbox"], scan["crop_padding"], w, h)
        rw, rh = region[2] - region[0], region[3] - region[1]
        scale = _crop_scale(rw, rh, scan)
        entry = _render_view(book, sid, img, oid, region, scale, "object", views, "crops")
        names = [oid]
        if scale < 1.0:
            for index, part in enumerate(_split(region, scan["crop_max_long_side"]), start=1):
                pw, ph = part[2] - part[0], part[3] - part[1]
                pname = f"{oid}-p{index}"
                _render_view(book, sid, img, pname, part, _crop_scale(pw, ph, scan), "part", views, "crops")
                views[pname]["object_id"] = oid
                names.append(pname)
        ctx_region = pad_box(obj["bbox"], scan["context_padding"], w, h)
        cw, ch = ctx_region[2] - ctx_region[0], ctx_region[3] - ctx_region[1]
        _render_view(book, sid, img, f"{oid}-ctx", ctx_region, fit_scale(cw, ch, scan["view_max_side"]), "context", views, "crops")
        views[oid]["object_id"] = oid
        views[f"{oid}-ctx"]["object_id"] = oid
        tasks.append({"object_id": oid, "label": obj["label"], "kind": obj["kind"], "alone": [views[n]["file"] for n in names], "context": views[f"{oid}-ctx"]["file"], "zoom": entry["scale"]})
    # Gap crops: grid cells that no object crop covers well.
    grid = int(scan["gap_grid"])
    covered = [pad_box(o["bbox"], scan["crop_padding"], w, h) for o in doc["objects"]]
    gaps = []
    for r in range(grid):
        for c in range(grid):
            cell = clamp_box([c * w / grid, r * h / grid, (c + 1) * w / grid, (r + 1) * h / grid], w, h)
            share = _covered_share(cell, covered, w, h)
            if share < 0.6:
                region = pad_box(cell, 0.10, w, h)
                rw, rh = region[2] - region[0], region[3] - region[1]
                name = f"gap-r{r + 1}c{c + 1}"
                _render_view(book, sid, img, name, region, _crop_scale(rw, rh, scan), "gap", views, "gaps")
                gaps.append({"view": name, "file": views[name]["file"], "covered_by_objects": round(share * 100)})
    save_views(book, sid, views)
    write_json(book.scene_work(sid) / "crop-tasks.json", {"objects": tasks, "gaps": gaps})
    return {"objects": len(tasks), "gaps": len(gaps), "tasks": tasks, "gap_views": gaps}


def _mask_cells(w: int, h: int, step: int) -> tuple[int, int]:
    return max(1, math.ceil(w / step)), max(1, math.ceil(h / step))


def _covered_share(region: list[int], boxes: list[list[int]], w: int, h: int) -> float:
    step = max(4, max(w, h) // 400)
    total = 0
    hit = 0
    for y in range(region[1], region[3], step):
        for x in range(region[0], region[2], step):
            total += 1
            if any(b[0] <= x < b[2] and b[1] <= y < b[3] for b in boxes):
                hit += 1
    return hit / total if total else 1.0


def coverage(book: Book, doc: dict[str, Any]) -> tuple[int, int | None]:
    """(coverage_pct, reviewed_at_px) from objects whose checks are all filled and gaps marked reviewed."""
    sid = doc["scene_id"]
    views = load_views(book, sid)
    w, h = doc["size_px"]
    boxes = []
    shorts = []
    for obj in doc.get("objects", []):
        checks = obj.get("checks") or {}
        if not all(code in checks for code in OBJECT_CODES):
            continue
        view = views.get(obj["object_id"])
        if not view:
            continue
        boxes.append(view["region"])
        shorts.append(min(view["view_size"]))
    for name in doc.get("gaps_reviewed", []):
        view = views.get(name)
        if view:
            boxes.append(view["region"])
            shorts.append(min(view["view_size"]))
    if not boxes:
        return 0, None
    return round(_covered_share([0, 0, w, h], boxes, w, h) * 100), min(shorts)

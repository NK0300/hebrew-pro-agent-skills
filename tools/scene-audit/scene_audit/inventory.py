"""Stage 1 and 2: inventory with hashes and format checks, plus a contact sheet."""

from __future__ import annotations

import csv
import math
import re
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .config import Book, read_json, write_json
from .imaging import font, image_size, open_rgb, sha256

FILENAME_RE = re.compile(r"[\w\-. ()֐-׿]+\.(?:png|jpe?g|webp|tiff?)", re.IGNORECASE)


def _format_issues(book: Book, width: int, height: int) -> list[str]:
    fmt = book.cfg["format"]
    issues: list[str] = []
    layout = fmt["layout"]
    if layout == "spread" and width <= height:
        issues.append("expected a landscape spread, file is portrait or square")
    if layout == "single" and width > height * 1.2:
        issues.append("expected a single page, file looks like a spread")
    want_w, want_h = fmt.get("width_px"), fmt.get("height_px")
    tol = float(fmt.get("tolerance_pct") or 0) / 100
    if want_w and want_h:
        want_ratio = want_w / want_h
        ratio = width / height
        if abs(ratio - want_ratio) / want_ratio > tol:
            issues.append(f"aspect {ratio:.3f} differs from spec {want_ratio:.3f}")
        if width < want_w * (1 - tol) or height < want_h * (1 - tol):
            issues.append(f"size {width}x{height} is below spec {want_w}x{want_h}")
    return issues


def _tracking_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        parts = []
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith(".xml") and (name.startswith("xl/worksheets/") or name == "xl/sharedStrings.xml"):
                    parts.append(archive.read(name).decode("utf-8", "replace"))
        return re.sub(r"<[^>]+>", " ", "\n".join(parts))
    return path.read_text(encoding="utf-8-sig", errors="replace")


def check_tracking(book: Book, current: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Find tracking-sheet references to files that are not the current renders."""
    names = {Path(info["source_file"]).name.lower() for info in current.values()}
    results = []
    for entry in book.cfg["paths"].get("tracking") or []:
        path = book.path(entry)
        if not path or not path.is_file():
            results.append({"sheet": str(entry), "problem": "sheet not found"})
            continue
        refs = sorted({m.group(0).strip() for m in FILENAME_RE.finditer(_tracking_text(path))})
        stale = [r for r in refs if Path(r).name.lower() not in names]
        unreferenced = sorted(n for n in names if n not in {Path(r).name.lower() for r in refs})
        results.append(
            {
                "sheet": book.rel(path),
                "references": len(refs),
                "missing_files": stale,
                "renders_not_in_sheet": unreferenced,
            }
        )
    return results


def contact_sheet(book: Book, entries: list[dict[str, Any]], target: Path, thumb: int = 360) -> Path | None:
    if not entries:
        return None
    cols = max(1, min(6, math.ceil(math.sqrt(len(entries)))))
    rows = math.ceil(len(entries) / cols)
    label_h = 34
    gap = 12
    sheet = Image.new("RGB", (cols * (thumb + gap) + gap, rows * (thumb + label_h + gap) + gap), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    fnt = font(18)
    for index, entry in enumerate(entries):
        img = open_rgb(book.root / entry["source_file"])
        img.thumbnail((thumb, thumb), Image.LANCZOS)
        col, row = index % cols, index // cols
        x = gap + col * (thumb + gap)
        y = gap + row * (thumb + label_h + gap)
        sheet.paste(img, (x + (thumb - img.width) // 2, y + (thumb - img.height) // 2))
        draw.text((x, y + thumb + 6), f"{entry['scene_id']}  {Path(entry['source_file']).name}"[:40], fill=(20, 20, 20), font=fnt)
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, quality=90)
    return target


def run(book: Book, make_contact_sheet: bool = True) -> dict[str, Any]:
    previous = read_json(book.work / "inventory.json", {}) or {}
    prev_scenes = previous.get("scenes", {})
    scenes: dict[str, dict[str, Any]] = {}
    for sid, path in book.scene_map().items():
        width, height = image_size(path)
        digest = sha256(path)
        old = prev_scenes.get(sid)
        if not old:
            change = "new"
        elif old.get("sha256") != digest:
            change = "changed"
        else:
            change = "unchanged"
        scenes[sid] = {
            "scene_id": sid,
            "source_file": book.rel(path),
            "size_px": [width, height],
            "orientation": "landscape" if width > height else ("portrait" if height > width else "square"),
            "bytes": path.stat().st_size,
            "sha256": digest,
            "change": change,
            "format_issues": _format_issues(book, width, height),
        }
    removed = sorted(set(prev_scenes) - set(scenes))
    data = {
        "book": book.cfg.get("book", ""),
        "scenes_dir": book.rel(book.scenes_dir),
        "count": len(scenes),
        "scenes": scenes,
        "removed": removed,
        "tracking": check_tracking(book, scenes),
    }
    write_json(book.work / "inventory.json", data)
    book.out.mkdir(parents=True, exist_ok=True)
    with (book.out / "inventory.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["scene_id", "source_file", "width_px", "height_px", "orientation", "sha256", "change", "format_issues"])
        for info in scenes.values():
            writer.writerow(
                [info["scene_id"], info["source_file"], *info["size_px"], info["orientation"], info["sha256"], info["change"], "; ".join(info["format_issues"])]
            )
    if make_contact_sheet:
        sheet = contact_sheet(book, list(scenes.values()), book.out / "contact-sheet.jpg")
        data["contact_sheet"] = book.rel(sheet) if sheet else None
        write_json(book.work / "inventory.json", data)
    return data


def describe(data: dict[str, Any]) -> str:
    lines = [f"{data['count']} scene(s) in {data['scenes_dir']}"]
    for info in data["scenes"].values():
        w, h = info["size_px"]
        flag = "" if not info["format_issues"] else "  !! " + "; ".join(info["format_issues"])
        lines.append(f"  {info['scene_id']:>4}  {Path(info['source_file']).name:<40} {w}x{h}  {info['change']}{flag}")
    if data["removed"]:
        lines.append("Removed since last inventory: " + ", ".join(data["removed"]))
    for sheet in data["tracking"]:
        if "problem" in sheet:
            lines.append(f"Tracking {sheet['sheet']}: {sheet['problem']}")
            continue
        lines.append(f"Tracking {sheet['sheet']}: {sheet['references']} reference(s)")
        for name in sheet["missing_files"]:
            lines.append(f"  !! points at a file that is not a current render: {name}")
        for name in sheet["renders_not_in_sheet"]:
            lines.append(f"  render not listed in the sheet: {name}")
    if data.get("contact_sheet"):
        lines.append(f"Contact sheet: {data['contact_sheet']}")
    return "\n".join(lines)

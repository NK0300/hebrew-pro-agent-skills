"""Findings: coordinate normalization, validation, second-pass packs, dismissed memory."""

from __future__ import annotations

from typing import Any

from .config import Book, read_json, write_json
from .geometry import clamp_box, iou, pad_box, valid_box, view_to_source
from .imaging import open_rgb
from .rules import known_sections
from .scene import _crop_scale, _render_view, coverage, load_views, save_views
from . import taxonomy as tx

FOUR_TAGS = ("type", "severity", "confidence", "fix_kind")


# Normalization ----------------------------------------------------------

def _convert(item: dict[str, Any], views: dict[str, Any], w: int, h: int) -> str | None:
    """If an item has view + view_bbox, set bbox in source px. Returns an error or None."""
    view_name = item.get("view") or item.get("crop")
    view_box = item.get("view_bbox") or item.get("crop_bbox")
    if item.get("bbox") or not view_name or not view_box:
        return None
    view = views.get(view_name)
    if not view:
        return f"unknown view {view_name!r}"
    item["bbox"] = clamp_box(view_to_source(view_box, view["offset"], view["scale"]), w, h)
    return None


def load_dismissed(book: Book) -> list[dict[str, Any]]:
    return read_json(book.work / "dismissed.json", []) or []


def remember_dismissal(book: Book, doc: dict[str, Any], finding: dict[str, Any], note: str = "") -> None:
    memory = load_dismissed(book)
    memory.append(
        {
            "sha256": doc["sha256"],
            "scene_id": doc["scene_id"],
            "finding_id": finding["finding_id"],
            "code": finding.get("code"),
            "bbox": finding.get("bbox"),
            "problem": finding.get("problem", ""),
            "note": note,
        }
    )
    write_json(book.work / "dismissed.json", memory)


def normalize_doc(book: Book, doc: dict[str, Any]) -> list[str]:
    sid = doc["scene_id"]
    views = load_views(book, sid)
    w, h = doc["size_px"]
    errors = []
    for finding in doc.get("findings", []):
        err = _convert(finding, views, w, h)
        if err:
            errors.append(f"{finding.get('finding_id', '?')}: {err}")
        finding.setdefault("status", "pending")
        finding.setdefault("verified_by_second_pass", False)
    for count in doc.get("counts", []):
        for index, inst in enumerate(count.get("instances", [])):
            err = _convert(inst, views, w, h)
            if err:
                errors.append(f"count {count.get('label', '?')} instance {index + 1}: {err}")
    memory = [m for m in load_dismissed(book) if m.get("sha256") == doc["sha256"]]
    for finding in doc.get("findings", []):
        if finding.get("status") != "pending" or not finding.get("bbox"):
            continue
        for mem in memory:
            if mem.get("code") == finding.get("code") and mem.get("bbox") and iou(mem["bbox"], finding["bbox"]) >= 0.5:
                finding["status"] = "dismissed"
                finding["auto_dismissed_from"] = mem["finding_id"]
                break
    pct, px = coverage(book, doc)
    doc["coverage_pct"] = pct
    doc["reviewed_at_px"] = px
    return errors


# Validation -------------------------------------------------------------

def validate_doc(book: Book, doc: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    sid = doc["scene_id"]
    w, h = doc["size_px"]
    sections = known_sections(book)
    object_ids = set()
    for obj in doc.get("objects", []):
        oid = obj.get("object_id", "?")
        if oid in object_ids:
            errors.append(f"{oid}: duplicate object_id")
        object_ids.add(oid)
        if obj.get("kind") not in tx.OBJECT_KINDS:
            errors.append(f"{oid}: kind must be one of {tx.OBJECT_KINDS}")
        if not valid_box(obj.get("bbox"), w, h):
            errors.append(f"{oid}: bbox outside the image or malformed")
        checks = obj.get("checks") or {}
        for code, value in checks.items():
            if code not in tx.OBJECT_CODES:
                errors.append(f"{oid}: check {code} is not an object-level code {tx.OBJECT_CODES}")
            if value not in tx.CHECK_VALUES:
                errors.append(f"{oid}: check {code}={value!r}; use {tx.CHECK_VALUES}")
        missing = [c for c in tx.OBJECT_CODES if c not in checks]
        if missing:
            warnings.append(f"{oid}: not checked yet for {', '.join(missing)}")
        if obj.get("kind") == "character":
            action = obj.get("action") or {}
            if not action.get("who") or not action.get("does"):
                warnings.append(f"{oid}: character has no action sentence (who · does · with · toward)")
        for code, value in checks.items():
            if value == "fail" and not any(f.get("object_id") == oid and f.get("code") == code for f in doc.get("findings", [])):
                errors.append(f"{oid}: check {code} is fail but no finding records it")
    for code, value in (doc.get("scene_checks") or {}).items():
        if code not in tx.SCENE_CODES:
            errors.append(f"scene_checks: {code} is not a scene-level code {tx.SCENE_CODES}")
        if value not in tx.CHECK_VALUES:
            errors.append(f"scene_checks: {code}={value!r}; use {tx.CHECK_VALUES}")
    seen = set()
    for finding in doc.get("findings", []):
        fid = finding.get("finding_id", "?")
        if fid in seen:
            errors.append(f"{fid}: duplicate finding_id")
        seen.add(fid)
        if not str(fid).startswith(f"{sid}-F"):
            errors.append(f"{fid}: finding_id must look like {sid}-F01")
        for tag in FOUR_TAGS:
            if not finding.get(tag):
                errors.append(f"{fid}: missing {tag}. A finding without all four tags is not written.")
        checks = {
            "code": tx.ALL_CODES,
            "type": tx.TYPES,
            "severity": tx.SEVERITIES,
            "confidence": tx.CONFIDENCES,
            "fix_kind": tx.FIX_KINDS,
            "status": tx.STATUSES,
        }
        for key, allowed in checks.items():
            value = finding.get(key)
            if value and value not in allowed:
                errors.append(f"{fid}: {key}={value!r}; use {allowed}")
        if not finding.get("code"):
            errors.append(f"{fid}: missing code")
        if finding.get("type") == "spec_violation":
            ref = str(finding.get("spec_ref") or "")
            if not ref:
                errors.append(f"{fid}: a spec_violation must cite spec_ref")
            elif sections and ref not in sections:
                errors.append(f"{fid}: spec_ref {ref} is not a section of the production document")
        if finding.get("confidence") == "certain" and not finding.get("verified_by_second_pass"):
            errors.append(f"{fid}: confidence 'certain' only after the second pass confirmed it")
        if not valid_box(finding.get("bbox"), w, h):
            errors.append(f"{fid}: bbox missing, malformed or outside {w}x{h}")
        if finding.get("object_id") and finding["object_id"] not in object_ids:
            errors.append(f"{fid}: object_id {finding['object_id']} does not exist")
        for key in ("where", "problem", "fix_instruction"):
            if not finding.get(key):
                errors.append(f"{fid}: missing {key}")
    for count in doc.get("counts", []):
        label = count.get("label", "?")
        result = count.get("result")
        if result not in tx.TAG_RESULTS:
            errors.append(f"count {label}: result must be one of {tx.TAG_RESULTS}")
        instances = count.get("instances", [])
        for index, inst in enumerate(instances, start=1):
            if not valid_box(inst.get("bbox"), w, h):
                errors.append(f"count {label}: instance {index} has no valid bbox")
        expected = count.get("expected")
        if result == "correct" and expected is not None and len(instances) != expected:
            errors.append(f"count {label}: marked correct but {len(instances)} boxes vs tag {expected}")
        if result == "wrong" and expected is not None and len(instances) == expected:
            errors.append(f"count {label}: marked wrong but boxes equal the tag ({expected})")
    if doc.get("coverage_pct") is not None and doc["coverage_pct"] < 90:
        warnings.append(f"coverage {doc['coverage_pct']}%: review the remaining gap views or note what was not checked")
    return errors, warnings


def run_validate(book: Book, sid: str, write: bool = True) -> tuple[list[str], list[str], dict[str, Any]]:
    doc = read_json(book.scene_json(sid))
    if not doc:
        return [f"scene {sid} has not been scanned"], [], {}
    errors = normalize_doc(book, doc)
    more, warnings = validate_doc(book, doc)
    errors += more
    if write:
        write_json(book.scene_json(sid), doc)
    return errors, warnings, doc


# Second pass ------------------------------------------------------------

def verify_pack(book: Book, sid: str) -> dict[str, Any]:
    errors, _, doc = run_validate(book, sid)
    doc = read_json(book.scene_json(sid))
    img = open_rgb(book.root / doc["source_file"])
    w, h = img.size
    views = load_views(book, sid)
    tasks = []
    for finding in doc.get("findings", []):
        if finding.get("verified_by_second_pass") or finding.get("status") == "dismissed" or not finding.get("bbox"):
            continue
        fid = finding["finding_id"]
        region = pad_box(finding["bbox"], 0.6, w, h)
        rw, rh = region[2] - region[0], region[3] - region[1]
        name = f"verify-{fid}"
        _render_view(book, sid, img, name, region, _crop_scale(rw, rh, book.scan), "verify", views, "verify")
        ctx = pad_box(finding["bbox"], 2.0, w, h)
        cw, ch = ctx[2] - ctx[0], ctx[3] - ctx[1]
        _render_view(book, sid, img, f"{name}-ctx", ctx, min(1.0, book.scan["view_max_side"] / max(cw, ch)), "verify", views, "verify")
        tasks.append(
            {
                "finding_id": fid,
                "image": views[name]["file"],
                "context_image": views[f"{name}-ctx"]["file"],
                "look_for": tx.CODE_QUESTIONS.get(finding.get("code", ""), "Is anything wrong in this region?"),
                "where": finding.get("where", ""),
            }
        )
    save_views(book, sid, views)
    pack = {
        "scene_id": sid,
        "instructions": (
            "Independent second pass. You have not seen the first reviewer's reasoning. "
            "For each task, open image and context_image, look for what look_for asks, and answer with "
            "verdict confirmed (there is a real defect of that kind here), rejected (there is not), or "
            "uncertain (too small or unclear to say), plus one sentence describing what you see."
        ),
        "answer_file": book.rel(book.scene_work(sid) / "verify" / "answers.json"),
        "answer_format": {"<finding_id>": {"verdict": "confirmed|rejected|uncertain", "seen": "..."}},
        "tasks": tasks,
    }
    write_json(book.scene_work(sid) / "verify" / "tasks.json", pack)
    if not (book.scene_work(sid) / "verify" / "answers.json").exists():
        write_json(book.scene_work(sid) / "verify" / "answers.json", {})
    if doc.get("stage") in ("mapping", "checking"):
        doc["stage"] = "verifying"
        write_json(book.scene_json(sid), doc)
    return {"tasks": len(tasks), "file": book.rel(book.scene_work(sid) / "verify" / "tasks.json"), "validation_errors": errors}


def verify_apply(book: Book, sid: str) -> dict[str, int]:
    doc = read_json(book.scene_json(sid))
    answers = read_json(book.scene_work(sid) / "verify" / "answers.json", {}) or {}
    stats = {"confirmed": 0, "downgraded": 0, "unanswered": 0}
    for finding in doc.get("findings", []):
        if finding.get("verified_by_second_pass") or finding.get("status") == "dismissed":
            continue
        answer = answers.get(finding["finding_id"])
        if not answer:
            stats["unanswered"] += 1
            continue
        verdict = str(answer.get("verdict", "")).lower()
        finding["second_pass"] = {"verdict": verdict, "seen": answer.get("seen", "")}
        if verdict == "confirmed":
            finding["verified_by_second_pass"] = True
            stats["confirmed"] += 1
        else:
            finding["verified_by_second_pass"] = False
            finding["confidence"] = "verify"
            stats["downgraded"] += 1
    if stats["unanswered"] == 0 and doc.get("stage") in ("checking", "verifying"):
        doc["stage"] = "classified"
    write_json(book.scene_json(sid), doc)
    return stats

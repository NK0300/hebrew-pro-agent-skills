"""Stage 9: all outputs are built from work/scene-*.json, never the other way round."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from .config import SEVERITY_RANK, Book, read_json
from .findings import run_validate
from .geometry import pad_box
from .imaging import COUNT_COLOR, SEVERITY_COLORS, draw_boxes, fit_scale, open_rgb, resize, save_png
from . import taxonomy as tx

DECISION_FIELDS = ["finding_id", "scene_id", "severity", "type", "code", "where", "problem", "fix_kind", "fix_instruction", "status", "above_threshold", "decision", "note"]
DEFECT_FIELDS = ["finding_id", "source_file", "x1", "y1", "x2", "y2", "severity", "type", "code", "confidence", "where", "problem", "fix_kind", "fix_instruction", "status"]


def load_docs(book: Book) -> list[dict[str, Any]]:
    docs = []
    for sid in sorted(book.scene_map()):
        if book.scene_json(sid).is_file():
            run_validate(book, sid)  # normalize coordinates, coverage, dismissed memory
            docs.append(read_json(book.scene_json(sid)))
    return docs


def is_defect(f: dict[str, Any]) -> bool:
    """Counted as a defect: not dismissed, not a suggestion or spec conflict, not 'verify'."""
    return f.get("status") != "dismissed" and f.get("type") == "spec_violation" and f.get("confidence") in ("certain", "likely")


def needs_owner(f: dict[str, Any], threshold_rank: int) -> bool:
    """In the owner's queue: at or above the fix threshold, spec conflicts, and AU/SY questions."""
    if f.get("type") == "spec_conflict" or f.get("code") in ("AU", "SY"):
        return True
    if f.get("type") == "suggestion":
        return False
    return SEVERITY_RANK.get(f.get("severity", "minor"), 9) <= threshold_rank


def _sort_key(f: dict[str, Any]) -> tuple[int, str]:
    return (SEVERITY_RANK.get(f.get("severity", "minor"), 9), f.get("finding_id", ""))


def _he(f: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(f)
    out["scene_id"] = doc["scene_id"]
    out["source_file"] = doc["source_file"]
    out["code_he"] = tx.CODE_NAMES_HE.get(f.get("code", ""), f.get("code", ""))
    out["type_he"] = tx.TYPE_HE.get(f.get("type", ""), f.get("type", ""))
    out["severity_he"] = tx.SEVERITY_HE.get(f.get("severity", ""), f.get("severity", ""))
    out["confidence_he"] = tx.CONFIDENCE_HE.get(f.get("confidence", ""), f.get("confidence", ""))
    out["fix_he"] = tx.FIX_HE.get(f.get("fix_kind", ""), f.get("fix_kind", ""))
    out["status_he"] = tx.STATUS_HE.get(f.get("status", ""), f.get("status", ""))
    return out


def marked_pages(book: Book, docs: list[dict[str, Any]]) -> dict[str, str]:
    out = {}
    for doc in docs:
        boxes = []
        for f in doc.get("findings", []):
            if f.get("status") == "dismissed" or not f.get("bbox"):
                continue
            boxes.append((f["bbox"], f["finding_id"].split("-")[-1], SEVERITY_COLORS.get(f.get("severity"), (90, 90, 90))))
        for count in doc.get("counts", []):
            for index, inst in enumerate(count.get("instances", []), start=1):
                if inst.get("bbox"):
                    boxes.append((inst["bbox"], str(index), COUNT_COLOR))
        img = open_rgb(book.root / doc["source_file"])
        scale = fit_scale(img.width, img.height, 4096)
        marked = draw_boxes(resize(img, scale), boxes, scale)
        path = book.out / "marked" / f"scene-{doc['scene_id']}.png"
        save_png(marked, path)
        out[doc["scene_id"]] = path.relative_to(book.out).as_posix()
    return out


def write_defects(book: Book, docs: list[dict[str, Any]]) -> int:
    rows = 0
    with (book.out / "defects.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=DEFECT_FIELDS)
        writer.writeheader()
        for doc in docs:
            w, h = doc["size_px"]
            for f in sorted(doc.get("findings", []), key=_sort_key):
                if not is_defect(f) or f.get("status") == "fixed_verified":
                    continue
                x1, y1, x2, y2 = pad_box(f["bbox"], 0.10, w, h)
                writer.writerow(
                    {
                        "finding_id": f["finding_id"],
                        "source_file": doc["source_file"],
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        **{k: f.get(k, "") for k in ("severity", "type", "code", "confidence", "where", "problem", "fix_kind", "fix_instruction", "status")},
                    }
                )
                rows += 1
    return rows


def write_decisions(book: Book, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = book.out / "decisions.csv"
    typed: dict[str, dict[str, str]] = {}
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("decision") or row.get("note"):
                    typed[row["finding_id"]] = {"decision": row.get("decision", ""), "note": row.get("note", "")}
    threshold = SEVERITY_RANK[book.cfg["fix_threshold"]]
    queue = []
    for doc in docs:
        for f in sorted(doc.get("findings", []), key=_sort_key):
            if f.get("status") != "pending":
                continue
            row = {k: f.get(k, "") for k in DECISION_FIELDS if k in f}
            row["scene_id"] = doc["scene_id"]
            row["above_threshold"] = "yes" if needs_owner(f, threshold) else "no"
            row.update(typed.get(f["finding_id"], {"decision": "", "note": ""}))
            queue.append(row)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=DECISION_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(queue)
    return queue


def action_sentence(action: dict[str, Any] | None) -> str:
    if not action:
        return ""
    parts = [action.get("who", ""), action.get("does", "")]
    if action.get("with"):
        parts.append("עם " + action["with"] if not action["with"].startswith("עם") else action["with"])
    if action.get("toward"):
        parts.append("מול " + action["toward"] if not action["toward"].startswith(("מול", "אל", "ל")) else action["toward"])
    return " · ".join(p for p in parts if p)


def write_scenes_md(book: Book, docs: list[dict[str, Any]]) -> None:
    lines = [f"# תיאור הסצנות{(' — ' + book.cfg['book']) if book.cfg.get('book') else ''}", ""]
    for doc in docs:
        lines.append(f"## סצנה {doc['scene_id']}")
        lines.append("")
        if doc.get("summary"):
            lines.append(doc["summary"])
            lines.append("")
        resolution = f" · נבדק בחיתוכים של לפחות {doc['reviewed_at_px']} פיקסלים" if doc.get("reviewed_at_px") else " · עוד לא נבדק בחיתוכים"
        lines.append(f"קובץ: `{doc['source_file']}` · כיסוי: {doc.get('coverage_pct') or 0}%{resolution}")
        lines.append("")
        characters = [o for o in doc.get("objects", []) if o.get("kind") == "character"]
        others = [o for o in doc.get("objects", []) if o.get("kind") != "character"]
        if characters:
            lines.append("**דמויות**")
            lines.append("")
            for obj in characters:
                sentence = action_sentence(obj.get("action")) or "(הפעולה עוד לא תוארה)"
                lines.append(f"- `{obj['object_id']}` {sentence}")
            lines.append("")
        if others:
            lines.append("**אובייקטים**")
            lines.append("")
            for obj in others:
                note = f" — {obj['notes']}" if obj.get("notes") else ""
                lines.append(f"- `{obj['object_id']}` {obj.get('label', '')}{note}")
            lines.append("")
    (book.out / "scenes.md").write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")


def write_prompt_block(book: Book, docs: list[dict[str, Any]]) -> None:
    codes = Counter()
    rerender: list[str] = []
    for doc in docs:
        for f in doc.get("findings", []):
            if not is_defect(f):
                continue
            codes[f["code"]] += 1
            if f.get("fix_kind") == "rerender" or f.get("status") == "rerender":
                rerender.append(f"- סצנה {doc['scene_id']}: {f.get('fix_instruction', '')}")
    lines = ["# בלוק פרומפט למניעת חזרה", "", "להדביק בסוף כל פרומפט רינדור של הספר.", ""]
    if codes:
        lines.append("## כללים כלליים")
        lines.append("")
        for code, _ in codes.most_common():
            lines.append(f"- {tx.PREVENTION_HE.get(code, '')}")
        lines.append("")
    if rerender:
        lines.append("## הוראות לרינדור מחדש")
        lines.append("")
        lines.extend(rerender)
        lines.append("")
    if not codes and not rerender:
        lines.append("אין פגמים פתוחים, ואין מה להוסיף לפרומפט.")
        lines.append("")
    (book.out / "prompt-block.md").write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")


def build(book: Book) -> dict[str, Any]:
    book.out.mkdir(parents=True, exist_ok=True)
    docs = load_docs(book)
    inventory = read_json(book.work / "inventory.json", {}) or {}
    marked = marked_pages(book, docs)
    defects = write_defects(book, docs)
    queue = write_decisions(book, docs)
    write_scenes_md(book, docs)
    write_prompt_block(book, docs)

    all_findings = [_he(f, d) for d in docs for f in sorted(d.get("findings", []), key=_sort_key)]
    live = [f for f in all_findings if f.get("status") != "dismissed"]
    critical = [f for f in live if is_defect(f) and f.get("severity") == "critical"]
    other = [f for f in live if is_defect(f) and f.get("severity") != "critical"]
    to_verify = [f for f in live if f.get("confidence") == "verify" and f.get("type") != "suggestion"]
    conflicts = [f for f in live if f.get("type") == "spec_conflict"]
    suggestions = [f for f in live if f.get("type") == "suggestion"]
    tags: dict[str, list[dict[str, Any]]] = {r: [] for r in tx.TAG_RESULTS}
    for doc in docs:
        for count in doc.get("counts", []):
            item = dict(count)
            item["scene_id"] = doc["scene_id"]
            item["found"] = len(count.get("instances", []))
            tags.setdefault(count.get("result", "unconfirmed"), []).append(item)
    scenes_total = len(book.scene_map())
    not_done = sorted(set(book.scene_map()) - {d["scene_id"] for d in docs if d.get("stage") in ("classified", "done")})
    env = Environment(loader=PackageLoader("scene_audit", "templates"), autoescape=select_autoescape(["html", "j2"]))
    html = env.get_template("report.html.j2").render(
        book=book.cfg.get("book", ""),
        docs=docs,
        marked=marked,
        critical=critical,
        other=other,
        to_verify=to_verify,
        conflicts=conflicts,
        suggestions=suggestions,
        tags=tags,
        tag_he=tx.TAG_RESULT_HE,
        sev_he=tx.SEVERITY_HE,
        fix_he=tx.FIX_HE,
        queue=[q for q in queue if q["above_threshold"] == "yes"],
        threshold_he=tx.SEVERITY_HE[book.cfg["fix_threshold"]],
        scenes_total=scenes_total,
        not_done=not_done,
        format_issues={sid: info["format_issues"] for sid, info in (inventory.get("scenes") or {}).items() if info.get("format_issues")},
        defect_count=len(critical) + len(other),
        contact_sheet=Path(inventory["contact_sheet"]).name if inventory.get("contact_sheet") else None,
    )
    (book.out / "report.html").write_text(html, encoding="utf-8")
    return {
        "scenes": len(docs),
        "defects": len(critical) + len(other),
        "critical": len(critical),
        "verify": len(to_verify),
        "conflicts": len(conflicts),
        "suggestions": len(suggestions),
        "decisions_pending": len(queue),
        "defects_csv_rows": defects,
        "not_done": not_done,
    }

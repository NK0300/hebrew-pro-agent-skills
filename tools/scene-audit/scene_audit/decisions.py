"""Stages 10 and 11: the owner's decisions, dismissed memory, and recheck after a re-render."""

from __future__ import annotations

import csv
from typing import Any

from .config import Book, read_json, write_json
from .findings import remember_dismissal
from .geometry import iou
from .report import needs_owner
from . import taxonomy as tx


def _find(book: Book, finding_id: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    sid = finding_id.split("-F")[0]
    doc = read_json(book.scene_json(sid))
    if not doc:
        raise KeyError(f"No scene {sid} for finding {finding_id}")
    for finding in doc.get("findings", []):
        if finding.get("finding_id") == finding_id:
            return sid, doc, finding
    raise KeyError(f"Finding {finding_id} not found in scene {sid}")


def set_decision(book: Book, finding_id: str, decision: str, note: str = "") -> str:
    status = tx.DECISION_ALIASES.get(decision.strip().lower())
    if not status:
        raise ValueError(f"Unknown decision {decision!r}. Use ok, local, rerender (or תקין, מקומי, רינדור).")
    sid, doc, finding = _find(book, finding_id)
    finding["status"] = status
    if note:
        finding["owner_note"] = note
    if status == "dismissed":
        remember_dismissal(book, doc, finding, note)
    write_json(book.scene_json(sid), doc)
    return status


def apply_csv(book: Book) -> dict[str, int]:
    path = book.out / "decisions.csv"
    if not path.is_file():
        raise FileNotFoundError("out/decisions.csv does not exist. Run `scene-audit report` first.")
    stats = {"applied": 0, "skipped": 0}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        decision = (row.get("decision") or "").strip()
        if not decision:
            stats["skipped"] += 1
            continue
        set_decision(book, row["finding_id"], decision, (row.get("note") or "").strip())
        stats["applied"] += 1
    return stats


def queue(book: Book, threshold_only: bool = True) -> list[dict[str, Any]]:
    from .config import SEVERITY_RANK

    limit = SEVERITY_RANK[book.cfg["fix_threshold"]]
    items = []
    for sid in sorted(book.scene_map()):
        doc = read_json(book.scene_json(sid))
        if not doc:
            continue
        for finding in doc.get("findings", []):
            if finding.get("status") != "pending":
                continue
            above = needs_owner(finding, limit)
            if threshold_only and not above:
                continue
            items.append({"scene_id": sid, **finding})
    items.sort(key=lambda f: (SEVERITY_RANK.get(f.get("severity", "minor"), 9), f["finding_id"]))
    return items


def recheck(book: Book, sid: str) -> dict[str, Any]:
    doc = read_json(book.scene_json(sid))
    if not doc:
        raise FileNotFoundError(f"Scene {sid} has not been scanned")
    if not doc.get("previous"):
        raise ValueError(f"Scene {sid} has no previous version to compare. It was never re-rendered after a scan.")
    old = read_json(book.root / doc["previous"])
    old_findings = [f for f in old.get("findings", []) if f.get("status") != "dismissed" and f.get("type") != "suggestion"]
    new_findings = [f for f in doc.get("findings", []) if f.get("status") != "dismissed" and f.get("type") != "suggestion"]
    matched_new: set[str] = set()
    remaining, closed = [], []
    for of in old_findings:
        best = None
        for nf in new_findings:
            if nf["finding_id"] in matched_new or nf.get("code") != of.get("code"):
                continue
            if of.get("bbox") and nf.get("bbox") and iou(of["bbox"], nf["bbox"]) >= 0.3:
                best = nf
                break
        if best:
            matched_new.add(best["finding_id"])
            remaining.append({"old": of["finding_id"], "new": best["finding_id"], "problem": best.get("problem", "")})
        else:
            closed.append({"old": of["finding_id"], "problem": of.get("problem", "")})
    new = [{"new": f["finding_id"], "problem": f.get("problem", "")} for f in new_findings if f["finding_id"] not in matched_new]
    result = {"scene_id": sid, "previous": doc["previous"], "closed": closed, "remaining": remaining, "new": new}
    doc["recheck"] = result
    write_json(book.scene_json(sid), doc)
    lines = [f"# בדיקה חוזרת: סצנה {sid}", "", f"השוואה מול `{doc['previous']}`.", ""]
    for title, key, field in (("נסגרו", "closed", "old"), ("נשארו", "remaining", "new"), ("חדשים", "new", "new")):
        lines.append(f"## {title} ({len(result[key])})")
        lines.append("")
        for item in result[key]:
            lines.append(f"- `{item[field]}` {item['problem']}")
        if not result[key]:
            lines.append("- אין")
        lines.append("")
    book.out.mkdir(parents=True, exist_ok=True)
    (book.out / f"recheck-{sid}.md").write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return result

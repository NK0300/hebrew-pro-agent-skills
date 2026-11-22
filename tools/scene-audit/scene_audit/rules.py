"""Stage 3: production document -> spec.txt with section numbers -> rules.yaml.

The script extracts text and section numbers. Claude reads spec.txt and fills
rules.yaml; every rule keeps the section it came from. The owner approves the
file once with `scene-audit rules --approve`.
"""

from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path
from typing import Any

import yaml

from .config import Book, read_json, write_json
from . import hebrew

SPEC_EXTS = {".md", ".markdown", ".txt", ".docx", ".pdf"}
SECTION_RE = re.compile(r"^\s*(?:#{1,6}\s*)?(?:סעיף\s*|section\s*|§\s*)?(\d+(?:\.\d+){0,4})[.)]?\s+\S", re.IGNORECASE)

RULES_TEMPLATE: dict[str, Any] = {
    "approved": False,
    "spec_sha256": "",
    "source_files": [],
    "characters": [
        {
            "name": "",
            "spec_ref": "",
            "age_or_role": "",
            "id_marks": [],
            "color_family": "",
            "proportions": "",
        }
    ],
    "style": [{"rule": "", "spec_ref": ""}],
    "forbidden": [{"rule": "", "spec_ref": ""}],
    "safety": [{"rule": "", "spec_ref": ""}],
    "audience": [{"rule": "", "spec_ref": ""}],
    "find_tags": [{"scene_id": "", "label": "", "expected": 0, "spec_ref": ""}],
    "words": [{"word": "", "scene_id": "", "item": "", "color": "", "spec_ref": ""}],
    "spreads": [{"rule": "", "spec_ref": ""}],
    "scenes": [{"scene_id": "", "must_show": "", "expected_objects": [], "spec_ref": ""}],
    "format": {"layout": "", "spec_ref": ""},
}


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(entity, char)
    return text


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError("PDF spec needs pypdf: pip install pypdf (or pip install -e .[pdf])") from exc
    reader = PdfReader(str(path))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        pages.append(f"[page {number}]\n{page.extract_text() or ''}")
    return "\n".join(pages)


def read_spec_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _docx_text(path)
    if suffix == ".pdf":
        return _pdf_text(path)
    return path.read_text(encoding="utf-8-sig", errors="replace")


def spec_files(book: Book) -> list[Path]:
    folder = book.spec_dir
    if folder.is_file():
        return [folder]
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in SPEC_EXTS)


def extract(book: Book) -> dict[str, Any]:
    files = spec_files(book)
    if not files:
        raise FileNotFoundError(
            f"No production document in {book.rel(book.spec_dir)}. The audit needs it; without it there is only opinion."
        )
    out_lines: list[str] = []
    sections: dict[str, dict[str, Any]] = {}
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.read_bytes())
        out_lines.append(f"=== {book.rel(path)} ===")
        for raw in read_spec_file(path).splitlines():
            line = raw.rstrip()
            out_lines.append(line)
            match = SECTION_RE.match(line)
            if match and match.group(1) not in sections:
                sections[match.group(1)] = {"line": len(out_lines), "title": line.strip().lstrip("#").strip()[:120], "file": book.rel(path)}
    book.work.mkdir(parents=True, exist_ok=True)
    (book.work / "spec.txt").write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    meta = {"spec_sha256": digest.hexdigest(), "source_files": [book.rel(p) for p in files], "sections": sections}
    write_json(book.work / "spec-sections.json", meta)
    rules_path = book.work / "rules.yaml"
    if not rules_path.exists():
        template = dict(RULES_TEMPLATE)
        template["spec_sha256"] = meta["spec_sha256"]
        template["source_files"] = meta["source_files"]
        rules_path.write_text(
            "# Fill from work/spec.txt. Every rule keeps spec_ref = the section number it came from.\n"
            "# The owner approves once: scene-audit rules --approve\n"
            + yaml.safe_dump(template, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    return meta


def load_rules(book: Book) -> dict[str, Any] | None:
    path = book.work / "rules.yaml"
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def known_sections(book: Book) -> set[str]:
    meta = read_json(book.work / "spec-sections.json", {}) or {}
    return set(meta.get("sections", {}))


def _walk_refs(node: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "spec_ref" and value:
                refs.append(str(value))
            else:
                refs.extend(_walk_refs(value))
    elif isinstance(node, list):
        for item in node:
            refs.extend(_walk_refs(item))
    return refs


def check_rules(book: Book) -> list[str]:
    rules = load_rules(book)
    if rules is None:
        return ["work/rules.yaml is missing. Run `scene-audit rules` first."]
    problems = []
    sections = known_sections(book)
    for ref in _walk_refs(rules):
        if sections and ref not in sections:
            problems.append(f"spec_ref {ref} is not a section number found in the production document")
    meta = read_json(book.work / "spec-sections.json", {}) or {}
    if meta.get("spec_sha256") and rules.get("spec_sha256") and meta["spec_sha256"] != rules["spec_sha256"]:
        problems.append("the production document changed after rules.yaml was written. Re-read it and approve again.")
    return problems


def approve(book: Book) -> list[str]:
    problems = check_rules(book)
    hard = [p for p in problems if "missing" in p]
    if hard:
        return hard
    path = book.work / "rules.yaml"
    rules = load_rules(book) or {}
    meta = read_json(book.work / "spec-sections.json", {}) or {}
    rules["approved"] = True
    rules["spec_sha256"] = meta.get("spec_sha256", rules.get("spec_sha256", ""))
    path.write_text(yaml.safe_dump(rules, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return problems


def is_approved(book: Book) -> bool:
    rules = load_rules(book)
    if not rules or not rules.get("approved"):
        return False
    meta = read_json(book.work / "spec-sections.json", {}) or {}
    return not meta.get("spec_sha256") or rules.get("spec_sha256") == meta["spec_sha256"]


def spec_search(book: Book, term: str) -> list[tuple[int, str]]:
    path = book.work / "spec.txt"
    if not path.is_file():
        extract(book)
    lines = path.read_text(encoding="utf-8").splitlines()
    return hebrew.search(term, lines)

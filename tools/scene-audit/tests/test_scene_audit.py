"""End-to-end and unit tests on synthetic renders. Run: python -m unittest discover -s tests -v"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

from scene_audit import hebrew
from scene_audit.cli import main
from scene_audit.geometry import iou, view_to_source

OBJECT_CODES = ["ID", "ST", "FB", "AN", "OB", "AC", "GZ"]
SCENE_CODES = ["DU", "SF", "SY", "AU", "TG", "WD", "SP"]


def run(*argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = main(list(argv))
    return code, buffer.getvalue()


def draw_scene(path: Path, color=(200, 220, 255), mark=False) -> None:
    img = Image.new("RGB", (3000, 1500), color)
    d = ImageDraw.Draw(img)
    d.ellipse([400, 300, 900, 1200], fill=(200, 80, 80))
    d.rectangle([2000, 900, 2300, 1300], fill=(60, 120, 60))
    if mark:
        d.rectangle([10, 10, 50, 50], fill=(0, 0, 0))
    img.save(path)


def tree_hash(folder: Path) -> str:
    digest = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            digest.update(p.name.encode())
            digest.update(p.read_bytes())
    return digest.hexdigest()


class HebrewTest(unittest.TestCase):
    def test_niqqud_full_and_defective_spelling(self):
        lines = ["הילד חובש כּוֹבַע אדום.", "nothing here", "ובכובעים"]
        self.assertEqual([n for n, _ in hebrew.search("כובע", lines)], [1, 3])
        self.assertEqual([n for n, _ in hebrew.search("כבע", lines)], [1, 3])
        self.assertEqual(hebrew.search("hat", lines), [])

    def test_final_letters(self):
        self.assertEqual(hebrew.normalize("שלום"), hebrew.normalize("שלומ"))


class GeometryTest(unittest.TestCase):
    def test_view_to_source(self):
        self.assertEqual(view_to_source([10, 20, 30, 40], [100, 200], 2.0), [105, 210, 115, 220])

    def test_iou(self):
        self.assertAlmostEqual(iou([0, 0, 10, 10], [5, 0, 15, 10]), 1 / 3)


class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "book"
        code, out = run("init", str(self.root), "--name", "בדיקה", "--layout", "spread")
        self.assertEqual(code, 0, out)
        draw_scene(self.root / "scenes" / "scene-1.png")
        draw_scene(self.root / "scenes" / "scene-2.png", color=(255, 230, 200))
        (self.root / "spec" / "spec.md").write_text(
            "# מסמך הפקה\n\n## 3.2 הילד\nהילד חובש כּוֹבַע אדום.\n\n## 5.1 אנטומיה\nחמש אצבעות.\n", encoding="utf-8"
        )
        self.book = ["--book", str(self.root)]

    def tearDown(self):
        self.tmp.cleanup()

    def scene_doc(self, sid="01"):
        return json.loads((self.root / "work" / f"scene-{sid}.json").read_text(encoding="utf-8"))

    def save_doc(self, doc, sid="01"):
        (self.root / "work" / f"scene-{sid}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    def views(self, sid="01"):
        return json.loads((self.root / "work" / f"scene-{sid}" / "views.json").read_text(encoding="utf-8"))

    def test_full_pipeline(self):
        code, out = run("inventory", *self.book)
        self.assertEqual(code, 0, out)
        self.assertIn("3000x1500", out)
        self.assertTrue((self.root / "out" / "contact-sheet.jpg").is_file())

        # No approved rules: scan stops.
        code, out = run("scan", "--all", *self.book)
        self.assertEqual(code, 2, out)
        self.assertEqual(run("rules", *self.book)[0], 0)
        self.assertEqual(run("rules", "--approve", *self.book)[0], 0)
        code, out = run("scan", "--all", *self.book)
        self.assertEqual(code, 0, out)
        views = self.views()
        self.assertEqual(len([v for v in views.values() if v["kind"] == "tile"]), 9)

        # Mapping: the box is seen in two tiles and must merge into one object.
        s = views["full"]["scale"]
        cands = [{"view": "full", "bbox": [400 * s, 300 * s, 900 * s, 1200 * s], "kind": "character", "label": "הילד", "spec_ref": "3.2"}]
        for name in ("r2c3", "r3c3"):
            t = views[name]
            ox, oy = t["offset"]
            y2 = min(1300, t["region"][3])
            cands.append({"view": name, "bbox": [(2000 - ox) * t["scale"], (900 - oy) * t["scale"], (2300 - ox) * t["scale"], (y2 - oy) * t["scale"]], "kind": "object", "label": "קופסה"})
        (self.root / "work" / "scene-01" / "candidates.json").write_text(json.dumps(cands, ensure_ascii=False), encoding="utf-8")
        code, out = run("map", "--scene", "1", *self.book)
        self.assertEqual(code, 0, out)
        doc = self.scene_doc()
        self.assertEqual(len(doc["objects"]), 2)
        box = next(o for o in doc["objects"] if o["label"] == "קופסה")["bbox"]
        self.assertEqual(box, [2000, 900, 2300, 1300])

        code, out = run("crops", "--scene", "1", *self.book)
        self.assertEqual(code, 0, out)
        tasks = json.loads((self.root / "work" / "scene-01" / "crop-tasks.json").read_text(encoding="utf-8"))
        for task in tasks["objects"]:
            with Image.open(self.root / task["alone"][0]) as img:
                self.assertGreaterEqual(min(img.size), 768)

        # Checks and findings.
        doc = self.scene_doc()
        for obj in doc["objects"]:
            obj["checks"] = {c: "pass" for c in OBJECT_CODES}
        doc["objects"][0]["checks"]["AN"] = "fail"
        doc["objects"][0]["action"] = {"who": "הילד", "does": "מוזג מיץ", "with": "קנקן", "toward": "הכוס"}
        doc["scene_checks"] = {c: "pass" for c in SCENE_CODES}
        oid = doc["objects"][0]["object_id"]
        doc["findings"] = [
            {"finding_id": "01-F01", "object_id": oid, "code": "AN", "type": "spec_violation", "spec_ref": "5.1", "severity": "critical", "confidence": "certain", "view": oid, "view_bbox": [300, 600, 500, 800], "where": "יד ימין", "problem": "שש אצבעות", "fix_kind": "local_edit", "fix_instruction": "חמש אצבעות"},
            {"finding_id": "01-F02", "code": "FB", "type": "spec_violation", "spec_ref": "9.9", "severity": "medium", "confidence": "likely", "bbox": [2000, 900, 2300, 1300], "where": "קופסה", "problem": "אותיות", "fix_kind": "local_edit", "fix_instruction": "להסיר"},
        ]
        doc["counts"] = [{"label": "תפוחים", "expected": 2, "result": "correct", "instances": [{"bbox": [10, 10, 40, 40]}]}]
        self.save_doc(doc)
        code, out = run("validate", "--scene", "1", *self.book)
        self.assertEqual(code, 1)
        self.assertIn("confidence 'certain' only after the second pass", out)
        self.assertIn("spec_ref 9.9", out)
        self.assertIn("marked correct but 1 boxes", out)

        doc = self.scene_doc()
        doc["findings"][0]["confidence"] = "likely"
        doc["findings"][1]["spec_ref"] = "3.2"
        doc["counts"][0]["instances"].append({"bbox": [60, 10, 90, 40]})
        self.save_doc(doc)
        code, out = run("validate", "--scene", "1", *self.book)
        self.assertEqual(code, 0, out)
        doc = self.scene_doc()
        self.assertTrue(all(isinstance(v, int) for v in doc["findings"][0]["bbox"]))

        # Coverage reaches 100% only when gap views are marked seen.
        self.assertLess(doc["coverage_pct"], 100)
        run("seen", "--scene", "01", *[g["view"] for g in tasks["gaps"]], *self.book)
        run("validate", "--scene", "1", *self.book)
        self.assertEqual(self.scene_doc()["coverage_pct"], 100)

        # Second pass: confirmed stays, rejected moves to «לוודא».
        code, out = run("verify-pack", "--scene", "1", *self.book)
        self.assertEqual(code, 0, out)
        pack = json.loads((self.root / "work" / "scene-01" / "verify" / "tasks.json").read_text(encoding="utf-8"))
        self.assertEqual(len(pack["tasks"]), 2)
        self.assertNotIn("שש אצבעות", json.dumps(pack, ensure_ascii=False))
        (self.root / "work" / "scene-01" / "verify" / "answers.json").write_text(
            json.dumps({"01-F01": {"verdict": "confirmed", "seen": "six"}, "01-F02": {"verdict": "rejected", "seen": "plain"}}), encoding="utf-8"
        )
        run("verify-apply", "--scene", "1", *self.book)
        doc = self.scene_doc()
        self.assertTrue(doc["findings"][0]["verified_by_second_pass"])
        self.assertEqual(doc["findings"][1]["confidence"], "verify")
        self.assertEqual(run("done", "--scene", "1", *self.book)[0], 0)

        code, out = run("report", *self.book)
        self.assertEqual(code, 0, out)
        out_dir = self.root / "out"
        html = (out_dir / "report.html").read_text(encoding="utf-8")
        self.assertIn('dir="rtl"', html)
        self.assertIn("שש אצבעות", html)
        for name in ("scenes.md", "defects.csv", "decisions.csv", "prompt-block.md", "marked/scene-01.png"):
            self.assertTrue((out_dir / name).is_file(), name)
        with (out_dir / "defects.csv").open(encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([r["finding_id"] for r in rows], ["01-F01"])  # the «לוודא» item is not a defect
        self.assertIn("הילד · מוזג מיץ · עם קנקן · מול הכוס", (out_dir / "scenes.md").read_text(encoding="utf-8"))

        # Same input -> same report.
        run("report", *self.book)
        self.assertEqual(html, (out_dir / "report.html").read_text(encoding="utf-8"))

        # Unchanged and done -> skipped.
        code, out = run("scan", "--scene", "1", *self.book)
        self.assertIn("skipped", out)

        # Decisions: a dismissal is remembered for the same file.
        self.assertEqual(run("decide", "--set", "01-F02=ok", *self.book)[0], 0)
        doc = self.scene_doc()
        doc["findings"].append(dict(doc["findings"][1], finding_id="01-F03", status="pending"))
        self.save_doc(doc)
        run("validate", "--scene", "1", *self.book)
        f3 = next(f for f in self.scene_doc()["findings"] if f["finding_id"] == "01-F03")
        self.assertEqual(f3["status"], "dismissed")

        # Re-render: archive, fresh scene, recheck.
        draw_scene(self.root / "scenes" / "scene-1.png", mark=True)
        code, out = run("scan", "--scene", "1", *self.book)
        self.assertIn("changed", out)
        doc = self.scene_doc()
        self.assertEqual(doc["findings"], [])
        self.assertTrue(doc["previous"].startswith("work/history/"))
        doc["findings"] = [
            {"finding_id": "01-F01", "code": "AN", "type": "spec_violation", "spec_ref": "5.1", "severity": "critical", "confidence": "likely", "bbox": self.old_bbox(doc), "where": "יד", "problem": "עדיין", "fix_kind": "local_edit", "fix_instruction": "x"},
            {"finding_id": "01-F02", "code": "OB", "type": "spec_violation", "spec_ref": "3.2", "severity": "minor", "confidence": "likely", "bbox": [100, 100, 300, 300], "where": "שולחן", "problem": "כוס מרחפת", "fix_kind": "local_edit", "fix_instruction": "x"},
        ]
        self.save_doc(doc)
        code, out = run("recheck", "--scene", "1", *self.book)
        self.assertEqual(code, 0, out)
        self.assertIn("0 closed, 1 remaining, 1 new", out)


    def old_bbox(self, doc):
        history = json.loads((self.root / doc["previous"]).read_text(encoding="utf-8"))
        return history["findings"][0]["bbox"]

    def test_tool_never_writes_to_scenes(self):
        before = tree_hash(self.root / "scenes")
        run("inventory", *self.book)
        run("rules", *self.book)
        run("rules", "--approve", *self.book)
        run("scan", "--all", *self.book)
        run("report", *self.book)
        self.assertEqual(before, tree_hash(self.root / "scenes"))

    def test_docx_spec_and_tracking(self):
        (self.root / "spec" / "spec.md").unlink()
        docx = self.root / "spec" / "spec.docx"
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr("word/document.xml", "<w:document><w:body><w:p><w:r><w:t>4.1 סגנון אחיד</w:t></w:r></w:p></w:body></w:document>")
        code, out = run("rules", *self.book)
        self.assertEqual(code, 0, out)
        self.assertIn("1 numbered section", out)
        (self.root / "track.csv").write_text("page,file\n1,scene-1.png\n2,scene-old.png\n", encoding="utf-8")
        cfg = (self.root / "book.yaml").read_text(encoding="utf-8").replace("tracking: []", 'tracking: ["track.csv"]')
        (self.root / "book.yaml").write_text(cfg, encoding="utf-8")
        code, out = run("inventory", "--no-contact-sheet", *self.book)
        self.assertIn("scene-old.png", out)
        self.assertIn("render not listed in the sheet: scene-2.png", out)

    def test_changed_spec_needs_new_approval(self):
        run("rules", *self.book)
        run("rules", "--approve", *self.book)
        self.assertEqual(run("scan", "--all", *self.book)[0], 0)
        spec = self.root / "spec" / "spec.md"
        spec.write_text(spec.read_text(encoding="utf-8") + "\n## 7.1 חדש\nכלל חדש.\n", encoding="utf-8")
        code, out = run("scan", "--all", *self.book)
        self.assertEqual(code, 2, out)
        self.assertIn("not approved", out)
        self.assertIn("7.1", (self.root / "work" / "spec.txt").read_text(encoding="utf-8"))
        self.assertEqual(run("rules", "--approve", *self.book)[0], 0)
        self.assertEqual(run("scan", "--all", *self.book)[0], 0)

    def test_csv_decision_does_not_carry_to_a_rerender(self):
        run("rules", *self.book)
        run("rules", "--approve", *self.book)
        run("scan", "--scene", "1", *self.book)
        finding = {"finding_id": "01-F01", "code": "AN", "type": "spec_violation", "spec_ref": "5.1", "severity": "critical", "confidence": "likely", "bbox": [500, 500, 600, 600], "where": "יד", "problem": "שש אצבעות", "fix_kind": "local_edit", "fix_instruction": "x"}
        doc = self.scene_doc()
        doc["findings"] = [finding]
        self.save_doc(doc)
        run("report", *self.book)
        path = self.root / "out" / "decisions.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
            fields = list(rows[0].keys())
        rows[0]["decision"] = "ok"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        # Re-render before applying: the same id now names a different defect.
        draw_scene(self.root / "scenes" / "scene-1.png", mark=True)
        run("scan", "--scene", "1", *self.book)
        doc = self.scene_doc()
        doc["findings"] = [dict(finding, code="OB", bbox=[100, 100, 200, 200], problem="כוס מרחפת")]
        self.save_doc(doc)
        code, out = run("decide", "--apply", *self.book)
        self.assertIn("1 row(s) ignored", out)
        self.assertEqual(self.scene_doc()["findings"][0].get("status", "pending"), "pending")
        run("report", *self.book)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            self.assertEqual(next(csv.DictReader(handle))["decision"], "")
        self.assertFalse((self.root / "work" / "dismissed.json").exists())

    def test_init_with_windows_path_and_quotes(self):
        root = Path(self.tmp.name) / "win"
        code, out = run("init", str(root), "--name", 'ספר "חג"', "--spec", "spec\\production.docx", "--scenes", "C:\\renders\\book")
        self.assertEqual(code, 0, out)
        from scene_audit.config import Book

        cfg = Book.load(root).cfg
        self.assertEqual(cfg["paths"]["spec"], "spec\\production.docx")
        self.assertEqual(cfg["paths"]["scenes"], "C:\\renders\\book")
        self.assertEqual(cfg["book"], 'ספר "חג"')

    def test_skill_install(self):
        dest = Path(self.tmp.name) / "skills"
        code, out = run("skill", "--dest", str(dest))
        self.assertEqual(code, 0, out)
        text = (dest / "scene-audit" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: scene-audit\n"))


if __name__ == "__main__":
    unittest.main()

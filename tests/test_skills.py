#!/usr/bin/env python3
"""Unit tests for skill parsing, rendering, and the RTL lint."""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "script"))

from rtl_lint import lint_path  # noqa: E402
from skills_lib import (  # noqa: E402
    CORE_MARKER,
    build_plan,
    destination,
    flat_globs,
    load_skills,
    merge_managed,
    remove_managed,
)
from validate_skills import validate  # noqa: E402


class SkillTests(unittest.TestCase):
    def test_schema_and_dedupe(self) -> None:
        errors = validate(ROOT)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_nine_skills_and_folder_names(self) -> None:
        skills = load_skills(ROOT)
        self.assertEqual(
            [skill.name for skill in skills],
            [
                "core-orchestrator",
                "fullstack-architect",
                "ui-rtl-system",
                "qa-security-gate",
                "interactive-motion",
                "hebrew-content-nikud",
                "kids-edtech-a11y",
                "testing-strategy",
                "devops-deploy",
            ],
        )

    def test_brace_globs_become_a_comma_string(self) -> None:
        flat = flat_globs("**/*.{test,spec}.{ts,tsx},**/e2e/**")
        self.assertIn("**/*.test.ts", flat)
        self.assertIn("**/*.spec.tsx", flat)
        self.assertNotIn("{", flat)
        self.assertNotIn("\n", flat)

    def test_project_all_tools_keeps_one_full_contract(self) -> None:
        planned = {
            item.relpath: item.content
            for item in build_plan(
                ROOT,
                "full",
                ["cursor", "claude", "copilot", "windsurf", "agents"],
                "project",
                True,
            )
        }
        self.assertEqual(planned["AGENTS.md"].count(CORE_MARKER), 1)
        self.assertNotIn(CORE_MARKER, planned["CLAUDE.md"])
        self.assertNotIn(CORE_MARKER, planned["GEMINI.md"])
        self.assertNotIn(CORE_MARKER, planned[".github/copilot-instructions.md"])
        self.assertNotIn(".cursor/rules/core-orchestrator.mdc", planned)
        self.assertIn("@AGENTS.md", planned["CLAUDE.md"])
        cursor = planned[".cursor/rules/ui-rtl-system.mdc"]
        self.assertIn("alwaysApply: false", cursor)
        self.assertNotIn("\nname:", cursor.split("---", 2)[1])

    def test_cursor_only_is_always_apply(self) -> None:
        planned = {
            item.relpath: item.content
            for item in build_plan(ROOT, "web", ["cursor"], "project", True)
        }
        core = planned[".cursor/rules/core-orchestrator.mdc"]
        self.assertIn("alwaysApply: true", core)
        self.assertNotIn("AGENTS.md", planned)
        self.assertNotIn("kids-edtech-a11y", "".join(planned))
        self.assertNotIn("devops-deploy", "".join(planned))
        self.assertIn(".cursor/rules/qa-security-gate.mdc", planned)

    def test_backend_profile_skips_kids_and_ui(self) -> None:
        paths = [
            item.relpath
            for item in build_plan(
                ROOT, "backend", ["cursor", "claude"], "project", True
            )
        ]
        joined = "\n".join(paths)
        self.assertIn("devops-deploy", joined)
        self.assertNotIn("ui-rtl-system", joined)
        self.assertNotIn("kids-edtech-a11y", joined)

    def test_global_destinations(self) -> None:
        home = Path("/tmp/hebrew-home")
        target = Path("/tmp/hebrew-project")
        self.assertEqual(
            destination("global", home, target, "CLAUDE.md"),
            home / ".claude" / "CLAUDE.md",
        )
        self.assertEqual(
            destination("global", home, target, "AGENTS.md"),
            home / ".codex" / "AGENTS.md",
        )
        self.assertEqual(
            destination("global", home, target, ".github/copilot-instructions.md"),
            home / ".copilot" / "copilot-instructions.md",
        )
        self.assertEqual(
            destination("global", home, target, ".windsurf/rules/ui-rtl-system.md"),
            home / ".devin" / "rules" / "ui-rtl-system.md",
        )
        self.assertIsNone(destination("global", home, target, ".devin/rules/ui-rtl-system.md"))
        self.assertNotEqual(
            destination("global", home, target, "CLAUDE.md"),
            home / "CLAUDE.md",
        )

    def test_managed_block_roundtrip(self) -> None:
        block = "<!-- hebrew-pro-agent-skills:begin -->\ncore\n<!-- hebrew-pro-agent-skills:end -->\n"
        original = "# keep\n\nstay\n"
        merged = merge_managed(original, block)
        self.assertIn("# keep", merged)
        self.assertEqual(merged.count("hebrew-pro-agent-skills:begin"), 1)
        again = merge_managed(merged, block.replace("core", "core2"))
        self.assertEqual(again.count("hebrew-pro-agent-skills:begin"), 1)
        self.assertIn("core2", again)
        self.assertNotIn("\ncore\n", again)
        restored = remove_managed(again + "after\n")
        self.assertIn("# keep", restored)
        self.assertIn("after", restored)
        self.assertNotIn("hebrew-pro-agent-skills", restored)

    def test_rtl_fixtures(self) -> None:
        good = lint_path(ROOT / "tests/fixtures/rtl/good.css")
        bad = lint_path(ROOT / "tests/fixtures/rtl/bad.css")
        self.assertEqual(good, [])
        self.assertGreaterEqual(len(bad), 4)
        self.assertEqual(lint_path(ROOT / "tests/fixtures/rtl/good.html"), [])
        self.assertTrue(lint_path(ROOT / "tests/fixtures/rtl/bad.html"))

    def test_secret_patterns_absent(self) -> None:
        blob = "\n".join(
            path.read_text(encoding="utf-8")
            for path in ROOT.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
            and path != Path(__file__)
        )
        self.assertNotIn("BEGIN PRIVATE KEY", blob)
        self.assertIsNone(re.search(r"AKIA[0-9A-Z]{16}", blob))
        self.assertNotIn("ghp_", blob)
        self.assertNotIn("sk-proj-", blob)


class SnapshotTests(unittest.TestCase):
    def test_committed_snapshot_matches_generator(self) -> None:
        out = ROOT / "dist" / "project-full"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "script" / "generate.py"),
                "--check",
                "--out",
                str(out),
                "--profile",
                "full",
                "--mode",
                "project",
                "--tools",
                "cursor,claude,copilot,windsurf,agents",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()

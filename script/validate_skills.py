#!/usr/bin/env python3
"""Schema and rendered-format checks for skills/."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rtl_lint import lint_text
from skills_lib import (
    ACTIVATIONS,
    CORE_MARKER,
    CORE_NAME,
    GENERATED_NOTE,
    NAME_RE,
    PROFILES,
    REQUIRED_HEADINGS,
    VERSION,
    build_plan,
    load_skills,
    repo_root_from,
)


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def frontmatter_block(content: str) -> str:
    if not content.startswith("---\n"):
        return ""
    end = content.find("\n---\n", 4)
    if end == -1:
        return ""
    return content[4:end]


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    skills = load_skills(root)
    orders: set[str] = set()
    names: set[str] = set()
    for skill in skills:
        rel = skill.path.parent.name
        if skill.name != rel:
            fail(errors, f"{skill.path}: folder {rel} must equal name {skill.name}")
        if not NAME_RE.match(skill.name) or len(skill.name) > 64 or skill.name.startswith("-"):
            fail(errors, f"{skill.name}: name must be a lowercase hyphen slug, max 64 chars")
        if "anthropic" in skill.name or "claude" in skill.name:
            fail(errors, f"{skill.name}: name uses a reserved word")
        if not skill.description or len(skill.description) > 1024:
            fail(errors, f"{skill.name}: description must be 1..1024 characters")
        if "<" in skill.description or ">" in skill.description:
            fail(errors, f"{skill.name}: description cannot contain XML")
        if skill.license != "MIT":
            fail(errors, f"{skill.name}: license must be MIT")
        if skill.author != "NK":
            fail(errors, f"{skill.name}: author must be NK")
        if skill.version != VERSION:
            fail(errors, f"{skill.name}: version must be {VERSION}")
        if skill.activation not in ACTIVATIONS:
            fail(errors, f"{skill.name}: bad activation")
        if skill.activation == "always" and skill.name != CORE_NAME:
            fail(errors, f"{skill.name}: only the core skill is always-on")
        if skill.activation == "globs" and not skill.globs:
            fail(errors, f"{skill.name}: globs activation needs metadata.globs")
        if skill.activation != "always" and not skill.globs:
            fail(errors, f"{skill.name}: metadata.globs is required for copilot applyTo")
        if skill.name == CORE_NAME and skill.globs:
            fail(errors, f"{skill.name}: the always-on skill has no globs")
        unknown = [item for item in skill.profiles if item not in PROFILES or item == "full"]
        if unknown or not skill.profiles:
            fail(errors, f"{skill.name}: profiles must list non-full known profiles")
        if skill.name == CORE_NAME and set(skill.profiles) != {"web", "backend", "kids-hebrew"}:
            fail(errors, f"{skill.name}: core must belong to every profile")
        if skill.order in orders:
            fail(errors, f"{skill.name}: duplicate order {skill.order}")
        orders.add(skill.order)
        if skill.name in names:
            fail(errors, f"duplicate skill name {skill.name}")
        names.add(skill.name)
        for heading in REQUIRED_HEADINGS:
            if heading not in skill.body:
                fail(errors, f"{skill.name}: missing {heading}")
        if "```" not in skill.body:
            fail(errors, f"{skill.name}: needs a fenced example")
    if CORE_MARKER not in next(skill.body for skill in skills if skill.name == CORE_NAME):
        fail(errors, "core marker sentence missing")

    template = root / "skills" / "ui-rtl-system" / "tokens.template.css"
    if not template.is_file():
        fail(errors, "tokens.template.css missing")
    else:
        css_errors = lint_text(template.read_text(encoding="utf-8"), str(template))
        for message in css_errors:
            fail(errors, message)
        text = template.read_text(encoding="utf-8")
        for needle in ("--font-nikud", "--line-height-nikud", '[data-theme="dark"]', "prefers-color-scheme"):
            if needle not in text:
                fail(errors, f"tokens missing {needle}")

    tools = ["cursor", "claude", "copilot", "windsurf", "agents"]
    planned = build_plan(root, "full", tools, "project", dedupe=True)
    by_path = {item.relpath: item for item in planned}
    if ".cursor/rules/core-orchestrator.mdc" in by_path:
        fail(errors, "deduped project install must not always-apply the cursor core")
    if ".windsurf/rules/core-orchestrator.md" in by_path:
        fail(errors, "deduped project install must not always-on the windsurf core")
    agents = by_path["AGENTS.md"].content
    claude_md = by_path["CLAUDE.md"].content
    gemini = by_path["GEMINI.md"].content
    copilot = by_path[".github/copilot-instructions.md"].content
    if agents.count(CORE_MARKER) != 1:
        fail(errors, "AGENTS.md must contain the core contract once")
    for label, content in (("CLAUDE.md", claude_md), ("GEMINI.md", gemini), ("copilot", copilot)):
        if CORE_MARKER in content:
            fail(errors, f"{label} duplicates the full core contract")
    claude_core = by_path[f".claude/skills/{CORE_NAME}/SKILL.md"].content
    if "disable-model-invocation: true" not in claude_core:
        fail(errors, "claude core skill must not auto-invoke")
    if CORE_MARKER not in claude_core:
        fail(errors, "claude core skill keeps the contract for explicit invocation")
    if "name:" in frontmatter_block(by_path[".cursor/rules/ui-rtl-system.mdc"].content):
        fail(errors, "cursor frontmatter must not use name")
    cursor_fm = frontmatter_block(by_path[".cursor/rules/ui-rtl-system.mdc"].content)
    if "globs:" not in cursor_fm or "\n  -" in cursor_fm:
        fail(errors, "cursor globs must be a comma-separated string")
    if "alwaysApply: false" not in cursor_fm:
        fail(errors, "non-core cursor rules are not alwaysApply")
    claude_fm = frontmatter_block(by_path[".claude/skills/ui-rtl-system/SKILL.md"].content)
    if "name: ui-rtl-system" not in claude_fm:
        fail(errors, "claude folder skill must repeat name")
    if "metadata:" in claude_fm or "globs:" in claude_fm:
        fail(errors, "claude output keeps only portable frontmatter")
    copilot_rule = by_path[".github/instructions/qa-security-gate.instructions.md"].content
    if "applyTo:" not in frontmatter_block(copilot_rule):
        fail(errors, "copilot instructions need applyTo")
    wind_fm = frontmatter_block(by_path[".windsurf/rules/ui-rtl-system.md"].content)
    if "trigger: glob" not in wind_fm:
        fail(errors, "windsurf UI rule should trigger on globs")
    devin = by_path[".devin/rules/ui-rtl-system.md"].content
    if devin != by_path[".windsurf/rules/ui-rtl-system.md"].content:
        fail(errors, "devin and windsurf rule bodies drifted")
    for item in planned:
        if item.relpath.startswith(".windsurf/") or item.relpath.startswith(".devin/"):
            if len(item.content) > 12000:
                fail(errors, f"{item.relpath} exceeds the 12000 character workspace rule limit")
        if item.kind == "owned" and item.relpath.endswith(".css"):
            continue
        if item.kind == "owned" and GENERATED_NOTE not in item.content:
            fail(errors, f"{item.relpath} missing generated note")
    if ".github/instructions/core-orchestrator.instructions.md" in by_path:
        fail(errors, "core contract must not also be a path instruction")
    backend = {item.relpath for item in build_plan(root, "backend", tools, "project", True)}
    if any("ui-rtl-system" in path for path in backend):
        fail(errors, "backend profile must not include the UI skill")
    if not any("devops-deploy" in path for path in backend):
        fail(errors, "backend profile must include devops")
    return errors


def main() -> int:
    root = repo_root_from(Path(__file__).resolve().parent)
    errors = validate(root)
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        print(f"{len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"validated {len(load_skills(root))} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

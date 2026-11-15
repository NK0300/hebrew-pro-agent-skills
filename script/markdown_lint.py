#!/usr/bin/env python3
"""Small markdown lint for the files this repository authors.

Checks trailing whitespace, final newline, tabs, fenced-code language tags,
and a blank line around fenced blocks. Generated dist/ is excluded.
"""

from __future__ import annotations

import sys
from pathlib import Path


def lint_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if "\t" in text:
        errors.append(f"{path}: contains a tab")
    if not text.endswith("\n"):
        errors.append(f"{path}: missing final newline")
    if text.endswith("\n\n"):
        errors.append(f"{path}: extra blank line at end of file")
    lines = text.splitlines()
    in_fence = False
    fence = ""
    for index, line in enumerate(lines, start=1):
        if line.rstrip(" ") != line:
            errors.append(f"{path}:{index}: trailing whitespace")
        if line.startswith("```"):
            if not in_fence:
                lang = line[3:].strip()
                if lang == "":
                    errors.append(f"{path}:{index}: fenced block needs a language")
                if index > 1 and lines[index - 2].strip() != "":
                    errors.append(f"{path}:{index}: blank line required before fence")
                in_fence = True
                fence = line
            else:
                in_fence = False
                if index < len(lines) and lines[index].strip() != "":
                    # The next line may be the end of the file's last construct.
                    errors.append(f"{path}:{index}: blank line required after fence")
                fence = ""
        _ = fence
    if in_fence:
        errors.append(f"{path}: unclosed fence")
    return errors


def iter_markdown(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*.md"):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(("dist/", "node_modules/", ".git/", ".hebrew-skills/")):
            continue
        paths.append(path)
    return sorted(paths)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    files = iter_markdown(root)
    for path in files:
        errors.extend(lint_file(path))
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        print(f"{len(errors)} markdown issue(s)", file=sys.stderr)
        return 1
    print(f"markdown ok ({len(files)} file(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

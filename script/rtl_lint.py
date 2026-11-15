#!/usr/bin/env python3
"""Flag physical left/right CSS and oversized Hebrew letter-spacing.

Line opt-out: rtl-lint-disable-line on the same line, or
rtl-lint-disable-next-line on the previous line. File opt-out:
rtl-lint-disable-file.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROP_RE = re.compile(
    r"(?m)^(?P<indent>\s*)(?P<prop>[a-z-]+)\s*:\s*(?P<value>[^;]+);"
)
PHYSICAL_PROPS = {
    "margin-left",
    "margin-right",
    "padding-left",
    "padding-right",
    "border-left",
    "border-right",
    "border-left-width",
    "border-right-width",
    "border-left-style",
    "border-right-style",
    "border-left-color",
    "border-right-color",
    "left",
    "right",
    "scroll-margin-left",
    "scroll-margin-right",
    "scroll-padding-left",
    "scroll-padding-right",
    "border-top-left-radius",
    "border-top-right-radius",
    "border-bottom-left-radius",
    "border-bottom-right-radius",
}
DIRECTION_VALUES = {
    "text-align": {"left", "right"},
    "float": {"left", "right"},
    "clear": {"left", "right"},
}
TAILWIND_RE = re.compile(
    r"(?:^|[\s\"'`{])(?:[A-Za-z0-9:/_-]+:)?("
    r"ml|mr|pl|pr|text-left|text-right|float-left|float-right|border-l|border-r|left|right"
    r")-"
)
MARKUP_SUFFIXES = {".html", ".tsx", ".jsx", ".vue", ".svelte"}


def _disabled(lines: list[str], index: int, text: str) -> bool:
    if "rtl-lint-disable-file" in text:
        return True
    if "rtl-lint-disable-line" in lines[index]:
        return True
    if index > 0 and "rtl-lint-disable-next-line" in lines[index - 1]:
        return True
    return False


def _letter_spacing_bad(value: str) -> bool:
    cleaned = value.strip().strip("'\"").lower()
    if cleaned in {
        "0",
        "0em",
        "0px",
        "normal",
        "inherit",
        "initial",
        "unset",
        "var(--letter-spacing-hebrew)",
    }:
        return False
    if cleaned.startswith("var("):
        return False
    match = re.fullmatch(r"(-?\d*\.?\d+)em", cleaned)
    if match:
        return float(match.group(1)) > 0.02
    return True


def lint_text(text: str, name: str, markup: bool = False) -> list[str]:
    if "rtl-lint-disable-file" in text:
        return []
    errors: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if _disabled(lines, index, text):
            continue
        for match in PROP_RE.finditer(line):
            prop = match.group("prop")
            value = match.group("value").strip()
            if prop in PHYSICAL_PROPS:
                errors.append(f"{name}:{index + 1}: physical property {prop}")
            allowed = DIRECTION_VALUES.get(prop)
            if allowed and value.lower() in allowed:
                errors.append(f"{name}:{index + 1}: physical {prop}: {value.strip()}")
            if prop == "letter-spacing" and _letter_spacing_bad(value):
                errors.append(
                    f"{name}:{index + 1}: Hebrew letter-spacing must be 0 or at most 0.02em"
                )
        if markup:
            for tw in TAILWIND_RE.finditer(line):
                errors.append(f"{name}:{index + 1}: physical utility {tw.group(1)}-")
    return errors


def lint_path(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return lint_text(text, str(path), markup=path.suffix in MARKUP_SUFFIXES)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint CSS for physical direction")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--expect-fail",
        action="store_true",
        help="Exit 0 only when at least one finding is reported",
    )
    args = parser.parse_args(argv)
    findings: list[str] = []
    for path in args.paths:
        if not path.is_file():
            print(f"missing {path}", file=sys.stderr)
            return 2
        findings.extend(lint_path(path))
    for finding in findings:
        print(finding)
    if args.expect_fail:
        if findings:
            print(f"expected failure observed ({len(findings)})")
            return 0
        print("expected physical-property findings, found none", file=sys.stderr)
        return 1
    if findings:
        print(f"{len(findings)} finding(s)", file=sys.stderr)
        return 1
    print(f"rtl-lint ok ({len(args.paths)} file(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

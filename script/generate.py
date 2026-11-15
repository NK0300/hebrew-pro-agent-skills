#!/usr/bin/env python3
"""Write derived tool files from skills/."""

from __future__ import annotations

import argparse
import filecmp
import sys
import tempfile
from pathlib import Path

from skills_lib import PROFILES, TOOLS, build_plan, parse_tools, repo_root_from


def write_tree(out: Path, files: list) -> None:
    if out.exists():
        for child in sorted(out.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
    for planned in files:
        dest = out / planned.relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(planned.content, encoding="utf-8", newline="\n")


def trees_equal(left: Path, right: Path) -> bool:
    compared = filecmp.dircmp(left, right)
    if compared.left_only or compared.right_only or compared.diff_files or compared.funny_files:
        return False
    return all(trees_equal(left / name, right / name) for name in compared.common_dirs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate per-tool skill files")
    parser.add_argument("--repo", type=Path, default=None)
    parser.add_argument("--profile", default="full", choices=PROFILES)
    parser.add_argument("--tools", default=",".join(TOOLS))
    parser.add_argument("--mode", default="project", choices=("project", "global"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Give every selected tool a full always-on copy",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when --out does not match a fresh generation",
    )
    args = parser.parse_args(argv)
    root = repo_root_from(args.repo or Path(__file__).resolve().parent)
    if args.out.resolve() == root.resolve():
        raise SystemExit("refusing to generate into the repository root")
    tools = parse_tools(args.tools)
    planned = build_plan(root, args.profile, tools, args.mode, dedupe=not args.no_dedupe)
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "fresh"
            write_tree(fresh, planned)
            if not args.out.exists() or not trees_equal(fresh, args.out):
                print(f"generated tree differs from {args.out}", file=sys.stderr)
                return 1
        print(f"ok {args.out}")
        return 0
    write_tree(args.out, planned)
    print(f"wrote {len(planned)} files to {args.out}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())

#!/usr/bin/env python3
"""Install or remove generated skill files without clobbering user instructions.

Owned files (rules, skills) are replaced only after a timestamped backup.
Managed files (CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions.md) keep
everything outside the hebrew-pro-agent-skills markers.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skills_lib import (  # noqa: E402
    PROFILES,
    TOOLS,
    VERSION,
    build_plan,
    destination,
    merge_managed,
    parse_tools,
    remove_managed,
    repo_root_from,
    sha256_text,
)

GITIGNORE = "*\n!.gitignore\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install Hebrew-first agent skills")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--mode", required=True, choices=("project", "global"))
    parser.add_argument("--tools", required=True)
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--target", type=Path, default=None)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--no-dedupe", action="store_true")
    return parser.parse_args(argv)


def state_paths(mode: str, home: Path, target: Path) -> tuple[Path, Path]:
    if mode == "project":
        directory = target / ".hebrew-skills"
    else:
        directory = home / ".hebrew-pro-agent-skills"
    return directory, directory / "install-state.json"


def guard(mode: str, home: Path, target: Path) -> None:
    home_resolved = home.resolve()
    if home_resolved == Path("/"):
        raise SystemExit("refusing to use / as HOME")
    if not home.is_dir():
        raise SystemExit(f"HOME is not a directory: {home}")
    if mode == "project":
        target_resolved = target.resolve()
        if target_resolved == Path("/"):
            raise SystemExit("refusing to install into /")
        if target_resolved == home_resolved:
            raise SystemExit("project target must not be HOME; use --mode global")
        if not target.is_dir():
            raise SystemExit(f"target is not a directory: {target}")


def contained(base: Path, path: Path) -> None:
    resolved = path.resolve()
    root = base.resolve()
    if resolved != root and root not in resolved.parents:
        raise SystemExit(f"refusing to write outside {root}: {path}")


def assert_not_home_root_instruction(home: Path, path: Path) -> None:
    resolved = path.resolve()
    if resolved in {home.resolve() / "CLAUDE.md", home.resolve() / "AGENTS.md"}:
        raise SystemExit(f"refusing to write {resolved.name} at the home directory root")


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def load_state(path: Path) -> dict:
    if not path.is_file():
        return {"version": VERSION, "files": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, payload: dict, dry_run: bool) -> None:
    if dry_run:
        print(f"dry-run write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_gitignore(directory: Path, dry_run: bool) -> None:
    path = directory / ".gitignore"
    if path.is_file() and path.read_text(encoding="utf-8") == GITIGNORE:
        print(f"unchanged {path}")
        return
    print(("dry-run write " if dry_run else "write ") + str(path))
    if dry_run:
        return
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(GITIGNORE, encoding="utf-8")


def backup_file(src: Path, backup_root: Path, relative: str, dry_run: bool) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest = backup_root / stamp / relative
    print(("dry-run backup " if dry_run else "backup ") + f"{src} -> {dest}")
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return str(dest)


def relative_to_base(base: Path, path: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def install(args: argparse.Namespace, root: Path, home: Path, target: Path) -> int:
    tools = parse_tools(args.tools)
    mode = args.mode
    directory, state_file = state_paths(mode, home, target)
    base = target if mode == "project" else home
    previous = {item["path"]: item for item in load_state(state_file).get("files", [])}
    planned = build_plan(root, args.profile, tools, mode, dedupe=not args.no_dedupe)
    records: list[dict] = []
    backup_root = directory / "backups"

    for item in planned:
        dest_path = destination(mode, home, target, item.relpath)
        if dest_path is None:
            continue
        dest = dest_path.resolve()
        contained(base, dest)
        assert_not_home_root_instruction(home, dest)
        key = str(dest)
        prev = previous.get(key)
        existed_on_disk = dest.exists()
        if prev is not None:
            existed_before = bool(prev.get("existed_before"))
        else:
            existed_before = existed_on_disk

        if item.kind == "managed":
            current = read_text(dest) if existed_on_disk else None
            if existed_on_disk and current is None:
                raise SystemExit(f"{dest} is not UTF-8; refusing to merge a managed block")
            merged = merge_managed(current, item.content)
            changed = (not existed_on_disk) or current != merged
        else:
            merged = item.content
            current = read_text(dest) if existed_on_disk else None
            changed = (not existed_on_disk) or current != merged

        backup_path = prev.get("backup") if prev else None
        if changed and existed_on_disk:
            fresh = backup_file(dest, backup_root, relative_to_base(base, dest), args.dry_run)
            if not backup_path:
                backup_path = fresh
            action = "merge" if item.kind == "managed" else "write"
            print(("dry-run " if args.dry_run else "") + f"{action} {dest}")
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(merged, encoding="utf-8", newline="\n")
        elif changed:
            print(("dry-run write " if args.dry_run else "write ") + str(dest))
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(merged, encoding="utf-8", newline="\n")
        else:
            print(f"unchanged {dest}")

        records.append(
            {
                "backup": backup_path,
                "existed_before": existed_before,
                "kind": item.kind,
                "path": str(dest),
                "sha256": sha256_text(merged),
            }
        )

    payload = {
        "files": records,
        "mode": mode,
        "profile": args.profile,
        "tools": tools,
        "version": VERSION,
    }
    ensure_gitignore(directory, args.dry_run)
    save_state(state_file, payload, args.dry_run)
    print(f"installed {len(records)} file(s) profile={args.profile} tools={','.join(tools)}")
    return 0


def uninstall(args: argparse.Namespace, home: Path, target: Path) -> int:
    directory, state_file = state_paths(args.mode, home, target)
    state = load_state(state_file)
    files = state.get("files") or []
    if not state_file.is_file() or not files:
        print("nothing to uninstall")
        return 0
    for record in files:
        path = Path(record["path"])
        if not path.exists():
            print(f"absent {path}")
            continue
        kind = record["kind"]
        if kind == "managed":
            current = read_text(path)
            if current is None:
                print(f"kept {path} (not UTF-8)")
                continue
            updated = remove_managed(current)
            if updated == current:
                print(f"unchanged {path}")
                continue
            if updated == "" and not record.get("existed_before"):
                print(("dry-run delete " if args.dry_run else "delete ") + str(path))
                if not args.dry_run:
                    path.unlink()
                continue
            print(("dry-run merge " if args.dry_run else "merge ") + str(path))
            if not args.dry_run:
                path.write_text(updated, encoding="utf-8", newline="\n")
            continue
        current_text = read_text(path)
        current_sha = sha256_text(current_text) if current_text is not None else ""
        if current_sha != record.get("sha256"):
            print(f"kept modified {path}")
            continue
        if record.get("existed_before") and record.get("backup"):
            backup = Path(record["backup"])
            print(("dry-run restore " if args.dry_run else "restore ") + f"{backup} -> {path}")
            if not args.dry_run:
                shutil.copy2(backup, path)
            continue
        if record.get("existed_before"):
            print(f"kept {path} (no backup to restore)")
            continue
        print(("dry-run delete " if args.dry_run else "delete ") + str(path))
        if not args.dry_run:
            path.unlink()
    print(("dry-run delete " if args.dry_run else "delete ") + str(state_file))
    if not args.dry_run and state_file.exists():
        state_file.unlink()
    print("uninstalled")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root_from(args.repo)
    home = args.home.expanduser().resolve()
    target = (args.target or Path.cwd()).expanduser().resolve()
    guard(args.mode, home, target)
    if args.uninstall:
        return uninstall(args, home, target)
    return install(args, root, home, target)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)

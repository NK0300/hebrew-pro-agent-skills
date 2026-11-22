"""Command line entry point: `scene-audit <command>`."""

from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path

from . import __version__
from .config import CONFIG_NAME, Book, ConfigError, read_json, write_json


def _out(text: str) -> None:
    print(text)


def _json(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _book(args) -> Book:
    return Book.load(getattr(args, "book", None))


# Commands ---------------------------------------------------------------

def cmd_init(args) -> int:
    root = Path(args.dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / CONFIG_NAME
    if target.exists() and not args.force:
        _out(f"{target} already exists. Use --force to overwrite.")
        return 1
    template = resources.files("scene_audit").joinpath("data/book.yaml.template").read_text(encoding="utf-8")
    values = {"book": args.name or root.name, "scenes": args.scenes or "scenes", "spec": args.spec or "spec", "layout": args.layout}
    for key, value in values.items():
        # A JSON string is a valid YAML double-quoted scalar: backslashes in Windows paths and quotes stay literal.
        template = template.replace(f'"{{{{{key}}}}}"', json.dumps(value, ensure_ascii=False))
    target.write_text(template, encoding="utf-8")
    for folder in ([] if args.scenes else ["scenes"]) + ([] if args.spec else ["spec"]) + ["work", "out"]:
        (root / folder).mkdir(exist_ok=True)
    _out(f"Created {target}")
    _out("Next: put the renders in scenes/ and the production document in spec/, then run `scene-audit inventory`.")
    return 0


def cmd_skill(args) -> int:
    text = resources.files("scene_audit").joinpath("data/SKILL.md").read_text(encoding="utf-8")
    if args.print:
        sys.stdout.write(text)
        return 0
    if args.dest:
        base = Path(args.dest).expanduser()
    elif args.user:
        base = Path.home() / ".claude" / "skills"
    else:
        base = Path.cwd() / ".claude" / "skills"
    target = base / "scene-audit" / "SKILL.md"
    if target.exists() and target.read_text(encoding="utf-8") != text and not args.force:
        _out(f"{target} exists and differs. Use --force to replace it.")
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    _out(f"Installed the Claude Code skill: {target}")
    _out("In Claude Code, ask: «תסרוק את כל הסצנות» or run /scene-audit.")
    return 0


def cmd_inventory(args) -> int:
    from . import inventory

    book = _book(args)
    data = inventory.run(book, make_contact_sheet=not args.no_contact_sheet)
    if args.json:
        _json(data)
    else:
        _out(inventory.describe(data))
    if data["count"] == 0:
        _out(f"No images found in {book.rel(book.scenes_dir)}. Check paths.scenes in {CONFIG_NAME}.")
        return 1
    return 0


def cmd_rules(args) -> int:
    from . import rules

    book = _book(args)
    if args.approve:
        problems = rules.approve(book)
        for p in problems:
            _out(f"!! {p}")
        if any("missing" in p for p in problems):
            return 1
        _out("rules.yaml approved.")
        return 0
    if args.check:
        problems = rules.check_rules(book)
        for p in problems:
            _out(f"!! {p}")
        _out("approved" if rules.is_approved(book) else "NOT approved yet")
        return 1 if problems else 0
    try:
        meta = rules.extract(book)
    except FileNotFoundError as exc:
        _out(str(exc))
        return 1
    _out(f"Extracted {len(meta['source_files'])} file(s) to work/spec.txt, {len(meta['sections'])} numbered section(s).")
    _out("Next: read work/spec.txt, fill work/rules.yaml (each rule with spec_ref), show it to the owner, then `scene-audit rules --approve`.")
    return 0


def cmd_spec_search(args) -> int:
    from . import hebrew, rules

    book = _book(args)
    for term in args.terms:
        hits = rules.spec_search(book, term)
        _out(f"«{term}» variants {hebrew.variants(term)}: {len(hits)} hit(s)")
        for number, line in hits[: args.limit]:
            _out(f"  spec.txt:{number}: {line.strip()[:160]}")
    return 0


def _require_spec(book: Book, allow_unapproved: bool) -> str | None:
    from . import rules

    if not rules.spec_files(book):
        return f"No production document in {book.rel(book.spec_dir)}. The audit stops here and asks for it."
    if not (book.work / "spec.txt").is_file() or rules.spec_changed(book):
        rules.extract(book)  # a changed spec gets a new digest, so the old approval no longer matches
    if not rules.is_approved(book) and not allow_unapproved:
        return "work/rules.yaml is not approved. Fill it from work/spec.txt, show the owner, run `scene-audit rules --approve`."
    return None


def cmd_scan(args) -> int:
    from . import inventory, scene

    book = _book(args)
    problem = _require_spec(book, args.allow_unapproved)
    if problem:
        _out(problem)
        return 2
    inventory.run(book, make_contact_sheet=False)
    sids = book.resolve_scenes(args.scene, args.all)
    report = []
    for sid in sids:
        state, doc = scene.prepare(book, sid, force=args.force)
        views = scene.load_views(book, sid)
        report.append(
            {
                "scene_id": sid,
                "state": state,
                "stage": doc.get("stage"),
                "views": [v["file"] for n, v in views.items() if v["kind"] in ("full", "tile")] if state != "skipped" else [],
                "candidates": book.rel(book.scene_work(sid) / "candidates.json"),
            }
        )
    if args.json:
        _json(report)
        return 0
    for item in report:
        if item["state"] == "skipped":
            _out(f"scene {item['scene_id']}: unchanged and done, skipped")
            continue
        _out(f"scene {item['scene_id']}: {item['state']}, stage {item['stage']}")
        if item["stage"] == "mapping":
            _out("  look at every view, then list objects in " + item["candidates"])
            for v in item["views"]:
                _out(f"    {v}")
    return 0


def cmd_map(args) -> int:
    from . import scene

    book = _book(args)
    for sid in book.resolve_scenes(args.scene, args.all):
        result = scene.map_objects(book, sid)
        _out(f"scene {sid}: {result['candidates']} candidate(s) -> {result['objects']} object(s). Check work/scene-{sid}/objects-marked.png")
        for p in result["problems"]:
            _out(f"  !! {p}")
        for d in result["duplicates"]:
            _out(f"  ?? {d}")
        for m in result["expected_missing"]:
            _out(f"  missing vs spec: {m}")
    return 0


def cmd_crops(args) -> int:
    from . import scene

    book = _book(args)
    for sid in book.resolve_scenes(args.scene, args.all):
        result = scene.make_crops(book, sid)
        _out(f"scene {sid}: {result['objects']} object crop set(s), {result['gaps']} gap view(s). Task list: work/scene-{sid}/crop-tasks.json")
    return 0


def cmd_coords(args) -> int:
    from . import scene

    book = _book(args)
    box = [float(v) for v in args.bbox.split(",")]
    _out(json.dumps(scene.to_source(book, args.scene.zfill(2) if args.scene.isdigit() else args.scene, args.view, box)))
    return 0


def cmd_seen(args) -> int:
    book = _book(args)
    sid = args.scene.zfill(2) if args.scene.isdigit() else args.scene
    doc = read_json(book.scene_json(sid))
    reviewed = set(doc.get("gaps_reviewed", []))
    reviewed.update(args.views)
    doc["gaps_reviewed"] = sorted(reviewed)
    write_json(book.scene_json(sid), doc)
    _out(f"scene {sid}: {len(reviewed)} gap view(s) marked reviewed")
    return 0


def cmd_validate(args) -> int:
    from .findings import run_validate

    book = _book(args)
    failed = False
    for sid in book.resolve_scenes(args.scene, args.all):
        if not book.scene_json(sid).is_file():
            continue
        errors, warnings, doc = run_validate(book, sid)
        _out(f"scene {sid}: {len(errors)} error(s), {len(warnings)} warning(s), coverage {doc.get('coverage_pct')}%")
        for e in errors:
            _out(f"  !! {e}")
        if not args.quiet:
            for w in warnings:
                _out(f"  -- {w}")
        failed = failed or bool(errors)
    return 1 if failed else 0


def cmd_verify_pack(args) -> int:
    from .findings import verify_pack

    book = _book(args)
    for sid in book.resolve_scenes(args.scene, args.all):
        if not book.scene_json(sid).is_file():
            continue
        result = verify_pack(book, sid)
        _out(f"scene {sid}: {result['tasks']} finding(s) for the second pass -> {result['file']}")
        for e in result["validation_errors"]:
            _out(f"  !! {e}")
    return 0


def cmd_verify_apply(args) -> int:
    from .findings import verify_apply

    book = _book(args)
    for sid in book.resolve_scenes(args.scene, args.all):
        if not book.scene_json(sid).is_file():
            continue
        stats = verify_apply(book, sid)
        _out(f"scene {sid}: {stats['confirmed']} confirmed, {stats['downgraded']} moved to «לוודא», {stats['unanswered']} unanswered")
    return 0


def cmd_status(args) -> int:
    from .scene import coverage

    book = _book(args)
    rows = []
    for sid, path in sorted(book.scene_map().items()):
        doc = read_json(book.scene_json(sid))
        if not doc:
            rows.append((sid, path.name, "not scanned", "", "", "scene-audit scan --scene " + sid))
            continue
        pct, _ = coverage(book, doc)
        stage = doc.get("stage", "?")
        nxt = {
            "mapping": "fill candidates.json, then scene-audit map",
            "checking": "scene-audit crops, check every crop, write findings, then verify-pack",
            "verifying": "run the second pass, then verify-apply",
            "classified": "scene-audit report",
            "done": "-",
        }.get(stage, "")
        if stage == "checking" and not (book.scene_work(sid) / "crop-tasks.json").is_file():
            nxt = "scene-audit crops --scene " + sid
        findings = [f for f in doc.get("findings", []) if f.get("status") != "dismissed"]
        rows.append((sid, path.name, stage, f"{pct}%", str(len(findings)), nxt))
    for row in rows:
        _out(f"{row[0]:>4}  {row[1]:<32} {row[2]:<11} cov {row[3]:<5} findings {row[4]:<3} next: {row[5]}")
    return 0


def cmd_report(args) -> int:
    from .report import build

    book = _book(args)
    result = build(book)
    _out(
        f"report: {result['scenes']} scene(s), {result['defects']} defect(s) ({result['critical']} critical), "
        f"{result['verify']} to verify, {result['conflicts']} spec conflict(s), {result['decisions_pending']} decision(s) pending"
    )
    _out(f"Open {book.rel(book.out / 'report.html')}")
    if result["not_done"]:
        _out("Not complete yet: " + ", ".join(result["not_done"]))
    return 0


def cmd_done(args) -> int:
    from .findings import run_validate

    book = _book(args)
    sid = args.scene.zfill(2) if args.scene.isdigit() else args.scene
    errors, warnings, doc = run_validate(book, sid)
    if errors:
        _out(f"scene {sid} cannot be closed: {len(errors)} validation error(s). Run scene-audit validate.")
        return 1
    unverified = [f["finding_id"] for f in doc.get("findings", []) if not f.get("verified_by_second_pass") and f.get("confidence") != "verify" and f.get("status") != "dismissed"]
    if unverified:
        _out(f"scene {sid}: second pass missing for {', '.join(unverified)}")
        return 1
    doc["stage"] = "done"
    write_json(book.scene_json(sid), doc)
    _out(f"scene {sid} marked done (coverage {doc.get('coverage_pct')}%)")
    return 0


def cmd_decide(args) -> int:
    from . import decisions

    book = _book(args)
    if args.apply:
        stats = decisions.apply_csv(book)
        _out(f"applied {stats['applied']} decision(s), {stats['skipped']} row(s) left empty")
        if stats["stale"]:
            _out(f"!! {stats['stale']} row(s) ignored: the render or the finding changed since the CSV was written. Run scene-audit report and decide again.")
        return 0
    if args.set:
        for item in args.set:
            fid, _, decision = item.partition("=")
            status = decisions.set_decision(book, fid.strip(), decision, args.note or "")
            _out(f"{fid}: {status}")
        return 0
    items = decisions.queue(book, threshold_only=not args.all)
    if not items:
        _out("No decisions waiting.")
        return 0
    for f in items:
        _out(f"{f['finding_id']:<10} {f.get('severity', ''):<8} {f.get('code', ''):<3} {f.get('where', '')}: {f.get('problem', '')}  -> recommended {f.get('fix_kind', '')}")
    _out("Answer with: scene-audit decide --set 07-F02=ok|local|rerender  (or fill out/decisions.csv and --apply)")
    return 0


def cmd_recheck(args) -> int:
    from . import decisions

    book = _book(args)
    sid = args.scene.zfill(2) if args.scene.isdigit() else args.scene
    result = decisions.recheck(book, sid)
    _out(f"scene {sid}: {len(result['closed'])} closed, {len(result['remaining'])} remaining, {len(result['new'])} new. See out/recheck-{sid}.md")
    return 0


# Parser -----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scene-audit", description="Object-level audit of illustrated book scenes, driven by Claude Code.")
    parser.add_argument("--version", action="version", version=f"scene-audit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, func, help_text, scenes=False):
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.add_argument("--book", help=f"book folder or {CONFIG_NAME} (default: search upward from the current folder)")
        if scenes:
            p.add_argument("--scene", help="scene id, or several separated by commas")
            p.add_argument("--all", action="store_true", help="all scenes")
        p.set_defaults(func=func)
        return p

    p = sub.add_parser("init", help="create book.yaml and the folder layout")
    p.add_argument("dir", nargs="?", default=".")
    p.add_argument("--name")
    p.add_argument("--scenes", help="existing renders folder (relative to the book folder or absolute)")
    p.add_argument("--spec", help="existing production document file or folder")
    p.add_argument("--layout", choices=["single", "spread"], default="single")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("skill", help="install the Claude Code skill (default: ./.claude/skills/scene-audit)")
    p.add_argument("--user", action="store_true", help="install into ~/.claude/skills for every project")
    p.add_argument("--dest", help="skills folder to install into")
    p.add_argument("--print", action="store_true", help="print SKILL.md instead of installing")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_skill)

    p = add("inventory", cmd_inventory, "list renders: size, hash, format check, tracking sheets, contact sheet")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-contact-sheet", action="store_true")

    p = add("rules", cmd_rules, "extract the production document to work/spec.txt and create work/rules.yaml")
    p.add_argument("--approve", action="store_true", help="the owner approves rules.yaml")
    p.add_argument("--check", action="store_true", help="check spec_ref values and approval")

    p = add("spec-search", cmd_spec_search, "search the spec for a term in every spelling (niqqud, full/defective, finals)")
    p.add_argument("terms", nargs="+")
    p.add_argument("--limit", type=int, default=20)

    p = add("scan", cmd_scan, "prepare scenes that changed: full view and overlapping tiles", scenes=True)
    p.add_argument("--force", action="store_true", help="rescan even if unchanged; drops the current findings")
    p.add_argument("--allow-unapproved", action="store_true", help="run before the owner approved rules.yaml (opinion only)")
    p.add_argument("--json", action="store_true")

    add("map", cmd_map, "merge candidates.json into the object list (dedupe by box overlap)", scenes=True)
    add("crops", cmd_crops, "make zoomed crops per object, context crops, and gap views", scenes=True)

    p = add("coords", cmd_coords, "convert a box drawn on a view to source pixels")
    p.add_argument("--scene", required=True)
    p.add_argument("--view", required=True)
    p.add_argument("--bbox", required=True, help="x1,y1,x2,y2 in view pixels")

    p = add("seen", cmd_seen, "mark gap views as reviewed (they count toward coverage)")
    p.add_argument("--scene", required=True)
    p.add_argument("views", nargs="+")

    p = add("validate", cmd_validate, "normalize coordinates and check every finding has its four tags", scenes=True)
    p.add_argument("--quiet", action="store_true")

    add("verify-pack", cmd_verify_pack, "prepare the independent second pass (crops + neutral questions)", scenes=True)
    add("verify-apply", cmd_verify_apply, "apply second-pass answers; unconfirmed findings move to «לוודא»", scenes=True)

    p = add("done", cmd_done, "close a scene after validation and the second pass")
    p.add_argument("--scene", required=True)

    add("status", cmd_status, "stage, coverage and next step for every scene")
    add("report", cmd_report, "build report.html, scenes.md, defects.csv, decisions.csv, marked pages, prompt block")

    p = add("decide", cmd_decide, "show the decision queue, or record the owner's decisions")
    p.add_argument("--apply", action="store_true", help="read out/decisions.csv")
    p.add_argument("--set", nargs="+", metavar="ID=DECISION", help="e.g. 07-F02=ok 07-F03=rerender")
    p.add_argument("--note")
    p.add_argument("--all", action="store_true", help="include findings below the fix threshold")

    p = add("recheck", cmd_recheck, "after a re-render: compare findings with the previous version")
    p.add_argument("--scene", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # Hebrew on Windows consoles
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, KeyError, ValueError, FileNotFoundError) as exc:
        message = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
        print(f"scene-audit: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

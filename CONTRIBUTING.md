# Contributing

<div dir="rtl" lang="he">

תודה. המקור היחיד הוא `skills/`. אל תערכו את `dist/` ביד. אחרי שינוי מריצים את המחולל ואת הבדיקות, ומתארים בדוח מה רץ ומה לא אומת.

</div>

The source of truth is `skills/<name>/SKILL.md`. `script/generate.py` renders Cursor, Claude Code, Copilot, Windsurf, Devin, and `AGENTS.md` from that file. `dist/project-full/` is a snapshot of the full project install. Regenerate it. Do not edit it.

`install.sh` and `install.ps1` both call `script/install_apply.py`, so backup, merge, and path behavior cannot drift between bash and PowerShell. The shell scripts validate flags and refuse unsafe targets (`/`, and a project install whose target is `$HOME`).

## Add or change a skill

Follow `templates/skill-blueprint.md`. Folder name equals frontmatter `name`. Descriptions say when to use the skill and include Hebrew trigger words. Only `core-orchestrator` is always-on.

## Checks

```bash
shellcheck install.sh script/test-install.sh
python3 script/validate_skills.py
python3 script/markdown_lint.py
python3 -m unittest discover -s tests -v
bash script/test-install.sh
python3 script/rtl_lint.py skills/ui-rtl-system/tokens.template.css
npx --yes markdownlint-cli2@0.17.2
```

`bash script/test-install.sh` uses temporary directories and a fake `HOME`. It does not install into this repository. On PowerShell 7, `pwsh -File script/test-install.ps1` covers the Windows entry point the same way.

## Formats to re-check when a tool changes

These were checked for v1.0.0 in November 2026:

- Cursor rules: `description`, `globs` (a comma-separated string), `alwaysApply`. No `name`. Project path `.cursor/rules/*.mdc`. Global file rules `~/.cursor/rules`. Docs: [cursor.com/docs/rules](https://cursor.com/docs/rules), [cursor.com/help/customization/rules](https://cursor.com/help/customization/rules).
- Claude Code: `.claude/skills/<name>/SKILL.md`, folder name equals `name`. Portable fields are `name` and `description`. Global instructions are `~/.claude/CLAUDE.md`, not `~/CLAUDE.md`. Docs: [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills), [agentskills.io/specification](https://agentskills.io/specification).
- Copilot: `.github/copilot-instructions.md` plus `.github/instructions/*.instructions.md` with `applyTo`. Global: `~/.copilot/copilot-instructions.md` and `~/.copilot/instructions/`. Docs: [GitHub repository instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions), [Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions).
- Windsurf / Devin: `trigger` is `always_on`, `model_decision`, `glob`, or `manual`. Project files `.windsurf/rules/*.md` (still imported) and `.devin/rules/*.md` (current). Global rules `~/.devin/rules/`. Docs: [docs.devin.ai/cli/extensibility/rules](https://docs.devin.ai/cli/extensibility/rules).
- `AGENTS.md` is plain Markdown. [agents.md](https://agents.md). Gemini CLI also reads `GEMINI.md`. Codex global file used here is `~/.codex/AGENTS.md`.

## Always-on dedupe

A project install writes the full router once.

- `agents` puts it in `AGENTS.md`. `GEMINI.md` only points at that file.
- `claude` together with `agents` writes `@AGENTS.md` into `CLAUDE.md`, because Cursor would otherwise load both files in full. Claude-only installs embed the contract in `CLAUDE.md`. The Claude skill sets `disable-model-invocation: true` so the body is not loaded a second time.
- `cursor` gets `alwaysApply: true` only when neither `AGENTS.md` nor `CLAUDE.md` is being written. Cursor treats both as always-on.
- `copilot` embeds the contract in `copilot-instructions.md` only when `agents` is not selected.
- `windsurf` gets `trigger: always_on` only when neither `agents` nor `cursor` is selected. Devin reads `AGENTS.md` and `.cursor/rules`.

Pass `--no-dedupe` to force a full copy in every selected tool. Global installs already give each product its own copy, except Devin when Claude is selected, because Devin CLI reads `~/.claude/CLAUDE.md`.

## Reviews

A verification note names the commands that ran and the checks that did not. Do not report a green result you did not run.

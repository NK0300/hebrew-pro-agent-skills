# Skill blueprint

Copy this file to `skills/<name>/SKILL.md`. The folder name and `name` are the same lowercase hyphen slug. Do not put a numeric prefix on the folder: Claude Code and the Agent Skills spec use that name as the command.

Keep the body short. One skill, one job. Put long reference material in a sibling file and point to it.

```yaml
---
name: example-skill
description: "Use when <task>. Say the trigger in the third person and include the Hebrew words a developer would actually type. גם כשהבקשה בעברית."
license: MIT
metadata:
  author: NK
  version: "1.0.0"
  activation: description
  profiles: web
  order: "09"
  globs: "**/example/**"
---
```

`activation` is `always`, `globs`, or `description`.

- `always` is only for `core-orchestrator`. It has no `globs`.
- `globs` auto-attaches in Cursor and Windsurf when a matching file is open. `metadata.globs` is a comma-separated list. Braces are allowed in the source; the generator expands them.
- `description` is chosen by the agent from the description. Still set `globs` so Copilot has an `applyTo` pattern. Keep that pattern narrow. `**` makes the skill always-on.

`profiles` lists `web`, `backend`, and `kids-hebrew`. The `full` profile is every skill. The core skill lists all three.

## When to use

One short paragraph. Name the tasks that should load this skill, and one task that should not.

## Rules

Numbered rules. Prefer a default, then the exception and the comment it requires. Do not write a rule that cannot be bent for a security control: say that explicitly.

1. State the rule.
2. Say what a justified exception looks like, or say there is no exception.

## Examples

### Good

```text
A small snippet the agent can imitate.
```

### Bad

```text
The same situation done the wrong way.
```

## Checklist

- [ ] The change followed the rules above.
- [ ] Any exception has a one-line reason.
- [ ] Verification names commands that ran and checks that did not.

After adding the file, run:

```bash
python3 script/validate_skills.py
python3 script/generate.py --out dist/project-full --profile full --mode project \
  --tools cursor,claude,copilot,windsurf,agents
python3 script/markdown_lint.py
bash script/test-install.sh
```

Commit the regenerated `dist/project-full` tree with the skill. Do not hand-edit `dist/`.

# Agents

This repository publishes Hebrew-first skills. It is not itself a Hebrew application.

- Edit `skills/<name>/SKILL.md`. Do not edit `dist/` by hand.
- Regenerate with `python3 script/generate.py --out dist/project-full --profile full --mode project --tools cursor,claude,copilot,windsurf,agents`.
- Test with `python3 script/validate_skills.py`, `python3 -m unittest discover -s tests -v`, and `bash script/test-install.sh`.
- `bash script/test-install.sh` must use its own temp directories. Do not point `install.sh` at this repo unless you mean to install the skills into it.
- Code, comments, and commits stay in English. The README is Hebrew first, then English.
- A verification note lists commands that ran and checks that did not run.

See `CONTRIBUTING.md` for tool formats and the always-on dedupe rules.

# Changelog

## 1.0.0 - 2026-11-15

First public release of the Hebrew-first agent skills.

- Nine skills: orchestrator, fullstack, RTL UI, security gate, motion, nikud, kids and accessibility, testing, deploy.
- One source in `skills/`, generated for Cursor, Claude Code, GitHub Copilot, Windsurf/Devin, and `AGENTS.md`.
- `install.sh` and `install.ps1` with project and global modes, profiles (`full`, `web`, `backend`, `kids-hebrew`), `--dry-run`, `--uninstall`, timestamped backups, and a managed block that does not replace an existing `CLAUDE.md` or `AGENTS.md`.
- Global Claude instructions go to `~/.claude/CLAUDE.md`.
- Nikud guidance: Noto Sans Hebrew, Noto Serif Hebrew, Frank Ruhl Libre, David Libre, and Alef. Heebo, Assistant, Rubik, and Suez One stay on unpointed UI.
- CI runs shellcheck, schema validation, installer tests, RTL lint, and markdown lint.

#!/usr/bin/env bash
# Exercise install.sh in temporary directories. Never touches the repo tree.
set -euo pipefail

ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"
INSTALL="$ROOT/install.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_file() {
  [ -f "$1" ] || fail "missing file $1"
}

assert_absent() {
  if [ -e "$1" ]; then
    fail "unexpected path $1"
  fi
}

count_marker() {
  file="$1"
  if [ ! -f "$file" ]; then
    echo 0
    return
  fi
  grep -c "hebrew-pro-agent-skills:begin" "$file" || true
}

backup_count() {
  dir="$1"
  if [ ! -d "$dir" ]; then
    echo 0
    return
  fi
  find "$dir" -type f | wc -l | tr -d ' '
}

file_count() {
  dir="$1"
  if [ ! -d "$dir" ]; then
    echo 0
    return
  fi
  find "$dir" -type f | wc -l | tr -d ' '
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1. Dry-run writes nothing.
DRY_HOME="$TMP/dry-home"
DRY_TARGET="$TMP/dry-target"
mkdir -p "$DRY_HOME" "$DRY_TARGET"
HOME="$DRY_HOME" "$INSTALL" --dry-run --target "$DRY_TARGET" --profile full >/dev/null
[ "$(file_count "$DRY_TARGET")" -eq 0 ] || fail "dry-run wrote into the target"
[ "$(file_count "$DRY_HOME")" -eq 0 ] || fail "dry-run wrote into HOME"

# 2. Project install preserves an existing CLAUDE.md and is idempotent.
PROJ_HOME="$TMP/proj-home"
PROJ="$TMP/proj"
mkdir -p "$PROJ_HOME" "$PROJ"
printf '# User notes\nkeep this\n' >"$PROJ/CLAUDE.md"
printf 'name: keep\n' >"$PROJ/AGENTS.md"
HOME="$PROJ_HOME" "$INSTALL" --mode project --target "$PROJ" --profile kids-hebrew --tools cursor,claude,agents >/dev/null
assert_file "$PROJ/CLAUDE.md"
assert_file "$PROJ/AGENTS.md"
assert_file "$PROJ/.claude/skills/kids-edtech-a11y/SKILL.md"
assert_file "$PROJ/.cursor/rules/ui-rtl-system.mdc"
assert_absent "$PROJ/.cursor/rules/core-orchestrator.mdc"
assert_absent "$PROJ/.cursor/rules/devops-deploy.mdc"
assert_file "$PROJ/.hebrew-skills/templates/tokens.template.css"
grep -q "keep this" "$PROJ/CLAUDE.md" || fail "user CLAUDE.md content was dropped"
grep -q "name: keep" "$PROJ/AGENTS.md" || fail "user AGENTS.md content was dropped"
[ "$(count_marker "$PROJ/CLAUDE.md")" -eq 1 ] || fail "CLAUDE.md marker count"
[ "$(count_marker "$PROJ/AGENTS.md")" -eq 1 ] || fail "AGENTS.md marker count"
# Cursor+agents dedupe: the full router lives in AGENTS.md, not also in CLAUDE.md.
grep -q "Route by task" "$PROJ/AGENTS.md" || fail "AGENTS.md missing router"
if grep -q "Route by task" "$PROJ/CLAUDE.md"; then
  fail "CLAUDE.md duplicated the router"
fi
[ "$(backup_count "$PROJ/.hebrew-skills/backups")" -eq 2 ] || fail "expected backups of the two pre-existing files"
HOME="$PROJ_HOME" "$INSTALL" --mode project --target "$PROJ" --profile kids-hebrew --tools cursor,claude,agents >/dev/null
[ "$(count_marker "$PROJ/CLAUDE.md")" -eq 1 ] || fail "second install duplicated the block"
[ "$(backup_count "$PROJ/.hebrew-skills/backups")" -eq 2 ] || fail "second install added a backup"
[ "$(file_count "$PROJ_HOME")" -eq 0 ] || fail "project install wrote into HOME"

# 3. Owned-file backup and restore.
OWN="$TMP/own"
OWN_HOME="$TMP/own-home"
mkdir -p "$OWN_HOME" "$OWN/.cursor/rules"
printf 'USER RULE\n' >"$OWN/.cursor/rules/ui-rtl-system.mdc"
HOME="$OWN_HOME" "$INSTALL" --mode project --target "$OWN" --profile web --tools cursor >/dev/null
assert_file "$OWN/.cursor/rules/core-orchestrator.mdc"
grep -q "alwaysApply: true" "$OWN/.cursor/rules/core-orchestrator.mdc" || fail "cursor-only core should be alwaysApply"
backup_rule="$(find "$OWN/.hebrew-skills/backups" -name 'ui-rtl-system.mdc' -type f -print -quit)"
[ -n "$backup_rule" ] || fail "user rule was not backed up"
grep -q "USER RULE" "$backup_rule" || fail "backup does not contain the user rule"
if grep -q "USER RULE" "$OWN/.cursor/rules/ui-rtl-system.mdc"; then
  fail "installer left the old rule in place"
fi
HOME="$OWN_HOME" "$INSTALL" --uninstall --mode project --target "$OWN" >/dev/null
grep -q "USER RULE" "$OWN/.cursor/rules/ui-rtl-system.mdc" || fail "uninstall did not restore the user rule"
assert_absent "$OWN/.cursor/rules/core-orchestrator.mdc"
assert_absent "$OWN/.hebrew-skills/install-state.json"

# 4. A file we created is removed. A later edit outside the block survives.
EDIT="$TMP/edit"
EDIT_HOME="$TMP/edit-home"
mkdir -p "$EDIT_HOME" "$EDIT"
HOME="$EDIT_HOME" "$INSTALL" --mode project --target "$EDIT" --profile backend --tools claude >/dev/null
assert_file "$EDIT/CLAUDE.md"
assert_absent "$EDIT/AGENTS.md"
printf '\n# added later\n' >>"$EDIT/CLAUDE.md"
HOME="$EDIT_HOME" "$INSTALL" --uninstall --mode project --target "$EDIT" >/dev/null
grep -q "added later" "$EDIT/CLAUDE.md" || fail "uninstall dropped text outside the block"
if grep -q "hebrew-pro-agent-skills:begin" "$EDIT/CLAUDE.md"; then
  fail "uninstall left the managed block"
fi
HOME="$EDIT_HOME" "$INSTALL" --uninstall --mode project --target "$EDIT" >/dev/null

# 5. Modified owned file is kept.
MOD="$TMP/mod"
MOD_HOME="$TMP/mod-home"
mkdir -p "$MOD_HOME" "$MOD"
HOME="$MOD_HOME" "$INSTALL" --mode project --target "$MOD" --profile web --tools cursor >/dev/null
printf '\n/* user edit */\n' >>"$MOD/.cursor/rules/ui-rtl-system.mdc"
HOME="$MOD_HOME" "$INSTALL" --uninstall --mode project --target "$MOD" >/dev/null
grep -q "user edit" "$MOD/.cursor/rules/ui-rtl-system.mdc" || fail "modified rule was not kept"

# 6. Global mode uses tool directories under a fake HOME.
GLOB="$TMP/global-home"
GTARGET="$TMP/global-target"
mkdir -p "$GLOB" "$GTARGET"
HOME="$GLOB" "$INSTALL" --mode global --target "$GTARGET" --profile full --tools cursor,claude,copilot,windsurf,agents >/dev/null
assert_file "$GLOB/.claude/CLAUDE.md"
assert_file "$GLOB/.claude/skills/devops-deploy/SKILL.md"
assert_file "$GLOB/.cursor/rules/core-orchestrator.mdc"
assert_file "$GLOB/.copilot/copilot-instructions.md"
assert_file "$GLOB/.copilot/instructions/fullstack-architect.instructions.md"
assert_file "$GLOB/.devin/rules/ui-rtl-system.md"
assert_file "$GLOB/.codex/AGENTS.md"
assert_file "$GLOB/.gemini/GEMINI.md"
assert_absent "$GLOB/CLAUDE.md"
assert_absent "$GLOB/AGENTS.md"
assert_absent "$GLOB/.windsurf/rules/ui-rtl-system.md"
grep -q "disable-model-invocation: true" "$GLOB/.claude/skills/core-orchestrator/SKILL.md" || fail "global claude core still auto-invokes"
# Devin reads ~/.claude/CLAUDE.md, so the global windsurf core rule is omitted.
assert_absent "$GLOB/.devin/rules/core-orchestrator.md"
[ "$(file_count "$GTARGET")" -eq 0 ] || fail "global install wrote into --target"
HOME="$GLOB" "$INSTALL" --mode global --target "$GTARGET" --uninstall >/dev/null
assert_absent "$GLOB/.claude/CLAUDE.md"
assert_absent "$GLOB/.codex/AGENTS.md"
assert_absent "$GLOB/CLAUDE.md"

# 7. Windsurf-only global install lands in ~/.devin/rules and is always_on.
ONLY="$TMP/wind-home"
mkdir -p "$ONLY"
HOME="$ONLY" "$INSTALL" --mode global --target "$GTARGET" --profile web --tools windsurf >/dev/null
assert_file "$ONLY/.devin/rules/core-orchestrator.md"
grep -q "trigger: always_on" "$ONLY/.devin/rules/core-orchestrator.md" || fail "windsurf-only core is not always_on"
assert_absent "$ONLY/.claude/CLAUDE.md"

# 8. Bad arguments fail before writing.
BAD="$TMP/bad"
mkdir -p "$BAD"
set +e
HOME="$PROJ_HOME" "$INSTALL" --profile no-such --target "$BAD" >/dev/null 2>"$TMP/bad.err"
status="$?"
set -e
[ "$status" -eq 2 ] || fail "bad profile exited $status"
[ "$(file_count "$BAD")" -eq 0 ] || fail "bad profile wrote files"

echo "install.sh tests passed"

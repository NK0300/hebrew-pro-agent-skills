#!/usr/bin/env bash
# Install Hebrew-first agent skills into a project or a user home.
# Backups, merges, and per-tool paths live in script/install_apply.py so
# install.ps1 cannot drift. This wrapper validates the CLI and refuses
# unsafe targets before any file is touched.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install.sh [options]

Options:
  --mode project|global          Destination. Default: project
  --tools a,b,c                  cursor,claude,copilot,windsurf,agents
                                 Default: all of them
  --profile NAME                 full, web, backend, or kids-hebrew
                                 Default: full
  --target DIR                   Project directory. Default: current directory
  --dry-run                      Print actions and write nothing
  --uninstall                    Remove the managed block and files this
                                 installer owns. Restore a backup when a
                                 pre-existing file was replaced.
  --no-dedupe                    Give every selected tool a full always-on copy
  -h, --help                     Show this help

Global Claude instructions go to ~/.claude/CLAUDE.md, never ~/CLAUDE.md.
The installer merges a marked block into CLAUDE.md, AGENTS.md, GEMINI.md,
and copilot-instructions.md. It does not replace the rest of those files.
EOF
}

ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"

MODE="project"
TOOLS="cursor,claude,copilot,windsurf,agents"
PROFILE="full"
TARGET=""
DRY_RUN=0
UNINSTALL=0
NO_DEDUPE=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode)
      MODE="${2:?--mode needs a value}"
      shift 2
      ;;
    --mode=*)
      MODE="${1#*=}"
      shift
      ;;
    --tools)
      TOOLS="${2:?--tools needs a value}"
      shift 2
      ;;
    --tools=*)
      TOOLS="${1#*=}"
      shift
      ;;
    --profile)
      PROFILE="${2:?--profile needs a value}"
      shift 2
      ;;
    --profile=*)
      PROFILE="${1#*=}"
      shift
      ;;
    --target)
      TARGET="${2:?--target needs a value}"
      shift 2
      ;;
    --target=*)
      TARGET="${1#*=}"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --uninstall)
      UNINSTALL=1
      shift
      ;;
    --no-dedupe)
      NO_DEDUPE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$MODE" in
  project|global) ;;
  *)
    echo "Invalid mode: $MODE" >&2
    exit 2
    ;;
esac

case "$PROFILE" in
  web|backend|full|kids-hebrew) ;;
  *)
    echo "Invalid profile: $PROFILE" >&2
    exit 2
    ;;
esac

validate_tools() {
  rest="$1"
  part=""
  if [ -z "$rest" ]; then
    echo "--tools must list at least one tool" >&2
    return 2
  fi
  while [ -n "$rest" ]; do
    case "$rest" in
      *,*)
        part="${rest%%,*}"
        rest="${rest#*,}"
        ;;
      *)
        part="$rest"
        rest=""
        ;;
    esac
    case "$part" in
      cursor|claude|copilot|windsurf|agents) ;;
      *)
        echo "unknown tool: $part" >&2
        return 2
        ;;
    esac
  done
}

validate_tools "$TOOLS"

if [ -z "${HOME:-}" ]; then
  echo "HOME is required" >&2
  exit 1
fi

if [ -z "$TARGET" ]; then
  TARGET="$(pwd)"
fi

if [ "$TARGET" = "/" ] || [ "$HOME" = "/" ]; then
  echo "Refusing to install onto /" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

args=(
  "$ROOT/script/install_apply.py"
  --repo "$ROOT"
  --mode "$MODE"
  --tools "$TOOLS"
  --profile "$PROFILE"
  --target "$TARGET"
  --home "$HOME"
)

if [ "$DRY_RUN" -eq 1 ]; then
  args+=(--dry-run)
fi
if [ "$UNINSTALL" -eq 1 ]; then
  args+=(--uninstall)
fi
if [ "$NO_DEDUPE" -eq 1 ]; then
  args+=(--no-dedupe)
fi

exec python3 "${args[@]}"

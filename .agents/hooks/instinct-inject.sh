#!/usr/bin/env bash
# Hook: Instinct inject (SessionStart)
# Prints the active-instincts block to stdout; Claude Code injects it as context.
# Exit 0 always. Prints nothing when disabled or when there is nothing to show.

[ -n "${INSTINCTS_SKIP:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$HOOK_DIR/../.." && pwd)}"
[ -f "$ROOT/.instincts-off" ] && exit 0
[ -f "$ROOT/scripts/instincts/instinct.py" ] || exit 0

cat > /dev/null  # drain stdin
python3 "$ROOT/scripts/instincts/instinct.py" --root "$ROOT" inject 2>/dev/null
exit 0

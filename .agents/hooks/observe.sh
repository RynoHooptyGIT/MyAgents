#!/usr/bin/env bash
# Hook: Instinct capture
# UserPromptSubmit → `observe.sh prompt`; PostToolUse → `observe.sh tool`.
# Appends one JSONL line to team/_memory/_learnings/observations.jsonl.
# Exit 0 always. NEVER writes to stdout (UserPromptSubmit stdout is injected into context).

[ -n "${INSTINCTS_SKIP:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$HOOK_DIR/../.." && pwd)}"
[ -f "$ROOT/.instincts-off" ] && exit 0
[ -f "$ROOT/scripts/instincts/observe.py" ] || exit 0

python3 "$ROOT/scripts/instincts/observe.py" "${1:-tool}" --root "$ROOT" >/dev/null 2>&1
exit 0

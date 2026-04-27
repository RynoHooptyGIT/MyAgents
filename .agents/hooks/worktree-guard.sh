#!/usr/bin/env bash
# Hook: Worktree Guard
# Blocks git branch operations (checkout, switch, merge, rebase) when
# running in the main repo instead of a worktree.
# Exit 0 = allow, Exit 2 = block (with message on stderr)

set -euo pipefail

INPUT="$(cat)"

CMD="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null)" || \
CMD="$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')"

[ -z "$CMD" ] && exit 0

case "$CMD" in
  git\ checkout*|git\ switch*|git\ merge*|git\ rebase*)
    ;;
  *)
    exit 0
    ;;
esac

GIT_DIR="$(git rev-parse --git-dir 2>/dev/null)" || exit 0
GIT_COMMON="$(git rev-parse --git-common-dir 2>/dev/null)" || exit 0

if [ "$GIT_DIR" = "$GIT_COMMON" ]; then
  echo "BLOCKED: Branch operations (checkout/switch/merge/rebase) are not allowed in the main repo." >&2
  echo "Use your assigned worktree instead. Run /agent-coordinator to set one up." >&2
  exit 2
fi

exit 0

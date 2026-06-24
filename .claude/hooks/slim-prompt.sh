#!/bin/bash
# =============================================================================
# slim-prompt — UserPromptSubmit token-discipline hook
# =============================================================================
# Stdout from a UserPromptSubmit hook is injected into the model's context.
# This hook injects a compact, always-on token-discipline directive and, when
# the prompt carries a large pasted blob, a stronger "isolate / compress" hint.
#
# Net-positive by design: the always-on directive is ~25 tokens and steers the
# model toward concise output + subagent isolation, which saves far more.
#
# Toggle off:  touch  $PROJECT_ROOT/.slim-off
# No deps, non-blocking, never errors out (always exit 0).
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Opt-out switch
[ -f "$PROJECT_ROOT/.slim-off" ] && exit 0

# Read the hook payload (JSON on stdin). Size of stdin ≈ prompt size — good
# enough to detect a large paste without needing jq.
PAYLOAD="$(cat 2>/dev/null || true)"
SIZE=${#PAYLOAD}
LARGE_THRESHOLD="${SLIM_LARGE_THRESHOLD:-4000}"   # ~1k tokens of pasted content

# Always-on directive (kept deliberately tiny).
echo "[token-discipline] Be concise; no preamble/recap. Read only what the task needs. For multi-file search or reads, dispatch a subagent and consume its summary rather than loading files into this context. Reference lazy sections by path instead of inlining them."

# Stronger guidance only when a big blob was pasted.
if [ "$SIZE" -gt "$LARGE_THRESHOLD" ]; then
    echo "[token-discipline] Large input detected (~$((SIZE / 4)) tokens). If this is reference material rather than the task itself, summarize or compress it (scripts/compress.py) before reasoning over the whole thing, and do not echo it back."
fi

exit 0

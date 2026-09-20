#!/usr/bin/env bash
set -e

HOOK=".agents/hooks/observe.sh"
PASS=0
FAIL=0
ROOT="$(pwd)"
OBS="team/_memory/_learnings/observations.jsonl"

setup() { rm -f "$OBS" "$OBS.1" .instincts-off; }
teardown() { rm -f "$OBS" "$OBS.1" .instincts-off; }

check() {
  local desc="$1" ok="$2"
  if [ "$ok" = "1" ]; then echo "  PASS: $desc"; PASS=$((PASS + 1)); else echo "  FAIL: $desc"; FAIL=$((FAIL + 1)); fi
}

echo "=== Observe Hook Tests ==="
setup
trap teardown EXIT

OUT="$(echo '{"session_id":"s1","prompt":"hello"}' | CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" prompt)"; RC=$?
check "prompt event exits 0 and prints nothing" "$([ $RC -eq 0 ] && [ -z "$OUT" ] && echo 1 || echo 0)"
check "prompt event written" "$(grep -q '"event": *"prompt"' "$OBS" 2>/dev/null && echo 1 || echo 0)"

echo '{"session_id":"s1","tool_name":"Bash","tool_input":{"command":"echo API_KEY=abc"},"tool_response":{"exit_code":1,"stdout":"boom"}}' \
  | CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" tool
check "tool event scrubbed" "$(grep -q 'API_KEY=\[REDACTED\]' "$OBS" && echo 1 || echo 0)"
check "tool event flagged is_error" "$(grep -q '"is_error": *true' "$OBS" && echo 1 || echo 0)"

echo 'not json' | CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" tool; RC=$?
check "bad json exits 0" "$([ $RC -eq 0 ] && echo 1 || echo 0)"

BEFORE="$(wc -l < "$OBS")"
touch .instincts-off
echo '{"prompt":"x"}' | CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" prompt
check ".instincts-off suppresses capture" "$([ "$(wc -l < "$OBS")" -eq "$BEFORE" ] && echo 1 || echo 0)"
rm -f .instincts-off

echo '{"prompt":"x"}' | INSTINCTS_SKIP=1 CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" prompt
check "INSTINCTS_SKIP suppresses capture" "$([ "$(wc -l < "$OBS")" -eq "$BEFORE" ] && echo 1 || echo 0)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

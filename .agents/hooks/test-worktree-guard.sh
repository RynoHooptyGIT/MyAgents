#!/usr/bin/env bash
set -e

HOOK=".agents/hooks/worktree-guard.sh"
PASS=0
FAIL=0

run_test() {
  local desc="$1" input="$2" expected_exit="$3"
  local actual_exit=0
  echo "$input" | bash "$HOOK" > /dev/null 2>&1 || actual_exit=$?
  if [ "$actual_exit" -eq "$expected_exit" ]; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc (expected exit $expected_exit, got $actual_exit)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Worktree Guard Tests ==="
run_test "non-git command allowed" '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' 0
run_test "git status allowed" '{"tool_name":"Bash","tool_input":{"command":"git status"}}' 0
run_test "git log allowed" '{"tool_name":"Bash","tool_input":{"command":"git log --oneline -5"}}' 0

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

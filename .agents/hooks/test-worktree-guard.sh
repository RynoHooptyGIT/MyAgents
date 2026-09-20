#!/usr/bin/env bash
set -e

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/worktree-guard.sh"
PASS=0
FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

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

# Temp repo: main checkout + one worktree
git -C "$TMP" init -q main
git -C "$TMP/main" -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
git -C "$TMP/main" worktree add -q "$TMP/wt" -b agent/test/wt

cd "$TMP/main"
run_test "git checkout in main checkout blocked" '{"tool_name":"Bash","tool_input":{"command":"git checkout -b feature"}}' 2
run_test "git merge in main checkout blocked" '{"tool_name":"Bash","tool_input":{"command":"git merge agent/test/wt"}}' 2
run_test "git status in main checkout allowed" '{"tool_name":"Bash","tool_input":{"command":"git status"}}' 0

cd "$TMP/wt"
run_test "git checkout in worktree allowed" '{"tool_name":"Bash","tool_input":{"command":"git checkout -b feature"}}' 0
run_test "git rebase in worktree allowed" '{"tool_name":"Bash","tool_input":{"command":"git rebase main"}}' 0
cd - > /dev/null

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

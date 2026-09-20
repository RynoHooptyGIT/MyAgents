#!/usr/bin/env bash
set -e

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/claim-check.sh"
PASS=0
FAIL=0

# Hermetic: legacy cases run against $TMP/legacy (a fake main checkout with its own
# .agents/), never the repo's real .agents/.
setup() {
  mkdir -p "$TMP/legacy/.agents/claims" "$TMP/legacy/.agents/registry"
  cat > "$TMP/legacy/.agents/claims/feature-auth.yaml" << 'EOF'
agent_id: other1
branch: agent/other1/auth
story_id: "24-3"
claimed_at: 2026-04-26T14:30:00Z
owned_paths:
  - backend/app/auth/
  - backend/app/models/user.py
description: "Auth system"
EOF
  echo "self01" > "$TMP/legacy/.agents/registry/.current-agent-id-$$"
  echo "$TMP/legacy" > "$TMP/legacy/.agents/registry/.coord-root-$$"
}

teardown() {
  rm -rf "$TMP"
}

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

echo "=== Claim Check Tests ==="
TMP="$(mktemp -d)"
setup
trap teardown EXIT

# --- Legacy single-instance cases (PID files in registry, relative paths, cwd = fake main checkout) ---
run_test "edit claimed file blocked" "{\"cwd\":\"$TMP/legacy\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"backend/app/auth/router.py\"}}" 2
run_test "edit exact claimed file blocked" "{\"cwd\":\"$TMP/legacy\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"backend/app/models/user.py\"}}" 2
run_test "edit unclaimed file allowed" "{\"cwd\":\"$TMP/legacy\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"frontend/src/App.tsx\"}}" 0
run_test "edit .agents/ file allowed" "{\"cwd\":\"$TMP/legacy\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\".agents/decisions/test.yaml\"}}" 0

# --- Two-instance cases: worktree = identity ---
# Coordination root is a temp dir with the same claim; two worktrees A (other1, owns auth) and B (agentb).
mkdir -p "$TMP/.agents/claims" "$TMP/.agents/registry" "$TMP/wt/a/backend/app/auth" "$TMP/wt/b/backend/app/auth"
cp "$TMP/legacy/.agents/claims/feature-auth.yaml" "$TMP/.agents/claims/"
echo "other1" > "$TMP/wt/a/.agent-id"; echo "$TMP" > "$TMP/wt/a/.agent-coord-root"
echo "agentb" > "$TMP/wt/b/.agent-id"; echo "$TMP" > "$TMP/wt/b/.agent-coord-root"

run_test "B editing A's claimed path (abs path) blocked" "{\"cwd\":\"$TMP/wt/b\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TMP/wt/b/backend/app/auth/router.py\"}}" 2
run_test "A editing its own claimed path (abs path) allowed" "{\"cwd\":\"$TMP/wt/a\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TMP/wt/a/backend/app/auth/router.py\"}}" 0
run_test "B editing A's claimed path (rel path, cwd=B) blocked" "{\"cwd\":\"$TMP/wt/b\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"backend/app/auth/router.py\"}}" 2
run_test "A editing its own claimed path (rel path, cwd=A) allowed" "{\"cwd\":\"$TMP/wt/a\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"backend/app/auth/router.py\"}}" 0
run_test "B editing unclaimed path allowed" "{\"cwd\":\"$TMP/wt/b\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TMP/wt/b/frontend/App.tsx\"}}" 0
run_test "B editing coordination files allowed" "{\"cwd\":\"$TMP/wt/b\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/.agents/requests/b-to-a.yaml\"}}" 0

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

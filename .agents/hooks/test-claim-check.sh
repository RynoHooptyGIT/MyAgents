#!/usr/bin/env bash
set -e

HOOK=".agents/hooks/claim-check.sh"
PASS=0
FAIL=0
COORD_ROOT="$(pwd)"

setup() {
  mkdir -p .agents/claims .agents/registry
  cat > .agents/claims/feature-auth.yaml << 'EOF'
agent_id: other1
branch: agent/other1/auth
story_id: "24-3"
claimed_at: 2026-04-26T14:30:00Z
owned_paths:
  - backend/app/auth/
  - backend/app/models/user.py
description: "Auth system"
EOF
  echo "self01" > .agents/registry/.current-agent-id-$$
  echo "$COORD_ROOT" > .agents/registry/.coord-root-$$
}

teardown() {
  rm -f .agents/claims/feature-auth.yaml
  rm -f .agents/registry/.current-agent-id-$$
  rm -f .agents/registry/.coord-root-$$
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
setup
trap teardown EXIT

run_test "edit claimed file blocked" '{"tool_name":"Edit","tool_input":{"file_path":"backend/app/auth/router.py"}}' 2
run_test "edit exact claimed file blocked" '{"tool_name":"Edit","tool_input":{"file_path":"backend/app/models/user.py"}}' 2
run_test "edit unclaimed file allowed" '{"tool_name":"Edit","tool_input":{"file_path":"frontend/src/App.tsx"}}' 0
run_test "edit .agents/ file allowed" '{"tool_name":"Write","tool_input":{"file_path":".agents/decisions/test.yaml"}}' 0

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

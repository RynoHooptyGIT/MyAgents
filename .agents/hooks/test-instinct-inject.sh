#!/usr/bin/env bash
set -e

HOOK=".agents/hooks/instinct-inject.sh"
PASS=0
FAIL=0
ROOT="$(pwd)"
DIR="team/_memory/_learnings/instincts"
USER_DIR="$(mktemp -d)"

setup() {
  mkdir -p "$DIR"
  cat > "$DIR/zz-test-inject.yaml" << 'EOF'
id: "zz-test-inject"
trigger: "when testing the inject hook"
action: "print this line"
confidence: 0.9
domain: "tooling"
scope: "project"
status: "active"
source: "test"
evidence:
  - "harness"
observed_count: 11
first_seen: "2026-09-19"
last_seen: "2099-01-01"
EOF
}
teardown() { rm -f "$DIR/zz-test-inject.yaml" .instincts-off; rm -rf "$USER_DIR"; }
check() {
  local desc="$1" ok="$2"
  if [ "$ok" = "1" ]; then echo "  PASS: $desc"; PASS=$((PASS + 1)); else echo "  FAIL: $desc"; FAIL=$((FAIL + 1)); fi
}
run_hook() { echo '{"session_id":"s","source":"startup"}' | INSTINCTS_USER_DIR="$USER_DIR" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"; }

echo "=== Instinct Inject Hook Tests ==="
setup
trap teardown EXIT

OUT="$(run_hook)"; RC=$?
check "exit 0" "$([ $RC -eq 0 ] && echo 1 || echo 0)"
check "prints [instincts] header" "$(echo "$OUT" | grep -q '^\[instincts\]' && echo 1 || echo 0)"
check "prints the active instinct" "$(echo "$OUT" | grep -q 'when testing the inject hook → print this line' && echo 1 || echo 0)"

touch .instincts-off
OUT="$(run_hook)"
check ".instincts-off prints nothing" "$([ -z "$OUT" ] && echo 1 || echo 0)"
rm -f .instincts-off

OUT="$(echo '{}' | INSTINCTS_SKIP=1 CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK")"
check "INSTINCTS_SKIP prints nothing" "$([ -z "$OUT" ] && echo 1 || echo 0)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

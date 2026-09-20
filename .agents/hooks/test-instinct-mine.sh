#!/usr/bin/env bash
set -e

HOOK=".agents/hooks/instinct-mine.sh"
PASS=0
FAIL=0
ROOT="$(pwd)"
LEARN="team/_memory/_learnings"
SHIM_DIR="$(mktemp -d)"
SHIM_LOG="$SHIM_DIR/claude.calls"

setup() {
  mkdir -p "$LEARN/instincts"
  rm -f "$LEARN/observations.jsonl" "$LEARN/.instinct-watermark" "$LEARN/.miner.lock" "$LEARN/miner.log" "$LEARN/.candidates.json" "$LEARN/instincts/mined-from-shim.yaml"
  cat > "$SHIM_DIR/claude" << 'EOF'
#!/usr/bin/env bash
echo "$@" >> "${SHIM_LOG:?}"
cat > /dev/null
echo 'Sure! [{"id":"mined-from-shim","trigger":"when testing","action":"use the shim","observed_count":3,"evidence":["e"]}]'
EOF
  chmod +x "$SHIM_DIR/claude"
}
teardown() {
  rm -f "$LEARN/observations.jsonl" "$LEARN/.instinct-watermark" "$LEARN/.miner.lock" "$LEARN/miner.log" "$LEARN/.candidates.json" "$LEARN/instincts/mined-from-shim.yaml"
  rm -rf "$SHIM_DIR"
}
check() {
  local desc="$1" ok="$2"
  if [ "$ok" = "1" ]; then echo "  PASS: $desc"; PASS=$((PASS + 1)); else echo "  FAIL: $desc"; FAIL=$((FAIL + 1)); fi
}
run_hook() { echo '{"session_id":"s","stop_hook_active":false}' | SHIM_LOG="$SHIM_LOG" PATH="$SHIM_DIR:$PATH" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"; }
wait_for() { local f="$1" n=0; while [ ! -e "$f" ] && [ $n -lt 50 ]; do sleep 0.1; n=$((n + 1)); done; [ -e "$f" ]; }
wait_gone() { local f="$1" n=0; while [ -e "$f" ] && [ $n -lt 50 ]; do sleep 0.1; n=$((n + 1)); done; [ ! -e "$f" ]; }

echo "=== Instinct Mine Hook Tests ==="
setup
trap teardown EXIT

# 1. below threshold: no spawn, watermark advanced
printf '%s\n' '{"event":"prompt","text":"no, use gh"}' > "$LEARN/observations.jsonl"
run_hook
check "below threshold: no claude call" "$([ ! -f "$SHIM_LOG" ] && echo 1 || echo 0)"
check "below threshold: watermark written" "$([ -s "$LEARN/.instinct-watermark" ] && echo 1 || echo 0)"
check "below threshold: lock released" "$([ ! -f "$LEARN/.miner.lock" ] && echo 1 || echo 0)"

# 2. at threshold: spawn once, ingest lands, lock cleared, hook returns fast
printf '%s\n' '{"event":"prompt","text":"no, use gh"}' '{"event":"prompt","text":"actually do X"}' '{"event":"prompt","text":"stop, wrong file"}' >> "$LEARN/observations.jsonl"
START=$(date +%s)
run_hook
check "hook returns in < 3s" "$([ $(( $(date +%s) - START )) -lt 3 ] && echo 1 || echo 0)"
check "claude called once" "$(wait_for "$SHIM_LOG" && [ "$(wc -l < "$SHIM_LOG")" -eq 1 ] && echo 1 || echo 0)"
check "claude called with -p and --model" "$(grep -q -- '-p' "$SHIM_LOG" && grep -q -- '--model' "$SHIM_LOG" && echo 1 || echo 0)"
check "instinct ingested as pending" "$(wait_for "$LEARN/instincts/mined-from-shim.yaml" && grep -q 'status: "pending"' "$LEARN/instincts/mined-from-shim.yaml" && echo 1 || echo 0)"
check "lock removed after miner" "$(wait_gone "$LEARN/.miner.lock" && echo 1 || echo 0)"

# 3. live lock: skip
echo "99999 $(date +%s)" > "$LEARN/.miner.lock"
printf '%s\n' '{"event":"prompt","text":"no, a"}' '{"event":"prompt","text":"no, b"}' '{"event":"prompt","text":"no, c"}' >> "$LEARN/observations.jsonl"
run_hook
check "live lock: no second claude call" "$([ "$(wc -l < "$SHIM_LOG")" -eq 1 ] && echo 1 || echo 0)"

# 4. stale lock: proceeds
echo "99999 $(( $(date +%s) - 700 ))" > "$LEARN/.miner.lock"
run_hook
check "stale lock: claude called again" "$(sleep 1; [ "$(wc -l < "$SHIM_LOG")" -eq 2 ] && echo 1 || echo 0)"
wait_gone "$LEARN/.miner.lock" || true

# 5. stop_hook_active guard and INSTINCTS_SKIP
echo '{"stop_hook_active":true}' | SHIM_LOG="$SHIM_LOG" PATH="$SHIM_DIR:$PATH" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"
echo '{}' | INSTINCTS_SKIP=1 SHIM_LOG="$SHIM_LOG" PATH="$SHIM_DIR:$PATH" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"
check "guards: no extra claude calls" "$([ "$(wc -l < "$SHIM_LOG")" -eq 2 ] && echo 1 || echo 0)"

# 6. no claude on PATH: logs and exits 0
rm -f "$SHIM_DIR/claude"
printf '%s\n' '{"event":"prompt","text":"no, a"}' '{"event":"prompt","text":"no, b"}' '{"event":"prompt","text":"no, c"}' >> "$LEARN/observations.jsonl"
echo '{}' | PATH="$SHIM_DIR:$(dirname "$(command -v python3)"):/usr/bin:/bin" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"; RC=$?
check "missing claude: exit 0 and logged" "$([ $RC -eq 0 ] && grep -q 'claude not on PATH' "$LEARN/miner.log" && echo 1 || echo 0)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

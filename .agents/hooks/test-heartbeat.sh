#!/usr/bin/env bash
set -e

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/heartbeat.sh"
PASS=0
FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

check() { if [ "$2" -eq 0 ]; then echo "  PASS: $1"; PASS=$((PASS+1)); else echo "  FAIL: $1"; FAIL=$((FAIL+1)); fi; }

echo "=== Heartbeat Tests ==="
mkdir -p "$TMP/.agents/registry" "$TMP/.agents/status" "$TMP/wt/b"
echo "agentb" > "$TMP/wt/b/.agent-id"; echo "$TMP" > "$TMP/wt/b/.agent-coord-root"
printf 'agent_id: agentb\nlast_heartbeat: 2020-01-01T00:00:00Z\nstatus: active\n' > "$TMP/.agents/registry/agent-agentb.yaml"
printf 'agent_id: agentb\nlast_updated: 2020-01-01T00:00:00Z\n' > "$TMP/.agents/status/agent-agentb.yaml"

INPUT="{\"cwd\":\"$TMP/wt/b\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ls\"}}"

# 19 calls: counter increments, no heartbeat yet
for i in $(seq 1 19); do echo "$INPUT" | bash "$HOOK"; done
check "counter reaches 19" "$([ "$(cat "$TMP/.agents/registry/agentb.counter")" = "19" ]; echo $?)"
check "heartbeat untouched before 20th call" "$(grep -q '^last_heartbeat: 2020-01-01T00:00:00Z$' "$TMP/.agents/registry/agent-agentb.yaml"; echo $?)"

# 20th call: heartbeat written, counter reset
echo "$INPUT" | bash "$HOOK"
check "counter resets to 0" "$([ "$(cat "$TMP/.agents/registry/agentb.counter")" = "0" ]; echo $?)"
check "registry last_heartbeat updated" "$(! grep -q '^last_heartbeat: 2020-01-01T00:00:00Z$' "$TMP/.agents/registry/agent-agentb.yaml"; echo $?)"
check "registry other lines preserved" "$(grep -q '^status: active$' "$TMP/.agents/registry/agent-agentb.yaml"; echo $?)"
check "status last_updated updated" "$(! grep -q '^last_updated: 2020-01-01T00:00:00Z$' "$TMP/.agents/status/agent-agentb.yaml"; echo $?)"
check "no sed backup files created" "$([ -z "$(ls "$TMP/.agents/registry" | grep -v -e '^agent-agentb.yaml$' -e '^agentb.counter$')" ]; echo $?)"

# No identity → exit 0, nothing written
rc=0; echo '{"cwd":"/","tool_name":"Bash","tool_input":{"command":"ls"}}' | bash "$HOOK" || rc=$?
check "no identity exits 0" "$([ "$rc" -eq 0 ]; echo $?)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

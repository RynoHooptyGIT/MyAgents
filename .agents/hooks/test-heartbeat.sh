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

# Configured heartbeat_interval_calls: 3 → stamps on the 3rd call, not the 20th.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP2="$(mktemp -d)"
mkdir -p "$TMP2/.agents/registry" "$TMP2/.agents/status" "$TMP2/wt/c" "$TMP2/scripts/lib"
cp "$REPO_ROOT/scripts/lib/config.py" "$TMP2/scripts/lib/config.py"
printf 'coordination:\n  heartbeat_interval_calls: 3\n' > "$TMP2/.agents/config.yaml"
echo "agentc" > "$TMP2/wt/c/.agent-id"; echo "$TMP2" > "$TMP2/wt/c/.agent-coord-root"
printf 'agent_id: agentc\nlast_heartbeat: 2020-01-01T00:00:00Z\nstatus: active\n' > "$TMP2/.agents/registry/agent-agentc.yaml"
printf 'agent_id: agentc\nlast_updated: 2020-01-01T00:00:00Z\n' > "$TMP2/.agents/status/agent-agentc.yaml"

INPUT2="{\"cwd\":\"$TMP2/wt/c\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ls\"}}"

echo "$INPUT2" | bash "$HOOK"
echo "$INPUT2" | bash "$HOOK"
check "configured interval: heartbeat untouched before 3rd call" "$(grep -q '^last_heartbeat: 2020-01-01T00:00:00Z$' "$TMP2/.agents/registry/agent-agentc.yaml"; echo $?)"

echo "$INPUT2" | bash "$HOOK"
check "configured interval: counter resets to 0 on 3rd call" "$([ "$(cat "$TMP2/.agents/registry/agentc.counter")" = "0" ]; echo $?)"
check "configured interval: registry last_heartbeat updated on 3rd call" "$(! grep -q '^last_heartbeat: 2020-01-01T00:00:00Z$' "$TMP2/.agents/registry/agent-agentc.yaml"; echo $?)"
rm -rf "$TMP2"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1

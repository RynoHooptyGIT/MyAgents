#!/usr/bin/env bash
# Hook: Heartbeat
# Updates agent's last_heartbeat timestamp every ~20 tool calls.
# Exit 0 always (never blocks).

COORD_ROOT=""
for rootfile in .agents/registry/.coord-root-* ; do
  [ -f "$rootfile" ] && COORD_ROOT="$(cat "$rootfile")" && break
done
[ -z "$COORD_ROOT" ] && exit 0

MY_ID=""
for idfile in "$COORD_ROOT/.agents/registry/.current-agent-id-"* ; do
  [ -f "$idfile" ] && MY_ID="$(cat "$idfile")" && break
done
[ -z "$MY_ID" ] && exit 0

COUNTER_FILE="$COORD_ROOT/.agents/registry/${MY_ID}.counter"
REGISTRY_FILE="$COORD_ROOT/.agents/registry/agent-${MY_ID}.yaml"
STATUS_FILE="$COORD_ROOT/.agents/status/agent-${MY_ID}.yaml"

COUNT=0
[ -f "$COUNTER_FILE" ] && COUNT="$(cat "$COUNTER_FILE")"
COUNT=$((COUNT + 1))

if [ "$COUNT" -lt 20 ]; then
  echo "$COUNT" > "$COUNTER_FILE"
  exit 0
fi

echo "0" > "$COUNTER_FILE"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [ -f "$REGISTRY_FILE" ]; then
  sed -i '' "s/^last_heartbeat:.*$/last_heartbeat: $NOW/" "$REGISTRY_FILE" 2>/dev/null || true
fi

if [ -f "$STATUS_FILE" ]; then
  sed -i '' "s/^last_updated:.*$/last_updated: $NOW/" "$STATUS_FILE" 2>/dev/null || true
fi

exit 0

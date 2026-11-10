#!/usr/bin/env bash
# Hook: Heartbeat
# Updates agent's last_heartbeat timestamp every coordination.heartbeat_interval_calls
# tool calls (default 20; falls back to 20 with no python3 or no config).
# Exit 0 always (never blocks).

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-identity.sh
. "$HOOK_DIR/lib-identity.sh"

INPUT="$(cat)"
CWD="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null)" || CWD=""
FILE_PATH="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)" || FILE_PATH=""
[ -z "$CWD" ] && CWD="$PWD"

resolve_identity "$FILE_PATH" "$CWD"
[ -z "$COORD_ROOT" ] && exit 0
[ -z "$MY_ID" ] && exit 0

COUNTER_FILE="$COORD_ROOT/.agents/registry/${MY_ID}.counter"
REGISTRY_FILE="$COORD_ROOT/.agents/registry/agent-${MY_ID}.yaml"
STATUS_FILE="$COORD_ROOT/.agents/status/agent-${MY_ID}.yaml"

COUNT=0
[ -f "$COUNTER_FILE" ] && COUNT="$(cat "$COUNTER_FILE")"
case "$COUNT" in ''|*[!0-9]*) COUNT=0 ;; esac
COUNT=$((COUNT + 1))

INTERVAL="$(python3 "$COORD_ROOT/scripts/lib/config.py" --root "$COORD_ROOT" --section coordination --default-json '{"heartbeat_interval_calls":20}' heartbeat_interval_calls 2>/dev/null || echo 20)"
case "$INTERVAL" in ''|*[!0-9]*) INTERVAL=20 ;; esac

if [ "$COUNT" -lt "$INTERVAL" ]; then
  echo "$COUNT" > "$COUNTER_FILE"
  exit 0
fi

echo "0" > "$COUNTER_FILE"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Portable in-place edit (BSD and GNU sed): write to a temp file, then move.
replace_line() {  # file, key, value
  local tmp
  [ -f "$1" ] || return 0
  tmp="$(mktemp)" || return 0
  sed "s/^$2:.*$/$2: $3/" "$1" > "$tmp" && mv "$tmp" "$1" || rm -f "$tmp"
}

replace_line "$REGISTRY_FILE" "last_heartbeat" "$NOW"
replace_line "$STATUS_FILE" "last_updated" "$NOW"

exit 0

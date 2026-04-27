#!/usr/bin/env bash
# Hook: Claim Check
# Blocks edits to files claimed by another agent.
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

INPUT="$(cat)"

FILE_PATH="$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)" || \
FILE_PATH="$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')"

[ -z "$FILE_PATH" ] && exit 0

case "$FILE_PATH" in
  *.agents/*|*/.agents/*) exit 0 ;;
esac

COORD_ROOT=""
for pidfile in .agents/registry/.coord-root-* ; do
  [ -f "$pidfile" ] && COORD_ROOT="$(cat "$pidfile")" && break
done
[ -z "$COORD_ROOT" ] && COORD_ROOT="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null | sed 's|/.git$||')" || true
[ -z "$COORD_ROOT" ] && exit 0

CLAIMS_DIR="$COORD_ROOT/.agents/claims"
[ -d "$CLAIMS_DIR" ] || exit 0

MY_ID=""
for idfile in "$COORD_ROOT/.agents/registry/.current-agent-id-"* ; do
  [ -f "$idfile" ] && MY_ID="$(cat "$idfile")" && break
done

REL_PATH="$FILE_PATH"
REL_PATH="${REL_PATH#$COORD_ROOT/}"
REL_PATH="${REL_PATH#/}"

for claim in "$CLAIMS_DIR"/*.yaml; do
  [ -f "$claim" ] || continue
  CLAIM_AGENT="$(grep '^agent_id:' "$claim" | head -1 | sed 's/agent_id:[[:space:]]*//')"
  CLAIM_STORY="$(grep '^story_id:' "$claim" | head -1 | sed 's/story_id:[[:space:]]*//' | tr -d '"')"
  [ "$CLAIM_AGENT" = "$MY_ID" ] && continue

  while IFS= read -r owned_path; do
    owned_path="$(echo "$owned_path" | sed 's/^[[:space:]]*-[[:space:]]*//' | tr -d '[:space:]')"
    [ -z "$owned_path" ] && continue
    case "$REL_PATH" in
      "$owned_path"*|"$owned_path")
        echo "BLOCKED: File '$REL_PATH' is claimed by agent $CLAIM_AGENT (story $CLAIM_STORY)." >&2
        echo "To coordinate, write a request to .agents/requests/ or wait for their claim to release." >&2
        exit 2
        ;;
    esac
  done < <(grep '^  - ' "$claim")
done

exit 0

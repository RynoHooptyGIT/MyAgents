#!/usr/bin/env bash
# Hook: Instinct miner (Stop)
# Pre-filters new observations; only when enough candidates exist, spawns a DETACHED
# `claude -p` (Haiku) whose JSON output is piped into `instinct.py ingest`.
# The watermark advances only when a miner spawns (so sparse corrections accumulate across
# turns) or when the unmined backlog exceeds 2 MB (safety valve).
# The miner runs with no built-in tools and no MCP servers, so no hooks fire inside it.
# Exit 0 always. Returns immediately; the miner runs in the background and removes the lock.

[ -n "${INSTINCTS_SKIP:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$HOOK_DIR/../.." && pwd)}"
[ -f "$ROOT/.instincts-off" ] && exit 0
[ -f "$ROOT/scripts/instincts/prefilter.py" ] || exit 0

INPUT="$(cat)"
case "$INPUT" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;; esac

LEARN="$ROOT/team/_memory/_learnings"
mkdir -p "$LEARN" 2>/dev/null || exit 0
LOG="$LEARN/miner.log"
LOCK="$LEARN/.miner.lock"
CAND="$LEARN/.candidates.json"
WATERMARK="$LEARN/.instinct-watermark"
BACKLOG_MAX=2097152   # 2 MB: advance the watermark without mining past this much unmined data
PROMPT_FILE="$ROOT/team/prompts/instinct-observer.md"
STAMP() { date -u +%Y-%m-%dT%H:%M:%SZ; }

read -r ENABLED MODEL MIN_C <<< "$(python3 "$ROOT/scripts/instincts/config.py" --root "$ROOT" enabled model min_candidates 2>/dev/null | tr '\n' ' ')"
[ "$ENABLED" = "True" ] || exit 0

if ! command -v claude >/dev/null 2>&1; then
  echo "$(STAMP) skip: claude not on PATH" >> "$LOG"
  exit 0
fi

if [ -f "$LOCK" ]; then
  LOCK_TS="$(cut -d' ' -f2 "$LOCK" 2>/dev/null)"
  NOW="$(date +%s)"
  if [ -n "$LOCK_TS" ] && [ $((NOW - LOCK_TS)) -lt 600 ]; then
    exit 0
  fi
  echo "$(STAMP) stale lock overwritten" >> "$LOG"
fi
echo "$$ $(date +%s)" > "$LOCK"

if ! python3 "$ROOT/scripts/instincts/prefilter.py" --root "$ROOT" > "$CAND" 2>> "$LOG"; then
  rm -f "$LOCK"
  exit 0
fi
read -r COUNT NEW_OFF START_OFF <<< "$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d.get("count",0),d.get("new_offset",0),d.get("start_offset",0))' "$CAND" 2>/dev/null || echo "0 0 0")"
if [ "${COUNT:-0}" -lt "${MIN_C:-3}" ]; then
  if [ $((${NEW_OFF:-0} - ${START_OFF:-0})) -gt "$BACKLOG_MAX" ]; then
    echo "$NEW_OFF" > "$WATERMARK"
    echo "$(STAMP) watermark advanced without mining (backlog > 2MB, candidates=$COUNT)" >> "$LOG"
  fi
  rm -f "$LOCK"
  exit 0
fi

echo "$NEW_OFF" > "$WATERMARK"
echo "$(STAMP) miner spawned (candidates=$COUNT, model=$MODEL)" >> "$LOG"
INSTINCTS_SKIP=1 nohup bash -c '
  ROOT="$1"; CAND="$2"; PROMPT_FILE="$3"; MODEL="$4"; LOG="$5"; LOCK="$6"
  claude -p --model "$MODEL" --max-turns 1 --tools "" --strict-mcp-config --append-system-prompt "$(cat "$PROMPT_FILE")" < "$CAND" \
    | python3 "$ROOT/scripts/instincts/instinct.py" --root "$ROOT" ingest >> "$LOG" 2>&1
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) miner finished" >> "$LOG"
  rm -f "$LOCK"
' _ "$ROOT" "$CAND" "$PROMPT_FILE" "$MODEL" "$LOG" "$LOCK" >/dev/null 2>&1 &
disown 2>/dev/null || true
exit 0

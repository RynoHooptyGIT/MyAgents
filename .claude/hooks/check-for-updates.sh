#!/bin/bash
# =============================================================================
# My Dev Team — Session Update Check Hook
# =============================================================================
# Runs as a UserPromptSubmit hook. Checks for team updates at most once
# every 24 hours to avoid network overhead. Writes a marker file that
# Oracle/Maestro read during activation to display an update banner.
#
# This script is non-blocking and silent — it never outputs to the user
# directly. All notification happens through the orchestrator agents.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CHECK_SCRIPT="$PROJECT_ROOT/scripts/team-check.sh"
COOLDOWN_FILE="$PROJECT_ROOT/.team-last-check"
COOLDOWN_SECONDS=86400  # 24 hours

# ── Exit early if no check script ──────────────────────────────
[ -f "$CHECK_SCRIPT" ] || exit 0
[ -f "$PROJECT_ROOT/.team-upstream" ] || exit 0

# ── Cooldown: skip if checked recently ─────────────────────────
if [ -f "$COOLDOWN_FILE" ]; then
    LAST_CHECK=$(cat "$COOLDOWN_FILE" 2>/dev/null | tr -d '[:space:]')
    NOW=$(date +%s)
    if [ -n "$LAST_CHECK" ] && [ $((NOW - LAST_CHECK)) -lt $COOLDOWN_SECONDS ]; then
        exit 0
    fi
fi

# ── Run check in background (non-blocking) ─────────────────────
(
    date +%s > "$COOLDOWN_FILE"
    bash "$CHECK_SCRIPT" --quiet >/dev/null 2>&1
) &

exit 0

#!/bin/bash
# =============================================================================
# My Dev Team — Session Update Check Hook
# =============================================================================
# Runs as a UserPromptSubmit hook. Checks for team updates AND plugin updates
# at most once every 24 hours to avoid network overhead. Writes marker files
# that Oracle/Maestro read during activation to display update banners.
#
# This script is non-blocking and silent — it never outputs to the user
# directly. All notification happens through the orchestrator agents.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CHECK_SCRIPT="$PROJECT_ROOT/scripts/team-check.sh"
PLUGIN_SYNC_SCRIPT="$PROJECT_ROOT/scripts/plugin-sync.sh"
COOLDOWN_FILE="$PROJECT_ROOT/.team-last-check"
COOLDOWN_SECONDS=86400  # 24 hours

# ── Cooldown: skip if checked recently ─────────────────────────
if [ -f "$COOLDOWN_FILE" ]; then
    LAST_CHECK=$(cat "$COOLDOWN_FILE" 2>/dev/null | tr -d '[:space:]')
    NOW=$(date +%s)
    if [ -n "$LAST_CHECK" ] && [ $((NOW - LAST_CHECK)) -lt $COOLDOWN_SECONDS ]; then
        exit 0
    fi
fi

# ── Run checks in background (non-blocking) ─────────────────────
(
    date +%s > "$COOLDOWN_FILE"

    # Check team updates (if configured)
    if [ -f "$CHECK_SCRIPT" ] && [ -f "$PROJECT_ROOT/.team-upstream" ]; then
        bash "$CHECK_SCRIPT" --quiet >/dev/null 2>&1
    fi

    # Check plugin updates (if registry exists)
    if [ -f "$PLUGIN_SYNC_SCRIPT" ] && [ -f "$PROJECT_ROOT/plugins/registry.json" ]; then
        bash "$PLUGIN_SYNC_SCRIPT" --quiet >/dev/null 2>&1
    fi
) &

exit 0

#!/bin/bash
# =============================================================================
# MyAgents — Plugin Sync
# =============================================================================
# Checks each plugin in plugins/registry.json against its upstream source.
# Downloads and installs updates when new commits are detected.
#
# Usage:
#   bash scripts/plugin-sync.sh              # check & update all plugins
#   bash scripts/plugin-sync.sh --check      # check only, no updates
#   bash scripts/plugin-sync.sh --quiet      # no output, set exit code
#   bash scripts/plugin-sync.sh --plugin X   # sync a specific plugin only
#
# Exit codes:
#   0 = updates applied (or available in --check mode)
#   1 = all plugins up to date
#   2 = error (network, missing tools, etc.)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REGISTRY="$PROJECT_ROOT/plugins/registry.json"
MARKER_FILE="$PROJECT_ROOT/.plugin-update-available"

QUIET=false
CHECK_ONLY=false
TARGET_PLUGIN=""

for arg in "$@"; do
    case "$arg" in
        --quiet)   QUIET=true ;;
        --check)   CHECK_ONLY=true ;;
        --plugin)  shift_next=true ;;
        *)
            if [ "$shift_next" = true ]; then
                TARGET_PLUGIN="$arg"
                shift_next=false
            fi
            ;;
    esac
done

# Handle --plugin properly with positional parsing
ARGS=("$@")
for i in "${!ARGS[@]}"; do
    if [ "${ARGS[$i]}" = "--plugin" ] && [ -n "${ARGS[$((i+1))]:-}" ]; then
        TARGET_PLUGIN="${ARGS[$((i+1))]}"
    fi
done

# ── Prereqs ─────────────────────────────────────────────────────
if ! command -v jq &>/dev/null; then
    $QUIET || echo "ERROR: jq is required. Install with: brew install jq"
    exit 2
fi

if ! command -v gh &>/dev/null; then
    $QUIET || echo "ERROR: gh (GitHub CLI) is required. Install with: brew install gh"
    exit 2
fi

if [ ! -f "$REGISTRY" ]; then
    $QUIET || echo "No plugin registry found at $REGISTRY"
    exit 2
fi

# ── Read plugin list ────────────────────────────────────────────
PLUGINS=$(jq -r '.plugins | keys[]' "$REGISTRY")
if [ -z "$PLUGINS" ]; then
    $QUIET || echo "No plugins registered."
    exit 1
fi

UPDATES_AVAILABLE=0
UPDATES_APPLIED=0
ERRORS=0

for PLUGIN_NAME in $PLUGINS; do
    # Skip if targeting a specific plugin
    if [ -n "$TARGET_PLUGIN" ] && [ "$PLUGIN_NAME" != "$TARGET_PLUGIN" ]; then
        continue
    fi

    SOURCE=$(jq -r ".plugins[\"$PLUGIN_NAME\"].source" "$REGISTRY")
    REPO=$(jq -r ".plugins[\"$PLUGIN_NAME\"].repo" "$REGISTRY")
    PATH_IN_REPO=$(jq -r ".plugins[\"$PLUGIN_NAME\"].path" "$REGISTRY")
    BRANCH=$(jq -r ".plugins[\"$PLUGIN_NAME\"].branch // \"main\"" "$REGISTRY")
    CURRENT_COMMIT=$(jq -r ".plugins[\"$PLUGIN_NAME\"].commit // empty" "$REGISTRY")

    if [ "$SOURCE" != "github" ]; then
        $QUIET || echo "  ⚠️  $PLUGIN_NAME: unsupported source '$SOURCE', skipping"
        continue
    fi

    # ── Get latest commit for the plugin path ────────────────────
    LATEST_COMMIT=$(gh api "repos/$REPO/commits?sha=$BRANCH&path=$PATH_IN_REPO&per_page=1" \
        --jq '.[0].sha' 2>/dev/null) || true

    if [ -z "$LATEST_COMMIT" ]; then
        $QUIET || echo "  ⚠️  $PLUGIN_NAME: could not fetch upstream commit"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    SHORT_LATEST="${LATEST_COMMIT:0:7}"
    SHORT_CURRENT="${CURRENT_COMMIT:0:7}"

    # ── Compare ──────────────────────────────────────────────────
    if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ]; then
        $QUIET || echo "  ✓ $PLUGIN_NAME: up to date ($SHORT_CURRENT)"
        continue
    fi

    UPDATES_AVAILABLE=$((UPDATES_AVAILABLE + 1))

    if [ -z "$CURRENT_COMMIT" ] || [ "$CURRENT_COMMIT" = "null" ]; then
        $QUIET || echo "  ↓ $PLUGIN_NAME: recording initial commit ($SHORT_LATEST)"
    else
        $QUIET || echo "  ↑ $PLUGIN_NAME: update available ($SHORT_CURRENT → $SHORT_LATEST)"
    fi

    if [ "$CHECK_ONLY" = true ]; then
        continue
    fi

    # ── Download updated files ───────────────────────────────────
    PLUGIN_DIR="$PROJECT_ROOT/plugins/$PLUGIN_NAME"

    # Get file tree for the plugin path (blobs only — skip directory entries)
    TREE=$(gh api "repos/$REPO/git/trees/$BRANCH?recursive=1" \
        --jq ".tree[] | select(.type == \"blob\") | select(.path | startswith(\"$PATH_IN_REPO/\")) | .path" 2>/dev/null) || true

    if [ -z "$TREE" ]; then
        $QUIET || echo "  ⚠️  $PLUGIN_NAME: could not fetch file tree"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    SYNC_ERRORS=0
    while IFS= read -r FILE_PATH; do
        # Skip directories
        [ -z "$FILE_PATH" ] && continue

        # Relative path within the plugin
        REL_PATH="${FILE_PATH#$PATH_IN_REPO/}"
        TARGET_FILE="$PLUGIN_DIR/$REL_PATH"

        # Ensure target directory exists
        mkdir -p "$(dirname "$TARGET_FILE")"

        # Download file content
        CONTENT=$(gh api "repos/$REPO/contents/$FILE_PATH?ref=$BRANCH" \
            --jq '.content' 2>/dev/null | base64 -d 2>/dev/null) || true

        if [ -z "$CONTENT" ]; then
            # Could be binary or empty — try download URL
            DOWNLOAD_URL=$(gh api "repos/$REPO/contents/$FILE_PATH?ref=$BRANCH" \
                --jq '.download_url' 2>/dev/null) || true
            if [ -n "$DOWNLOAD_URL" ] && [ "$DOWNLOAD_URL" != "null" ]; then
                curl -sf --max-time 10 "$DOWNLOAD_URL" > "$TARGET_FILE" 2>/dev/null || {
                    $QUIET || echo "    ⚠️  Failed to download: $REL_PATH"
                    SYNC_ERRORS=$((SYNC_ERRORS + 1))
                    continue
                }
            else
                $QUIET || echo "    ⚠️  Failed to fetch: $REL_PATH"
                SYNC_ERRORS=$((SYNC_ERRORS + 1))
                continue
            fi
        else
            echo "$CONTENT" > "$TARGET_FILE"
        fi
    done <<< "$TREE"

    # Make scripts executable
    find "$PLUGIN_DIR" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true

    if [ $SYNC_ERRORS -gt 0 ]; then
        $QUIET || echo "  ⚠️  $PLUGIN_NAME: synced with $SYNC_ERRORS errors"
        ERRORS=$((ERRORS + 1))
    else
        $QUIET || echo "  ✅ $PLUGIN_NAME: updated to $SHORT_LATEST"
        UPDATES_APPLIED=$((UPDATES_APPLIED + 1))
    fi

    # ── Update registry with new commit and timestamp ────────────
    NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    UPDATED_REGISTRY=$(jq \
        --arg plugin "$PLUGIN_NAME" \
        --arg commit "$LATEST_COMMIT" \
        --arg ts "$NOW" \
        '.plugins[$plugin].commit = $commit |
         .plugins[$plugin].last_checked = $ts |
         if .plugins[$plugin].installed_at == null then .plugins[$plugin].installed_at = $ts else . end' \
        "$REGISTRY")
    echo "$UPDATED_REGISTRY" > "$REGISTRY"

done

# ── Update the last_checked for check-only runs too ──────────────
if [ "$CHECK_ONLY" = true ]; then
    NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    for PLUGIN_NAME in $PLUGINS; do
        if [ -n "$TARGET_PLUGIN" ] && [ "$PLUGIN_NAME" != "$TARGET_PLUGIN" ]; then
            continue
        fi
        UPDATED_REGISTRY=$(jq \
            --arg plugin "$PLUGIN_NAME" \
            --arg ts "$NOW" \
            '.plugins[$plugin].last_checked = $ts' \
            "$REGISTRY")
        echo "$UPDATED_REGISTRY" > "$REGISTRY"
    done
fi

# ── Write or clear marker file ───────────────────────────────────
if [ "$CHECK_ONLY" = true ] && [ $UPDATES_AVAILABLE -gt 0 ]; then
    echo "plugins_with_updates=$UPDATES_AVAILABLE" > "$MARKER_FILE"
    echo "checked=$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$MARKER_FILE"
    exit 0
elif [ $UPDATES_AVAILABLE -eq 0 ]; then
    rm -f "$MARKER_FILE"
fi

# ── Summary ──────────────────────────────────────────────────────
if [ "$QUIET" = false ] && [ "$CHECK_ONLY" = false ]; then
    echo ""
    if [ $UPDATES_APPLIED -gt 0 ]; then
        echo "  $UPDATES_APPLIED plugin(s) updated."
    fi
    if [ $ERRORS -gt 0 ]; then
        echo "  $ERRORS error(s) during sync."
    fi
    if [ $UPDATES_AVAILABLE -eq 0 ]; then
        echo "  All plugins up to date."
    fi
fi

# Exit codes
if [ $ERRORS -gt 0 ]; then
    exit 2
elif [ $UPDATES_AVAILABLE -gt 0 ]; then
    exit 0
else
    exit 1
fi

#!/bin/bash
# =============================================================================
# My Dev Team — Update Checker
# =============================================================================
# Checks if a newer version is available from the upstream source.
# Writes .team-update-available marker if an update is found.
#
# Usage:
#   bash scripts/team-check.sh              # check and write marker
#   bash scripts/team-check.sh --quiet      # no output, just set exit code
#   bash scripts/team-check.sh --clear      # remove the update marker
#
# Exit codes:
#   0 = update available (or --clear succeeded)
#   1 = already up to date
#   2 = could not check (network error, no upstream configured)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

MARKER_FILE="$PROJECT_ROOT/.team-update-available"
QUIET=false

for arg in "$@"; do
    case "$arg" in
        --quiet) QUIET=true ;;
        --clear)
            rm -f "$MARKER_FILE"
            exit 0
            ;;
    esac
done

# ── Read last-synced upstream version ─────────────────────────
# Compare against last-synced upstream version, not local version
# (fork maintains its own version scheme, e.g. 7.x vs upstream 6.x)
LAST_SYNCED_UPSTREAM=""
if [ -f "$PROJECT_ROOT/.team-upstream-version" ]; then
    LAST_SYNCED_UPSTREAM=$(head -1 "$PROJECT_ROOT/.team-upstream-version" | sed 's/[[:space:]]*$//')
fi
CURRENT_VERSION=$(head -1 "$PROJECT_ROOT/VERSION" | sed 's/[[:space:]]*$//')

# ── Resolve upstream ───────────────────────────────────────────
UPSTREAM_FILE="$PROJECT_ROOT/.team-upstream"
if [ ! -f "$UPSTREAM_FILE" ]; then
    $QUIET || echo "No .team-upstream file — cannot check for updates"
    exit 2
fi
UPSTREAM=$(cat "$UPSTREAM_FILE" | head -1 | sed 's/[[:space:]]*$//')

# ── Fetch upstream version ─────────────────────────────────────
UPSTREAM_VERSION=""

# Try GitHub sources (works for github.com URLs)
if [[ "$UPSTREAM" == *github.com* ]]; then
    # Extract owner/repo from URL
    REPO_PATH=$(echo "$UPSTREAM" | sed -E 's|.*github\.com[:/]||; s|\.git$||')

    # Try 1: VERSION file via raw content (public repos)
    UPSTREAM_VERSION=$(curl -sf --max-time 5 \
        "https://raw.githubusercontent.com/${REPO_PATH}/main/VERSION" 2>/dev/null | head -1 | sed 's/[[:space:]]*$//') || true

    # Try 2: package.json version field (npm projects like bmad)
    if [ -z "$UPSTREAM_VERSION" ]; then
        UPSTREAM_VERSION=$(curl -sf --max-time 5 \
            "https://raw.githubusercontent.com/${REPO_PATH}/main/package.json" 2>/dev/null | grep '"version"' | head -1 | sed 's/.*"version": *"//;s/".*//' ) || true
    fi

    # Try 3: GitHub CLI API (private repos — requires gh auth)
    if [ -z "$UPSTREAM_VERSION" ] && command -v gh &>/dev/null; then
        UPSTREAM_VERSION=$(gh api "repos/${REPO_PATH}/contents/VERSION" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null | head -1 | sed 's/[[:space:]]*$//') || true
        # Fallback to package.json via API
        if [ -z "$UPSTREAM_VERSION" ]; then
            UPSTREAM_VERSION=$(gh api "repos/${REPO_PATH}/contents/package.json" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null | grep '"version"' | head -1 | sed 's/.*"version": *"//;s/".*//') || true
        fi
    fi
fi

# Fallback: local directory
if [ -z "$UPSTREAM_VERSION" ] && [ -d "$UPSTREAM" ]; then
    if [ -f "$UPSTREAM/VERSION" ]; then
        UPSTREAM_VERSION=$(head -1 "$UPSTREAM/VERSION" | sed 's/[[:space:]]*$//')
    elif [ -f "$UPSTREAM/package.json" ]; then
        UPSTREAM_VERSION=$(grep '"version"' "$UPSTREAM/package.json" | head -1 | sed 's/.*"version": *"//;s/".*//')
    fi
fi

if [ -z "$UPSTREAM_VERSION" ]; then
    $QUIET || echo "Could not fetch upstream version"
    exit 2
fi

# ── Compare versions ───────────────────────────────────────────
if [ "$LAST_SYNCED_UPSTREAM" = "$UPSTREAM_VERSION" ]; then
    # Up to date — clear any stale marker
    rm -f "$MARKER_FILE"
    $QUIET || echo "Up to date with upstream: v${UPSTREAM_VERSION} (local v${CURRENT_VERSION})"
    exit 1
fi

# ── Update available — write marker ────────────────────────────
cat > "$MARKER_FILE" <<EOF
current=${CURRENT_VERSION}
last_synced_upstream=${LAST_SYNCED_UPSTREAM}
available=${UPSTREAM_VERSION}
checked=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
upstream=${UPSTREAM}
EOF

if [ "$QUIET" = false ]; then
    echo ""
    echo "  Upstream update available: v${LAST_SYNCED_UPSTREAM:-unknown} → v${UPSTREAM_VERSION}"
    echo "  (local version: v${CURRENT_VERSION})"
    echo "  Run: bash scripts/team-update.sh"
    echo ""
fi
exit 0

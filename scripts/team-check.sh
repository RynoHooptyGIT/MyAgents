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

# ── Read current version ───────────────────────────────────────
if [ ! -f "$PROJECT_ROOT/VERSION" ]; then
    $QUIET || echo "No VERSION file found"
    exit 2
fi
CURRENT_VERSION=$(cat "$PROJECT_ROOT/VERSION" | head -1 | tr -d '[:space:]')

# ── Resolve upstream ───────────────────────────────────────────
UPSTREAM_FILE="$PROJECT_ROOT/.team-upstream"
if [ ! -f "$UPSTREAM_FILE" ]; then
    $QUIET || echo "No .team-upstream file — cannot check for updates"
    exit 2
fi
UPSTREAM=$(cat "$UPSTREAM_FILE" | head -1 | tr -d '[:space:]')

# ── Fetch upstream version ─────────────────────────────────────
UPSTREAM_VERSION=""

# Try GitHub sources (works for github.com URLs)
if [[ "$UPSTREAM" == *github.com* ]]; then
    # Extract owner/repo from URL
    REPO_PATH=$(echo "$UPSTREAM" | sed -E 's|.*github\.com[:/]||; s|\.git$||')

    # Try 1: GitHub raw content (public repos)
    UPSTREAM_VERSION=$(curl -sf --max-time 5 \
        "https://raw.githubusercontent.com/${REPO_PATH}/main/VERSION" 2>/dev/null | head -1 | tr -d '[:space:]') || true

    # Try 2: GitHub CLI API (private repos — requires gh auth)
    if [ -z "$UPSTREAM_VERSION" ] && command -v gh &>/dev/null; then
        UPSTREAM_VERSION=$(gh api "repos/${REPO_PATH}/contents/VERSION" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null | head -1 | tr -d '[:space:]') || true
    fi
fi

# Fallback: local directory
if [ -z "$UPSTREAM_VERSION" ] && [ -d "$UPSTREAM" ]; then
    if [ -f "$UPSTREAM/VERSION" ]; then
        UPSTREAM_VERSION=$(cat "$UPSTREAM/VERSION" | head -1 | tr -d '[:space:]')
    fi
fi

if [ -z "$UPSTREAM_VERSION" ]; then
    $QUIET || echo "Could not fetch upstream version"
    exit 2
fi

# ── Compare versions ───────────────────────────────────────────
if [ "$CURRENT_VERSION" = "$UPSTREAM_VERSION" ]; then
    # Up to date — clear any stale marker
    rm -f "$MARKER_FILE"
    $QUIET || echo "Up to date: v${CURRENT_VERSION}"
    exit 1
fi

# ── Update available — write marker ────────────────────────────
cat > "$MARKER_FILE" <<EOF
current=${CURRENT_VERSION}
available=${UPSTREAM_VERSION}
checked=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
upstream=${UPSTREAM}
EOF

if [ "$QUIET" = false ]; then
    echo ""
    echo "  Update available: v${CURRENT_VERSION} → v${UPSTREAM_VERSION}"
    echo "  Run: bash scripts/team-update.sh"
    echo ""
fi
exit 0

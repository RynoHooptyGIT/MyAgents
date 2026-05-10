#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Sync Upstream — Review changes from bmad upstream
# =============================================================================
# This fork has no shared git history with bmad (it was extracted, not forked).
# So this script works by comparing upstream tags/versions rather than git
# merge-base. It shows what's new and helps you review before manually porting.
#
# Usage:
#   ./scripts/sync-upstream.sh              # fetch + show what's new
#   ./scripts/sync-upstream.sh --diff       # show file-level changes
#   ./scripts/sync-upstream.sh --log-only   # just show new commits
#   ./scripts/sync-upstream.sh --mark-synced  # record current upstream as synced
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Config
UPSTREAM_REMOTE="bmad"
UPSTREAM_BRANCH="main"
SYNC_MARKER=".team-upstream-version"
LAST_SYNC_TAG=".team-last-sync-tag"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# Parse args
MODE="review"  # review | diff | log | mark
for arg in "$@"; do
  case "$arg" in
    --diff)         MODE="diff" ;;
    --log-only)     MODE="log" ;;
    --mark-synced)  MODE="mark" ;;
    -h|--help)
      echo "Usage: $0 [--diff|--log-only|--mark-synced]"
      echo ""
      echo "  (default)       Fetch upstream, show changelog of new commits"
      echo "  --diff          Show file-level diff between last sync tag and current upstream"
      echo "  --log-only      Just show new commits"
      echo "  --mark-synced   Record current upstream version as synced"
      exit 0
      ;;
  esac
done

# --- Preflight ---
if ! git remote | grep -q "^${UPSTREAM_REMOTE}$"; then
  echo -e "${RED}Error: remote '${UPSTREAM_REMOTE}' not found.${NC}"
  echo "Add it with: git remote add ${UPSTREAM_REMOTE} https://github.com/bmad-code-org/BMAD-METHOD.git"
  exit 1
fi

# --- Fetch ---
echo -e "${CYAN}Fetching ${UPSTREAM_REMOTE}...${NC}"
git fetch "$UPSTREAM_REMOTE" --tags --quiet 2>/dev/null || git fetch "$UPSTREAM_REMOTE" --quiet

# --- Resolve versions ---
UPSTREAM_HEAD=$(git rev-parse "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}")
LOCAL_VERSION=$(head -1 VERSION 2>/dev/null || echo "unknown")

# Upstream version from package.json
UPSTREAM_VERSION=$(git cat-file -p "${UPSTREAM_HEAD}:package.json" 2>/dev/null \
  | grep '"version"' | head -1 | sed 's/.*"version": *"//;s/".*//' || echo "unknown")

# Last synced upstream version
LAST_SYNCED=""
if [ -f "$SYNC_MARKER" ]; then
  LAST_SYNCED=$(head -1 "$SYNC_MARKER" | tr -d '[:space:]')
fi

# Last synced upstream tag (for commit range)
LAST_SYNC_REF=""
if [ -f "$LAST_SYNC_TAG" ]; then
  LAST_SYNC_REF=$(head -1 "$LAST_SYNC_TAG" | tr -d '[:space:]')
  # Verify it exists
  if ! git cat-file -t "$LAST_SYNC_REF" &>/dev/null; then
    LAST_SYNC_REF=""
  fi
fi

# If no sync ref, try to find a matching bmad tag for the last synced version
if [ -z "$LAST_SYNC_REF" ] && [ -n "$LAST_SYNCED" ]; then
  for tag_prefix in "v" ""; do
    candidate="${tag_prefix}${LAST_SYNCED}"
    if git rev-parse "${candidate}" &>/dev/null; then
      LAST_SYNC_REF="${candidate}"
      break
    fi
  done
fi

echo ""
echo -e "${BOLD}  Upstream Sync Status${NC}"
echo -e "  ─────────────────────────────────"
echo -e "  Local version:    ${YELLOW}v${LOCAL_VERSION}${NC}"
echo -e "  Upstream version: ${GREEN}v${UPSTREAM_VERSION}${NC}"
echo -e "  Last synced from: ${DIM}${LAST_SYNCED:-never}${NC}"
echo ""

# --- Mark-synced mode ---
if [ "$MODE" = "mark" ]; then
  echo "$UPSTREAM_VERSION" > "$SYNC_MARKER"
  echo "$UPSTREAM_HEAD" > "$LAST_SYNC_TAG"
  echo -e "  ${GREEN}Marked as synced with upstream v${UPSTREAM_VERSION}${NC}"
  echo -e "  ${DIM}(${UPSTREAM_HEAD})${NC}"
  exit 0
fi

# Check if already synced
if [ "$LAST_SYNCED" = "$UPSTREAM_VERSION" ]; then
  echo -e "  ${GREEN}Already in sync with upstream v${UPSTREAM_VERSION}.${NC}"
  exit 0
fi

# --- Determine commit range ---
# Find upstream release tags to show changes between versions
UPSTREAM_TAGS=$(git tag -l 'v*' --sort=version:refname --merged "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}" 2>/dev/null | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true)

# Find tags newer than last synced version
NEW_TAGS=""
FOUND_LAST=false
if [ -n "$LAST_SYNCED" ] && [ -n "$UPSTREAM_TAGS" ]; then
  while IFS= read -r tag; do
    tag_ver="${tag#v}"
    if [ "$FOUND_LAST" = true ]; then
      NEW_TAGS="${NEW_TAGS}${tag}"$'\n'
    fi
    if [ "$tag_ver" = "$LAST_SYNCED" ]; then
      FOUND_LAST=true
    fi
  done <<< "$UPSTREAM_TAGS"
elif [ -n "$UPSTREAM_TAGS" ]; then
  # Never synced — show last 2 releases
  NEW_TAGS=$(echo "$UPSTREAM_TAGS" | tail -2)
fi

# --- Show new releases ---
if [ -n "$NEW_TAGS" ]; then
  echo -e "${CYAN}  New upstream releases:${NC}"
  echo -e "  ─────────────────────────────────"
  while IFS= read -r tag; do
    [ -z "$tag" ] && continue
    echo -e "  ${GREEN}${tag}${NC}"
  done <<< "$NEW_TAGS"
  echo ""
fi

# --- Show changelog ---
echo -e "${CYAN}  New upstream commits:${NC}"
echo -e "  ─────────────────────────────────"

if [ -n "$LAST_SYNC_REF" ]; then
  COMMIT_COUNT=$(git rev-list --count "${LAST_SYNC_REF}..${UPSTREAM_HEAD}" --no-merges 2>/dev/null || echo "?")
  echo -e "  ${DIM}(${COMMIT_COUNT} commits since v${LAST_SYNCED})${NC}"
  echo ""
  git log "${LAST_SYNC_REF}..${UPSTREAM_HEAD}" --oneline --no-merges \
    --format="  %C(yellow)%h%C(reset) %s" 2>/dev/null | head -50
  TOTAL=$(git rev-list --count "${LAST_SYNC_REF}..${UPSTREAM_HEAD}" --no-merges 2>/dev/null || echo 0)
  if [ "$TOTAL" -gt 50 ]; then
    echo -e "  ${DIM}... and $((TOTAL - 50)) more${NC}"
  fi
else
  # No sync ref — show recent upstream commits
  echo -e "  ${DIM}(showing last 30 commits — no previous sync recorded)${NC}"
  echo ""
  git log "${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}" --oneline --no-merges \
    --format="  %C(yellow)%h%C(reset) %s" -30
fi

echo ""

# --- Diff mode: show file-level changes ---
if [ "$MODE" = "diff" ] && [ -n "$LAST_SYNC_REF" ]; then
  echo -e "${CYAN}  Changed files:${NC}"
  echo -e "  ─────────────────────────────────"

  git diff "${LAST_SYNC_REF}..${UPSTREAM_HEAD}" --stat 2>/dev/null | tail -20 | while IFS= read -r line; do
    echo -e "  $line"
  done
  echo ""

  echo -e "${CYAN}  Changes by area:${NC}"
  echo -e "  ─────────────────────────────────"
  git diff "${LAST_SYNC_REF}..${UPSTREAM_HEAD}" --dirstat=lines,3 2>/dev/null | while IFS= read -r line; do
    echo -e "  $line"
  done
  echo ""
elif [ "$MODE" = "diff" ]; then
  echo -e "  ${YELLOW}Cannot show diff — no previous sync point recorded.${NC}"
  echo -e "  ${DIM}Run with --mark-synced after your first manual sync.${NC}"
  echo ""
fi

# --- Next steps ---
if [ "$MODE" != "log" ]; then
  echo -e "${BLUE}  Next steps:${NC}"
  echo -e "  ─────────────────────────────────"
  if [ -n "$LAST_SYNC_REF" ]; then
    echo -e "  ${DIM}# View full diff:${NC}"
    echo -e "    git diff ${LAST_SYNC_REF}..${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}"
    echo ""
    echo -e "  ${DIM}# View a specific upstream file:${NC}"
    echo -e "    git show ${UPSTREAM_REMOTE}/${UPSTREAM_BRANCH}:<path>"
    echo ""
  fi
  echo -e "  ${DIM}# View a specific upstream commit:${NC}"
  echo -e "    git show <hash>"
  echo ""
  echo -e "  ${DIM}# After porting changes, record the sync:${NC}"
  echo -e "    $0 --mark-synced"
  echo ""
  echo -e "  ${DIM}# Note: this fork has no shared git history with bmad,${NC}"
  echo -e "  ${DIM}# so changes must be ported manually (copy files / adapt code).${NC}"
  echo -e "  ${DIM}# git merge and cherry-pick will not work.${NC}"
  echo ""
fi

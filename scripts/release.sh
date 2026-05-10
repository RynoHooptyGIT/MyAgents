#!/usr/bin/env bash
set -euo pipefail

# Release script — handles VERSION bump, commit, tag, push, and GitHub release
# Usage: ./scripts/release.sh <version> [--draft] [--no-push]
#
# Examples:
#   ./scripts/release.sh 7.5.0
#   ./scripts/release.sh 7.5.0 --draft
#   ./scripts/release.sh 7.5.0 --no-push

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Parse args ---
VERSION=""
DRAFT=false
NO_PUSH=false

for arg in "$@"; do
  case "$arg" in
    --draft)   DRAFT=true ;;
    --no-push) NO_PUSH=true ;;
    -h|--help)
      echo "Usage: $0 <version> [--draft] [--no-push]"
      echo ""
      echo "  <version>   Version number (e.g. 7.5.0) — 'v' prefix optional"
      echo "  --draft     Create GitHub release as draft"
      echo "  --no-push   Commit and tag locally but don't push"
      exit 0
      ;;
    *)
      if [[ -z "$VERSION" ]]; then
        VERSION="$arg"
      else
        echo "Error: unexpected argument '$arg'" >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Error: version required. Usage: $0 <version>" >&2
  exit 1
fi

# Strip leading 'v' if provided
VERSION="${VERSION#v}"
TAG="v${VERSION}"

cd "$REPO_ROOT"

# --- Preflight checks ---
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "Error: releases must be cut from main (currently on '$CURRENT_BRANCH')" >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: working tree is dirty — commit or stash changes first" >&2
  exit 1
fi

if git tag -l "$TAG" | grep -q "^${TAG}$"; then
  echo "Error: tag $TAG already exists" >&2
  exit 1
fi

CURRENT_VERSION=$(cat VERSION 2>/dev/null || echo "0.0.0")
echo "Releasing: $CURRENT_VERSION -> $VERSION"
echo ""

# --- Bump VERSION file ---
echo "$VERSION" > VERSION

# --- Build commit message from git log since last tag ---
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [[ -n "$LAST_TAG" ]]; then
  CHANGELOG=$(git log "${LAST_TAG}..HEAD" --oneline --no-merges | grep -v "chore(release)" || true)
else
  CHANGELOG=$(git log --oneline -20 --no-merges | grep -v "chore(release)" || true)
fi

# Prompt for release title
echo "Enter a short release title (e.g. 'multi-agent coordination system'):"
read -r RELEASE_TITLE

if [[ -z "$RELEASE_TITLE" ]]; then
  COMMIT_MSG="chore(release): ${TAG}"
else
  COMMIT_MSG="chore(release): ${TAG} — ${RELEASE_TITLE}"
fi

# --- Commit ---
git add VERSION
git commit -m "$COMMIT_MSG"

# --- Tag ---
git tag -a "$TAG" -m "$COMMIT_MSG"

echo ""
echo "Created commit and tag $TAG"

if $NO_PUSH; then
  echo "Skipping push (--no-push)"
  echo ""
  echo "When ready:"
  echo "  git push origin main"
  echo "  git push origin $TAG"
  exit 0
fi

# --- Push ---
git push origin main
git push origin "$TAG"
echo "Pushed commit and tag to origin"

# --- GitHub Release ---
if command -v gh &>/dev/null; then
  RELEASE_NOTES="## What's Changed"$'\n\n'
  if [[ -n "$CHANGELOG" ]]; then
    RELEASE_NOTES+=$(echo "$CHANGELOG" | sed 's/^[a-f0-9]* /- /')
  else
    RELEASE_NOTES+="- See commit history for details"
  fi

  GH_ARGS=(release create "$TAG" --title "$TAG — $RELEASE_TITLE" --notes "$RELEASE_NOTES")
  if $DRAFT; then
    GH_ARGS+=(--draft)
  fi

  gh "${GH_ARGS[@]}" && echo "GitHub release created" || echo "Warning: GitHub release creation failed (you can create it manually)"
else
  echo "Note: gh CLI not found — skipping GitHub release creation"
  echo "Create manually at: https://github.com/$(git remote get-url origin | sed 's|.*github.com[:/]||;s|\.git$||')/releases/new?tag=$TAG"
fi

echo ""
echo "Release $TAG complete!"

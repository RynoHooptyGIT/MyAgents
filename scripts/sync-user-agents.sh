#!/usr/bin/env bash
# Copy team/agents/*.md to ~/.claude/agents/ so Claude Code's Agent tool sees
# the current frontmatter (role:, tools:) and activation steps.
#
# Usage: scripts/sync-user-agents.sh [--check] [--dest DIR]
#   --check   report files that differ or are missing; exit 1 if any
#   --dest    destination directory (default: ~/.claude/agents)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$REPO_ROOT/team/agents"
DEST="$HOME/.claude/agents"
CHECK=false

while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK=true ;;
    --dest) shift; DEST="$1" ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Error: unknown argument '$1'" >&2; exit 1 ;;
  esac
  shift
done

mkdir -p "$DEST"
DIFFS=0
COPIED=0
for f in "$SRC"/*.md; do
  base="$(basename "$f")"
  [ "$base" = "oracle-dispatch-map.md" ] && continue
  if $CHECK; then
    if ! cmp -s "$f" "$DEST/$base"; then echo "STALE: $base"; DIFFS=$((DIFFS+1)); fi
  else
    if ! cmp -s "$f" "$DEST/$base"; then cp "$f" "$DEST/$base"; COPIED=$((COPIED+1)); fi
  fi
done

# Prune files we synced earlier whose source no longer exists (identified by
# the AUTHORITY line every team agent carries); never touch the user's own agents.
PRUNED=0
for f in "$DEST"/*.md; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  [ -f "$SRC/$base" ] && continue
  grep -q 'AUTHORITY: {project-root}/team/engine/authority-contract.xml' "$f" || continue
  if $CHECK; then echo "ORPHAN: $base"; DIFFS=$((DIFFS+1)); else rm -f "$f"; PRUNED=$((PRUNED+1)); fi
done

if $CHECK; then
  [ "$DIFFS" -eq 0 ] && echo "sync-user-agents --check: up to date" || { echo "sync-user-agents --check: $DIFFS stale" >&2; exit 1; }
else
  echo "sync-user-agents: $COPIED file(s) copied to $DEST, $PRUNED orphan(s) removed"
fi

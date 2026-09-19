#!/usr/bin/env bash
# Shared identity resolution for coordination hooks.
# Worktree = identity: /agent-coordinator writes .agent-id and .agent-coord-root
# into each agent's worktree. Resolve from (1) the directory of the file being
# edited, (2) the hook's cwd, (3) legacy PID-suffixed registry files.
#
# Usage:  source lib-identity.sh; resolve_identity "$FILE_PATH" "$CWD"
# Callers must pass an ABSOLUTE cwd; find_marker_dir does not test a relative "." itself.
# Sets:   COORD_ROOT  main checkout holding .agents/   (may be empty)
#         MY_ID       this instance's agent id           (may be empty)
#         WORK_ROOT   dir containing .agent-id, else COORD_ROOT

find_marker_dir() {  # $1 = start dir → prints dir containing .agent-id, or returns 1
  local d="$1"
  while [ -n "$d" ] && [ "$d" != "/" ] && [ "$d" != "." ]; do
    if [ -f "$d/.agent-id" ]; then printf '%s\n' "$d"; return 0; fi
    d="$(dirname "$d")"
  done
  return 1
}

resolve_identity() {  # $1 = file path (abs or rel, may be empty), $2 = cwd (may be empty)
  COORD_ROOT=""; MY_ID=""; WORK_ROOT=""
  local file="${1:-}" cwd="${2:-$PWD}" start="" dir=""

  if [ -n "$file" ]; then
    case "$file" in
      /*) start="$(dirname "$file")" ;;
      *)  start="$(dirname "$cwd/$file")" ;;
    esac
    dir="$(find_marker_dir "$start" 2>/dev/null)" || dir=""
  fi
  if [ -z "$dir" ]; then
    dir="$(find_marker_dir "$cwd" 2>/dev/null)" || dir=""
  fi

  if [ -n "$dir" ]; then
    MY_ID="$(cat "$dir/.agent-id" 2>/dev/null || true)"
    COORD_ROOT="$(cat "$dir/.agent-coord-root" 2>/dev/null || true)"
    WORK_ROOT="$dir"
  fi

  if [ -z "$COORD_ROOT" ]; then
    # Legacy fallback: PID-suffixed file written by /agent-coordinator in the main checkout.
    # Checked before git-common-dir because inside a worktree, --git-common-dir resolves to
    # the *parent* repository's .git, not the checkout that actually holds .agents/.
    for rootfile in "$cwd"/.agents/registry/.coord-root-*; do
      [ -f "$rootfile" ] && COORD_ROOT="$(cat "$rootfile")" && break
    done
    if [ -z "$COORD_ROOT" ]; then
      COORD_ROOT="$(git -C "$cwd" rev-parse --path-format=absolute --git-common-dir 2>/dev/null | sed 's|/\.git$||')" || COORD_ROOT=""
    fi
  fi

  if [ -z "$MY_ID" ] && [ -n "$COORD_ROOT" ]; then
    for idfile in "$COORD_ROOT/.agents/registry/.current-agent-id-"*; do
      [ -f "$idfile" ] && MY_ID="$(cat "$idfile")" && break
    done
  fi

  [ -z "$WORK_ROOT" ] && WORK_ROOT="$COORD_ROOT"
  return 0
}

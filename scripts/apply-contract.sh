#!/usr/bin/env bash
# Wire team/engine/authority-contract.xml into every agent file.
# Adds: frontmatter `role:` (+ `tools:` for advisors) and an AUTHORITY line.
# Role cards (plain markdown) get the line after their first heading; legacy
# activation-XML agents get <step n="2a"> plus an AUTHORITY <r> as the first rule.
# Idempotent — safe to re-run.
#
# Usage: scripts/apply-contract.sh [--check] [--agents-dir DIR]
#   --check   verify only; exit 1 and list gaps if any agent is unwired
#   AGENTS_DIR env var also overrides the directory (default: team/agents)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTS_DIR="${AGENTS_DIR:-$REPO_ROOT/team/agents}"
CHECK=false

while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK=true ;;
    --agents-dir) shift; AGENTS_DIR="$1" ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Error: unknown argument '$1'" >&2; exit 1 ;;
  esac
  shift
done

CONTRACT_PATH='{project-root}/team/engine/authority-contract.xml'
ADVISOR_TOOLS='Read, Grep, Glob, WebFetch, WebSearch'
STEP_2A='      <step n="2a">Load '"$CONTRACT_PATH"' and adopt the role named in this file'"'"'s frontmatter (role: supervisor | worker | advisor). Hard rules there override any menu item, workflow step, or persona principle.</step>'
RULE_LINE='      <r>AUTHORITY: '"$CONTRACT_PATH"' hard rules override any menu item, workflow step, or persona principle. If constructing a reason to skip one, that IS the signal to follow it.</r>'
CARD_LINE='AUTHORITY: '"$CONTRACT_PATH"' hard rules override any workflow step or principle in this file. If constructing a reason to skip one, that IS the signal to follow it.'

role_for() {
  case "$1" in
    oracle) echo supervisor ;;
    healthcare-expert|government-expert|financial-expert) echo advisor ;;
    *) echo worker ;;
  esac
}

has_role()  { grep -q '^role: "' "$1"; }
has_tools() { grep -q '^tools: ' "$1"; }
is_legacy() { grep -q '<activation' "$1"; }
has_step()  { ! is_legacy "$1" || grep -q '<step n="2a">' "$1"; }
has_rule()  { grep -q 'AUTHORITY: {project-root}/team/engine/authority-contract.xml' "$1"; }

# Insert `role:` (and `tools:` for advisors) after the `description:` line of the frontmatter.
add_frontmatter() {  # file role
  local tmp; tmp="$(mktemp)"
  awk -v role="$2" -v tools="$ADVISOR_TOOLS" -v add_tools="$( [ "$2" = advisor ] && echo 1 || echo 0 )" '
    BEGIN { done=0 }
    { print }
    !done && /^description: / {
      print "role: \"" role "\""
      if (add_tools == 1) print "tools: " tools
      done=1
    }
  ' "$1" > "$tmp" && mv "$tmp" "$1"
}

# Insert step 2a after the </step> that closes <step n="2">.
add_step() {  # file
  local tmp; tmp="$(mktemp)"
  awk -v step="$STEP_2A" '
    BEGIN { in2=0; done=0 }
    { print }
    !done && /<step n="2">/ { in2=1 }
    !done && in2 && /<\/step>/ { print step; in2=0; done=1 }
  ' "$1" > "$tmp" && mv "$tmp" "$1"
}

# Legacy: insert the AUTHORITY rule as the first line after <rules>.
# Role card: insert the AUTHORITY line (blank-line separated) after the first
# `# ` heading, or after the closing frontmatter `---` when there is no heading.
add_rule() {  # file
  local tmp; tmp="$(mktemp)"
  if is_legacy "$1"; then
    awk -v rule="$RULE_LINE" '
      BEGIN { done=0 }
      { print }
      !done && /<rules>/ { print rule; done=1 }
    ' "$1" > "$tmp" && mv "$tmp" "$1"
  else
    local anchor='^# '
    grep -q "$anchor" "$1" || anchor='^---$'   # no heading: use the closing frontmatter fence
    awk -v rule="$CARD_LINE" -v anchor="$anchor" '
      BEGIN { seen=0; done=0 }
      { print }
      !done && $0 ~ anchor { seen++; if (anchor == "^---$" && seen < 2) next; print ""; print rule; done=1 }
    ' "$1" > "$tmp" && mv "$tmp" "$1"
  fi
}

GAPS=0
CHANGED=0
for f in "$AGENTS_DIR"/*.md; do
  [ -f "$f" ] || continue
  base="$(basename "$f" .md)"
  [ "$base" = "oracle-dispatch-map" ] && continue
  role="$(role_for "$base")"

  missing=""
  has_role "$f"  || missing="$missing role"
  has_step "$f"  || missing="$missing step-2a"
  has_rule "$f"  || missing="$missing rule"
  if [ "$role" = advisor ] && ! has_tools "$f"; then missing="$missing tools"; fi

  if [ -z "$missing" ]; then continue; fi

  if $CHECK; then
    echo "UNWIRED: $base —$missing"
    GAPS=$((GAPS+1))
    continue
  fi

  has_role "$f" || add_frontmatter "$f" "$role"
  if [ "$role" = advisor ] && ! has_tools "$f"; then
    # role exists but tools missing (e.g. file wired before advisor tools were added)
    tmp="$(mktemp)"
    awk -v tools="$ADVISOR_TOOLS" 'BEGIN{d=0} {print} !d && /^role: "advisor"$/ {print "tools: " tools; d=1}' "$f" > "$tmp" && mv "$tmp" "$f"
  fi
  has_step "$f" || add_step "$f"
  has_rule "$f" || add_rule "$f"
  echo "wired: $base ($role)"
  CHANGED=$((CHANGED+1))
done

if $CHECK; then
  if [ "$GAPS" -gt 0 ]; then echo "apply-contract --check: $GAPS agent(s) unwired" >&2; exit 1; fi
  echo "apply-contract --check: all agents wired"
else
  echo "apply-contract: $CHANGED file(s) changed"
fi

#!/usr/bin/env bash
# =============================================================================
# check-settings-drift.sh — the settings template must register the same hooks
# as this repo's .claude/settings.local.json.
# =============================================================================
# Extracts the set of hook `command` strings from both JSON files and fails if
# they differ, except for the allow-listed differences below. Nothing else is
# normalized: the template's command strings must match local byte for byte
# (including "$CLAUDE_PROJECT_DIR").
#
# Usage: bash scripts/check-settings-drift.sh [LOCAL_JSON] [TEMPLATE_JSON]
# Exit:  0 no drift · 1 drift or unreadable input
# =============================================================================
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL="${1:-$REPO_ROOT/.claude/settings.local.json}"
TEMPLATE="${2:-$REPO_ROOT/templates/settings.local.json.template}"

# Allowed differences, matched as substrings of the command string.
ALLOWED_TEMPLATE_ONLY=("post-commit-context.sh")   # registered for installs only; this repo runs it via git hooks
ALLOWED_LOCAL_ONLY=()

for f in "$LOCAL" "$TEMPLATE"; do
    if [ ! -f "$f" ]; then
        echo "settings drift: cannot read $f" >&2
        exit 1
    fi
done

# One sorted command per line.
extract() {
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("\n".join(sorted({h["command"] for groups in d.get("hooks",{}).values() for g in groups for h in g.get("hooks",[]) if h.get("type")=="command"})))' "$1"
}

LOCAL_CMDS="$(extract "$LOCAL")" || { echo "settings drift: cannot parse $LOCAL" >&2; exit 1; }
TEMPLATE_CMDS="$(extract "$TEMPLATE")" || { echo "settings drift: cannot parse $TEMPLATE" >&2; exit 1; }

# is_allowed CMD ALLOWED... → 0 if CMD contains any allowed substring
is_allowed() {
    local cmd="$1"; shift
    local pat
    for pat in "$@"; do
        case "$cmd" in *"$pat"*) return 0 ;; esac
    done
    return 1
}

DRIFT=0
report() {  # kind cmd
    [ "$DRIFT" -eq 0 ] && echo "settings drift: templates/settings.local.json.template != .claude/settings.local.json" >&2
    DRIFT=$((DRIFT + 1))
    echo "  $1: $2" >&2
}

while IFS= read -r cmd; do
    [ -n "$cmd" ] || continue
    printf '%s\n' "$TEMPLATE_CMDS" | grep -qxF -- "$cmd" && continue
    is_allowed "$cmd" ${ALLOWED_LOCAL_ONLY[@]+"${ALLOWED_LOCAL_ONLY[@]}"} && continue
    report "missing from template" "$cmd"
done <<EOF
$LOCAL_CMDS
EOF

while IFS= read -r cmd; do
    [ -n "$cmd" ] || continue
    printf '%s\n' "$LOCAL_CMDS" | grep -qxF -- "$cmd" && continue
    is_allowed "$cmd" ${ALLOWED_TEMPLATE_ONLY[@]+"${ALLOWED_TEMPLATE_ONLY[@]}"} && continue
    report "only in template" "$cmd"
done <<EOF
$TEMPLATE_CMDS
EOF

if [ "$DRIFT" -gt 0 ]; then
    echo "  ($DRIFT difference(s); allowed template-only: ${ALLOWED_TEMPLATE_ONLY[*]:-none}; allowed local-only: ${ALLOWED_LOCAL_ONLY[*]:-none})" >&2
    exit 1
fi

echo "settings drift: none"
exit 0

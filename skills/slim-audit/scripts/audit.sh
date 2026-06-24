#!/bin/bash
# =============================================================================
# slim-audit — token bloat scanner
# =============================================================================
# Measures the real token footprint of command/agent/workflow markdown and
# flags every file over threshold. Token estimate = bytes / 4 (GPT/Claude-ish).
# No network, no deps. Run from the project root or anywhere inside it.
# =============================================================================

set -euo pipefail

# Resolve project root (this script lives in skills/slim-audit/scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$ROOT"

THRESHOLD_BYTES="${SLIM_THRESHOLD_BYTES:-8192}"   # flag files over ~2k tokens
ALWAYS_LOADED_REF="CLAUDE.md"                      # files referenced here = always paid

est_tokens() { awk "BEGIN{printf \"%.1fk\", $1/4096}"; }

scan_dir() {
    local label="$1" dir="$2"
    [ -d "$dir" ] || { printf "  %-12s (missing)\n" "$label"; return; }
    local total files
    total=$(find "$dir" -name '*.md' -type f -exec cat {} + 2>/dev/null | wc -c | tr -d ' ')
    files=$(find "$dir" -name '*.md' -type f | wc -l | tr -d ' ')
    printf "  %-12s %4s files  %8s bytes  ~%s tokens\n" \
        "$label" "$files" "$total" "$(est_tokens "$total")"
}

echo "═══════════════════════════════════════════════════════════"
echo " SLIM AUDIT  —  token footprint  (root: $ROOT)"
echo "═══════════════════════════════════════════════════════════"
echo
echo "DIRECTORY TOTALS"
scan_dir "commands"  "claude-commands"
scan_dir "agents"    "team/agents"
scan_dir "workflows" "team/workflows"
scan_dir "skills"    "skills"
echo

echo "FILES OVER THRESHOLD (>$(est_tokens "$THRESHOLD_BYTES") tokens)"
echo "  [A]=referenced in $ALWAYS_LOADED_REF (paid every session)  [ ]=on-demand"
# List fat files across the persona/command set, biggest first.
{ find claude-commands team/agents skills -name '*.md' -type f 2>/dev/null \
    -printf '%s\t%p\n' || true; } \
  | awk -v t="$THRESHOLD_BYTES" '$1 > t' \
  | sort -rn \
  | while IFS=$'\t' read -r size path; do
        flag=" "
        if [ -f "$ALWAYS_LOADED_REF" ] && grep -qiF "$(basename "$path")" "$ALWAYS_LOADED_REF" 2>/dev/null; then
            flag="A"
        fi
        printf "  [%s] %8s bytes  ~%-6s  %s\n" "$flag" "$size" "$(est_tokens "$size")" "$path"
    done
echo
echo "Re-run after edits to confirm savings. Focus on [A] rows first."

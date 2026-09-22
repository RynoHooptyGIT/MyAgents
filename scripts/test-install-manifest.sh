#!/usr/bin/env bash
# Harness for scripts/lib/install-manifest.sh (apply_manifest) against the real
# templates/install-manifest.txt. Builds a scratch SRC with a dummy file per
# manifest entry (two per glob), applies twice, and asserts copy/init/exec
# semantics, dry-run, and warning-only behaviour for unmatched globs.
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIB="$REPO_ROOT/scripts/lib/install-manifest.sh"
MANIFEST="$REPO_ROOT/templates/install-manifest.txt"
PASS=0
FAIL=0

check() {  # desc, condition-exit-code
  if [ "$2" -eq 0 ]; then echo "  PASS: $1"; PASS=$((PASS+1)); else echo "  FAIL: $1"; FAIL=$((FAIL+1)); fi
}

finish() {
  echo ""
  echo "Results: $PASS passed, $FAIL failed"
  [ "$FAIL" -eq 0 ] || exit 1
  exit 0
}

echo "=== Install Manifest Tests ==="

[ -f "$LIB" ];      check "library exists: scripts/lib/install-manifest.sh" $?
[ -f "$MANIFEST" ]; check "manifest exists: templates/install-manifest.txt" $?
[ "$FAIL" -eq 0 ] || finish

# shellcheck source=lib/install-manifest.sh
source "$LIB"
type apply_manifest > /dev/null 2>&1; check "apply_manifest is defined after sourcing" $?

# Scratch tree deliberately contains a space (this repo's own path does too).
BASE="$(mktemp -d)"
TMP="$BASE/with space"
SRC="$TMP/src"
DST="$TMP/dst"
mkdir -p "$SRC/templates" "$DST"
trap 'rm -rf "$BASE"' EXIT
# The scratch source carries the real manifest so the default lookup
# ($SRC_ROOT/templates/install-manifest.txt) is exercised, as in setup/update.
cp "$MANIFEST" "$SRC/templates/install-manifest.txt"

# --- Build SRC from the manifest; record expected "mode<TAB>relative-dst<TAB>group" per file
EXPECTED=()
ENTRIES=0
mk_src() {  # relpath content
  mkdir -p "$SRC/$(dirname "$1")"
  printf '%s\n' "$2" > "$SRC/$1"
}
while IFS=$'\t' read -r mode src dst group || [ -n "${mode:-}" ]; do
  case "$mode" in ''|'#'*) continue ;; esac
  ENTRIES=$((ENTRIES + 1))
  group="${group:-core}"
  name="${src##*/}"
  dir="${src%/*}"; [ "$dir" = "$src" ] && dir=""
  if [[ "$name" == *'*'* ]]; then
    for n in one two; do
      f="${name/\*/$n}"
      mk_src "${dir:+$dir/}$f" "v1 $src"
      EXPECTED+=("$mode	${dst}${f}	$group")
    done
  else
    mk_src "$src" "v1 $src"
    case "$dst" in
      */) EXPECTED+=("$mode	${dst}${name}	$group") ;;
      *)  EXPECTED+=("$mode	${dst}	$group") ;;
    esac
  fi
done < "$MANIFEST"

[ "$ENTRIES" -ge 20 ]; check "manifest has >= 20 entries (has $ENTRIES)" $?
printf '%s\n' "${EXPECTED[@]}" | grep -q '^exec	'; check "manifest has exec entries" $?
printf '%s\n' "${EXPECTED[@]}" | grep -q '^init	'; check "manifest has init entries" $?
printf '%s\n' "${EXPECTED[@]}" | grep -q '^copy	'; check "manifest has copy entries" $?
grep -qE '^init	templates/settings.local.json.template	.claude/settings.local.json(	|$)' "$MANIFEST"
check "settings template is an init entry targeting .claude/settings.local.json" $?
grep -q '^init	.agents/config.yaml	' "$MANIFEST"; check ".agents/config.yaml is an init entry" $?
! grep -qE '	scripts/(test|check-settings-drift)\.sh	' "$MANIFEST"
check "repo-only dev tools (test.sh, check-settings-drift.sh) are not in the manifest" $?
printf '%s\n' "${EXPECTED[@]}" | grep -q '	claude$' && printf '%s\n' "${EXPECTED[@]}" | grep -q '	core$'
check "manifest has both core and claude group entries" $?
printf '%s\n' "${EXPECTED[@]}" | grep -v '	claude$' | grep -q '^[a-z]*	\.claude/'
[ $? -ne 0 ]; check "every .claude/ destination is in the claude group" $?

# --- Run 1: fresh destination
OUT1="$(apply_manifest "$SRC" "$DST" 2> "$TMP/err1")"; RC1=$?
[ "$RC1" -eq 0 ]; check "first apply exits 0 (got $RC1)" $?
[ ! -s "$TMP/err1" ]; check "first apply prints no warnings (stderr empty)" $?

missing=0; not_exec=0; bad_content=0
for e in "${EXPECTED[@]}"; do
  mode="${e%%	*}"; rel="${e#*	}"; rel="${rel%	*}"
  if [ ! -f "$DST/$rel" ]; then missing=$((missing + 1)); echo "    missing: $rel"; continue; fi
  if [ "$mode" = "exec" ] && [ ! -x "$DST/$rel" ]; then not_exec=$((not_exec + 1)); echo "    not executable: $rel"; fi
  grep -q '^v1 ' "$DST/$rel" 2>/dev/null || { bad_content=$((bad_content + 1)); echo "    wrong content: $rel"; }
done
[ "$missing" -eq 0 ];     check "every manifest destination exists after first apply (${#EXPECTED[@]} files)" $?
[ "$not_exec" -eq 0 ];    check "every exec destination is executable" $?
[ "$bad_content" -eq 0 ]; check "every destination has the source content" $?

n_lines=$(printf '%s\n' "$OUT1" | grep -c .)
n_installed=$(printf '%s\n' "$OUT1" | grep -c '^installed ')
[ "$n_lines" -eq "${#EXPECTED[@]}" ] && [ "$n_installed" -eq "${#EXPECTED[@]}" ]
check "first apply prints exactly one 'installed <dst>' line per file ($n_installed/$n_lines of ${#EXPECTED[@]})" $?

# --- Between runs: mark init destinations, bump every source
for e in "${EXPECTED[@]}"; do
  mode="${e%%	*}"; rel="${e#*	}"; rel="${rel%	*}"
  [ "$mode" = "init" ] && [ -f "$DST/$rel" ] && printf '%s\n' "LOCAL-EDIT-MARKER" >> "$DST/$rel"
done
find "$SRC" -type f -not -path "$SRC/templates/*" | while IFS= read -r f; do printf '%s\n' "v2 $f" > "$f"; done

# --- Run 2: same destination
OUT2="$(apply_manifest "$SRC" "$DST" 2> "$TMP/err2")"; RC2=$?
[ "$RC2" -eq 0 ]; check "second apply exits 0 (got $RC2)" $?

init_clobbered=0; init_not_kept=0; copy_stale=0; n_init=0
for e in "${EXPECTED[@]}"; do
  mode="${e%%	*}"; rel="${e#*	}"; rel="${rel%	*}"
  if [ "$mode" = "init" ]; then
    n_init=$((n_init + 1))
    grep -q 'LOCAL-EDIT-MARKER' "$DST/$rel" 2>/dev/null || { init_clobbered=$((init_clobbered + 1)); echo "    clobbered: $rel"; }
    printf '%s\n' "$OUT2" | grep -qx "kept $rel" || { init_not_kept=$((init_not_kept + 1)); echo "    no 'kept' line: $rel"; }
  else
    grep -q '^v2 ' "$DST/$rel" 2>/dev/null || { copy_stale=$((copy_stale + 1)); echo "    not refreshed: $rel"; }
  fi
done
[ "$n_init" -ge 1 ] && [ "$init_clobbered" -eq 0 ]; check "init files keep local edits on second apply ($n_init init files)" $?
[ "$init_not_kept" -eq 0 ];                          check "second apply prints 'kept <dst>' for each existing init file" $?
[ "$copy_stale" -eq 0 ];                             check "copy/exec files are overwritten on second apply" $?

# --- Dry run into a fresh destination writes nothing
DST2="$TMP/dst-dry"
OUT3="$(apply_manifest "$SRC" "$DST2" --dry-run 2> "$TMP/err3")"; RC3=$?
[ "$RC3" -eq 0 ]; check "dry-run exits 0 (got $RC3)" $?
n_written=$(find "$DST2" -type f 2>/dev/null | wc -l | tr -d ' ')
[ "$n_written" -eq 0 ]; check "dry-run writes nothing ($n_written files under dst)" $?
n_would=$(printf '%s\n' "$OUT3" | grep -c '^would-install ')
[ "$n_would" -eq "${#EXPECTED[@]}" ]; check "dry-run prints 'would-install <dst>' per file ($n_would)" $?

# --- Custom manifest: unmatched glob warns but does not fail; other entries still apply
DST3="$TMP/dst-custom"
CUSTOM="$TMP/custom-manifest.txt"
printf '# custom\ncopy\tnothing/*.zzz\tnothing/\nexec\tscripts/team-check.sh\tscripts/\n' > "$CUSTOM"
OUT4="$(apply_manifest "$SRC" "$DST3" --manifest "$CUSTOM" 2> "$TMP/err4")"; RC4=$?
[ "$RC4" -eq 0 ];                              check "unmatched glob: exit 0 (got $RC4)" $?
grep -qi 'no match' "$TMP/err4";               check "unmatched glob: warning on stderr" $?
[ -x "$DST3/scripts/team-check.sh" ];          check "unmatched glob: remaining entries still installed" $?
[ ! -e "$DST3/nothing" ];                      check "unmatched glob: no directory created for the empty entry" $?

# --- Group filter: --group installs only matching entries; missing column defaults to core
DST5="$TMP/dst-core"
OUT5="$(apply_manifest "$SRC" "$DST5" --group core 2> "$TMP/err5")"; RC5=$?
n_core_expected=$(printf '%s\n' "${EXPECTED[@]}" | grep -c '	core$')
n_core_got=$(printf '%s\n' "$OUT5" | grep -c '^installed ')
[ "$RC5" -eq 0 ] && [ "$n_core_got" -eq "$n_core_expected" ]
check "--group core installs exactly the core entries ($n_core_got/$n_core_expected)" $?
[ ! -e "$DST5/.claude" ] && [ ! -e "$DST5/.agents/hooks" ] && [ -f "$DST5/scripts/team-update.sh" ] && [ -f "$DST5/.agents/config.yaml" ]
check "--group core: no .claude/ or .agents/hooks/, but scripts and .agents/config.yaml land" $?

DST6="$TMP/dst-claude"
OUT6="$(apply_manifest "$SRC" "$DST6" --group claude 2> "$TMP/err6")"; RC6=$?
n_claude_expected=$(printf '%s\n' "${EXPECTED[@]}" | grep -c '	claude$')
n_claude_got=$(printf '%s\n' "$OUT6" | grep -c '^installed ')
[ "$RC6" -eq 0 ] && [ "$n_claude_got" -eq "$n_claude_expected" ]
check "--group claude installs exactly the claude entries ($n_claude_got/$n_claude_expected)" $?
[ -f "$DST6/.claude/settings.local.json" ] && [ -x "$DST6/.agents/hooks/heartbeat.sh" ] && [ ! -e "$DST6/scripts" ]
check "--group claude: hooks and settings land, no scripts/" $?
[ $((n_core_got + n_claude_got)) -eq "${#EXPECTED[@]}" ]
check "core + claude cover every manifest entry" $?

DST7="$TMP/dst-groups"
OUT7="$(apply_manifest "$SRC" "$DST7" --group core,claude 2>/dev/null)"
[ "$(printf '%s\n' "$OUT7" | grep -c '^installed ')" -eq "${#EXPECTED[@]}" ]
check "--group core,claude (comma-separated) installs everything" $?

DST8="$TMP/dst-nogroup"
NOGROUP="$TMP/nogroup-manifest.txt"
printf 'copy\tscripts/team-check.sh\tscripts/\nexec\t.agents/hooks/heartbeat.sh\t.agents/hooks/\tclaude\n' > "$NOGROUP"
OUT8="$(apply_manifest "$SRC" "$DST8" --manifest "$NOGROUP" --group core 2>/dev/null)"
[ -f "$DST8/scripts/team-check.sh" ] && [ ! -e "$DST8/.agents" ] && [ "$(printf '%s\n' "$OUT8" | grep -c '^installed ')" -eq 1 ]
check "entry with no group column defaults to core" $?

OUT9="$(apply_manifest "$SRC" "$TMP/dst-nosuch" --group nosuch 2>/dev/null)"; RC9=$?
[ "$RC9" -eq 0 ] && [ -z "$OUT9" ] && [ ! -e "$TMP/dst-nosuch" ]
check "--group with no matching entries: exit 0, nothing installed" $?

# --- Error paths
apply_manifest "$SRC" "$TMP/dst-x" --manifest "$TMP/does-not-exist.txt" > /dev/null 2>&1
[ $? -ne 0 ]; check "missing manifest file: non-zero exit" $?

DST4="$TMP/dst-is-a-file"; : > "$DST4"
apply_manifest "$SRC" "$DST4" > /dev/null 2>&1
[ $? -ne 0 ]; check "copy error (destination root is a regular file): non-zero exit" $?

apply_manifest "$SRC" > /dev/null 2>&1
[ $? -ne 0 ]; check "usage error (missing DST_ROOT): non-zero exit" $?

# --- Works under set -e in a caller (setup.sh / team-update.sh both use it)
bash -ec "source \"$LIB\"; apply_manifest \"$SRC\" \"$TMP/dst-sete\" > /dev/null"
check "apply_manifest completes under 'set -e'" $?

finish

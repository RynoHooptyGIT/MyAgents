#!/usr/bin/env bash
# Factory gate runner. Usage: gates.sh [repo_dir [base_ref]]
# Runs the repo's checks (bash scripts/test.sh) and prints exactly one final line:
#   FACTORY-GATES: PASS | FAIL | MISCONFIGURED
# Exit codes: 0 PASS, 1 FAIL, 2 MISCONFIGURED. A check that cannot run is MISCONFIGURED.
set -u

verdict() {
  echo "FACTORY-GATES: $1"
  case "$1" in PASS) exit 0 ;; FAIL) exit 1 ;; *) exit 2 ;; esac
}

DIR="${1:-}"
if [ -z "$DIR" ]; then
  DIR="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)" || verdict MISCONFIGURED
fi

[ -d "$DIR" ] || { echo "gates: repo dir not found: $DIR"; verdict MISCONFIGURED; }
command -v bash >/dev/null 2>&1 || { echo "gates: bash not found"; verdict MISCONFIGURED; }
command -v python3 >/dev/null 2>&1 || { echo "gates: python3 not found"; verdict MISCONFIGURED; }
[ -f "$DIR/scripts/test.sh" ] || { echo "gates: scripts/test.sh missing in $DIR"; verdict MISCONFIGURED; }
python3 -m pytest --version >/dev/null 2>&1 || { echo "gates: pytest not available"; verdict MISCONFIGURED; }

# Trusted-base check (when a base ref is given): the gate entry script and everything it
# discovers or executes must be identical to the base commit. A worker that changed,
# added or deleted any of them gets MISCONFIGURED instead of a verdict it could forge.
BASE="${2:-}"
if [ -n "$BASE" ]; then
  git -C "$DIR" rev-parse --verify -q "$BASE^{commit}" >/dev/null 2>&1 \
    || { echo "gates: base ref not found: $BASE"; verdict MISCONFIGURED; }
  CHANGED="$( { git -C "$DIR" diff --name-only --no-renames "$BASE" -- ; \
                git -C "$DIR" ls-files --others --exclude-standard ; } 2>/dev/null )"
  shopt -s nocasematch
  BAD=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      scripts/test.sh|scripts/test-*.sh|scripts/apply-contract.sh|scripts/check-settings-drift.sh|\
      scripts/lib/*|scripts/factory/*|.agents/*|.claude/*|team/engine/*|\
      templates/settings.local.json.template|\
      conftest.py|*/conftest.py|pytest.ini|*/pytest.ini|pyproject.toml|*/pyproject.toml|\
      setup.cfg|*/setup.cfg|tox.ini|*/tox.ini)
        echo "gates: protected gate file changed by worker: $f"; BAD=1 ;;
    esac
  done <<< "$CHANGED"
  shopt -u nocasematch
  [ "$BAD" -eq 0 ] || verdict MISCONFIGURED
  git -C "$DIR" show "$BASE:scripts/test.sh" 2>/dev/null | cmp -s - "$DIR/scripts/test.sh" \
    || { echo "gates: scripts/test.sh differs from base $BASE"; verdict MISCONFIGURED; }
fi

OUTPUT="$(cd "$DIR" && bash scripts/test.sh 2>&1)"
CODE=$?

# Check output is untrusted: defuse any line that looks like a verdict.
while IFS= read -r line; do
  case "$line" in
    "FACTORY-GATES:"*) echo "> $line" ;;
    *) echo "$line" ;;
  esac
done <<< "$OUTPUT"

case "$CODE" in
  0) verdict PASS ;;
  1) verdict FAIL ;;
  *) echo "gates: scripts/test.sh exited with unexpected code $CODE"; verdict MISCONFIGURED ;;
esac

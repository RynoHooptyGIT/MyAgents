#!/usr/bin/env bash
set -u

# Comprehensive test harness
# Runs pytest, all test harnesses, apply-contract check, and settings drift check
# Usage: bash scripts/test.sh [--quiet]

QUIET=false
for arg in "$@"; do
  if [[ "$arg" == "--quiet" ]]; then
    QUIET=true
  fi
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PYTEST_PASSED=0
HARNESS_PASSED=0
HARNESSES_TOTAL=0
CONTRACT_OK=true
SETTINGS_OK=true
FAILURES=()

# --- Unified check function ---
# run_check NAME EXIT_CODE OUTPUT
# Returns: 0 if green, 1 if red
# On red: appends to FAILURES array and prints tail (always, even in quiet mode)
run_check() {
  local name=$1
  local exit_code=$2
  local output=$3

  if [[ $exit_code -eq 0 ]]; then
    if [[ "$QUIET" == "false" ]]; then
      echo "$name OK"
    fi
    return 0
  else
    FAILURES+=("$name")
    echo "$name FAILED — last 15 lines:"
    printf '%s\n' "$output" | tail -15
    return 1
  fi
}

# --- Run pytest ---
if [[ "$QUIET" == "false" ]]; then
  echo "Running pytest..."
fi
PYTEST_OUTPUT=$(python3 -m pytest -q 2>&1)
PYTEST_EXIT=$?

# Parse pytest output for passed count (robust: handle all-failed, collection crash, etc)
PYTEST_PASSED=$(printf '%s\n' "$PYTEST_OUTPUT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' | head -1)
[ -n "$PYTEST_PASSED" ] || PYTEST_PASSED=0

# Check pytest result
if run_check "pytest" "$PYTEST_EXIT" "$PYTEST_OUTPUT"; then
  :  # success, no-op
fi

# --- Run all test harnesses ---
# Find all .agents/hooks/test-*.sh and scripts/test-*.sh (except test.sh itself), sorted
HARNESSES=()
while IFS= read -r harness; do
  HARNESSES+=("$harness")
done < <((find .agents/hooks -name "test-*.sh" -type f; find scripts -name "test-*.sh" -type f | grep -v "scripts/test.sh$") | sort)

for harness in "${HARNESSES[@]:-}"; do
  HARNESSES_TOTAL=$((HARNESSES_TOTAL + 1))
  if [[ "$QUIET" == "false" ]]; then
    echo "Running $harness..."
  fi

  HARNESS_OUTPUT=$(bash "$harness" 2>&1)
  HARNESS_EXIT=$?

  # Harness passes if exit 0 AND output contains "0 failed"
  if [[ $HARNESS_EXIT -eq 0 ]] && printf '%s\n' "$HARNESS_OUTPUT" | grep -q "0 failed"; then
    HARNESS_PASSED=$((HARNESS_PASSED + 1))
    if [[ "$QUIET" == "false" ]]; then
      echo "$harness OK"
    fi
  else
    if run_check "$harness" 1 "$HARNESS_OUTPUT"; then
      :  # impossible, but keeps symmetry
    fi
  fi
done

# --- Run apply-contract check ---
if [[ "$QUIET" == "false" ]]; then
  echo "Checking apply-contract wiring..."
fi
CONTRACT_OUTPUT=$(bash "$REPO_ROOT/scripts/apply-contract.sh" --check 2>&1)
CONTRACT_EXIT=$?

if run_check "apply-contract" "$CONTRACT_EXIT" "$CONTRACT_OUTPUT"; then
  CONTRACT_OK=true
else
  CONTRACT_OK=false
fi

# --- Run settings drift check (template hooks == local hooks) ---
if [[ "$QUIET" == "false" ]]; then
  echo "Checking settings template drift..."
fi
SETTINGS_OUTPUT=$(bash "$REPO_ROOT/scripts/check-settings-drift.sh" 2>&1)
SETTINGS_EXIT=$?

if run_check "settings-drift" "$SETTINGS_EXIT" "$SETTINGS_OUTPUT"; then
  SETTINGS_OK=true
else
  SETTINGS_OK=false
fi

# --- Summary ---
CONTRACT_STATUS="ok"
if [[ "$CONTRACT_OK" == "false" ]]; then
  CONTRACT_STATUS="FAIL"
fi
SETTINGS_STATUS="ok"
if [[ "$SETTINGS_OK" == "false" ]]; then
  SETTINGS_STATUS="FAIL"
fi

SUMMARY="TESTS: pytest $PYTEST_PASSED passed · harnesses $HARNESS_PASSED/$HARNESSES_TOTAL green · contract $CONTRACT_STATUS · settings $SETTINGS_STATUS"

echo "$SUMMARY"

# --- Exit code ---
EXIT_CODE=0
if [[ ${#FAILURES[@]} -gt 0 ]]; then
  EXIT_CODE=1
fi

exit $EXIT_CODE

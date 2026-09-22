#!/usr/bin/env bash
set -u

# Comprehensive test harness
# Runs pytest, all test harnesses, and apply-contract check
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
PYTEST_FAILED=0
HARNESS_PASSED=0
HARNESS_FAILED=0
HARNESSES_TOTAL=0
CONTRACT_OK=true
FAILURES=()

# --- Run pytest ---
if [[ "$QUIET" == "false" ]]; then
  echo "Running pytest..."
fi
PYTEST_OUTPUT=$(python3 -m pytest -q 2>&1)
PYTEST_EXIT=$?

# Parse pytest output for passed count
PYTEST_PASSED=$(echo "$PYTEST_OUTPUT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' | head -1 || echo "0")

if [[ $PYTEST_EXIT -ne 0 ]]; then
  PYTEST_FAILED=1
  if [[ "$QUIET" == "false" ]]; then
    echo "pytest FAILED"
    echo "$PYTEST_OUTPUT" | tail -15
  fi
  FAILURES+=("pytest")
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

  if [[ $HARNESS_EXIT -eq 0 ]] && echo "$HARNESS_OUTPUT" | grep -q "0 failed"; then
    HARNESS_PASSED=$((HARNESS_PASSED + 1))
  else
    HARNESS_FAILED=$((HARNESS_FAILED + 1))
    if [[ "$QUIET" == "false" ]]; then
      echo "$harness FAILED"
      echo "$HARNESS_OUTPUT" | tail -15
    else
      # Even in quiet mode, record the failure
      FAILURES+=("$harness")
      echo "$harness FAILED — last 15 lines:"
      echo "$HARNESS_OUTPUT" | tail -15
    fi
  fi
done

# --- Run apply-contract check ---
if [[ "$QUIET" == "false" ]]; then
  echo "Checking apply-contract wiring..."
fi
CONTRACT_OUTPUT=$(bash "$REPO_ROOT/scripts/apply-contract.sh" --check 2>&1)
CONTRACT_EXIT=$?

if [[ $CONTRACT_EXIT -ne 0 ]]; then
  CONTRACT_OK=false
  if [[ "$QUIET" == "false" ]]; then
    echo "apply-contract FAILED"
    echo "$CONTRACT_OUTPUT" | tail -15
  else
    FAILURES+=("apply-contract")
    echo "apply-contract FAILED"
    echo "$CONTRACT_OUTPUT" | tail -15
  fi
fi

# --- Summary ---
CONTRACT_STATUS="ok"
if [[ "$CONTRACT_OK" == "false" ]]; then
  CONTRACT_STATUS="FAIL"
fi

SUMMARY="TESTS: pytest $PYTEST_PASSED passed · harnesses $HARNESS_PASSED/$HARNESSES_TOTAL green · contract $CONTRACT_STATUS"

if [[ "$QUIET" == "true" ]]; then
  echo "$SUMMARY"
else
  echo ""
  echo "$SUMMARY"
fi

# --- Exit code ---
EXIT_CODE=0
if [[ $PYTEST_FAILED -ne 0 ]] || [[ $HARNESS_FAILED -ne 0 ]] || [[ "$CONTRACT_OK" == "false" ]]; then
  EXIT_CODE=1
fi

exit $EXIT_CODE

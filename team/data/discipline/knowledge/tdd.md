# TDD Discipline

## Iron Law

**No production code without a failing test first. Delete means delete.**

If production code was written before a failing test exists, DELETE the production code and restart the cycle. No exceptions, no "I'll write the test after."

## Principle

The red-green-refactor cycle is not optional or advisory — it is a hard gate. The test must exist and FAIL before any production code is written. The production code must be the MINIMUM needed to make the test pass. Refactoring happens only with green tests. Writing production code first and then "covering" it with tests produces fundamentally different (worse) test suites.

## Red Flags

- Writing implementation code before any test exists
- Writing a test that passes immediately (test is not actually testing anything new)
- Writing more production code than the minimum needed to pass the current test
- Skipping the RED phase ("I know what the test should be, let me just write the code")
- "I'll add the tests after" or "Let me get the implementation working first"
- Refactoring while tests are red
- Deleting or modifying tests to make them pass instead of fixing the code

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "I'll write the tests right after" | Test-after produces coverage theater. Delete the code, write the test. |
| "This is too simple to need TDD" | Simple code with a failing test first takes 30 seconds. Do it. |
| "I need to see the implementation shape first" | That's design, not coding. Sketch in comments, then write a test. |
| "The test framework isn't set up for this yet" | Set it up. That's the task now. |
| "TDD doesn't work for UI code" | Component TDD exists. Use it. |
| "I'm just exploring / prototyping" | Prototype in a scratch file, then TDD the real implementation. |

## Enforcement Protocol

1. **Before writing any production code**: Write a test that describes the expected behavior
2. **Run the test**: Confirm it FAILS (show the failure output)
3. **If the test passes immediately**: STOP — investigate. The test is not testing new behavior.
4. **Write minimum production code**: Only enough to make the failing test pass
5. **Run the test again**: Confirm it PASSES (show the pass output)
6. **Refactor**: Only with green tests. Run tests after refactoring.

## Hard Gate

```
CHECK-SEQUENCE:
  1. Test written BEFORE production code
  2. Test FAILED first (failure output shown)
  3. Production code is MINIMAL (only what the test requires)
  4. Test PASSES after production code (pass output shown)
  5. Any refactoring done with green tests only

ON-VIOLATION (code written before test):
  - DELETE the production code
  - Write the test first
  - Confirm the test fails
  - Re-implement minimally
  - NO EXCEPTIONS
```

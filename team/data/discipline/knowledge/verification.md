# Verification Discipline

## Iron Law

**No completion claims without fresh verification evidence in the current context.**

"Tests were passing" is not evidence. "It should work" is not evidence. Only fresh command output visible in the current session counts.

## Principle

Every claim of completion must be backed by a verification artifact — command output, test results, or build logs — produced **in this session**, **after the final code change**, and **visible in context**. Stale evidence from earlier steps does not carry forward past code modifications.

## Red Flags

- Claiming tests pass without showing test output
- Saying "all tests pass" after modifying code but before re-running tests
- Referencing test results from before the last code change
- Using exit codes alone as evidence (exit code 0 without visible output)
- Saying "it should work" or "this looks correct" instead of running the verification
- Marking a task `[x]` without a verification step between the last code change and the mark

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "I just ran the tests a minute ago" | Code changed since then. Run again. |
| "This is a trivial change, no need to re-test" | Trivial changes cause regressions. Run the tests. |
| "The test output is too long to show" | Show it anyway, or show the summary with pass/fail counts. |
| "Exit code 0 means it passed" | Exit codes can lie. Show the actual output. |
| "I'm confident this works" | Confidence is not evidence. Run the command. |
| "Re-running would waste time" | Shipping broken code wastes more time. Run the tests. |

## Enforcement Protocol

1. **Before any completion claim**: Run the verification command fresh
2. **After running**: Show the FULL output (or meaningful summary with counts)
3. **After showing output**: Confirm the output matches the claim
4. **Only then**: Mark the task complete or claim success

## Hard Gate

```
CHECK-SEQUENCE:
  1. Completion claim identified
  2. Verification command run FRESH (after last code change)
  3. FULL output visible in current context
  4. Output confirms the claim (not contradicts it)

ON-VIOLATION:
  - REFUSE to mark task complete
  - REFUSE to proceed to next task
  - Run the verification command immediately
  - Show the output before continuing
```

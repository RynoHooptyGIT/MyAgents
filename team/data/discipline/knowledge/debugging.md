# Debugging Discipline

## Iron Law

**No fixes without root cause investigation first. Three failed attempts means escalate.**

Never jump to code changes when encountering an error. Read the FULL error, state a hypothesis, THEN attempt a fix. Track attempts. At 3 failed fixes, HALT and escalate.

## Principle

Debugging is hypothesis-driven investigation, not trial-and-error patching. Each fix attempt must be preceded by reading the complete error message, forming an explicit hypothesis about the root cause, and stating that hypothesis before changing code. Random fixes compound problems. After 3 failed attempts, the hypothesis is likely wrong — escalate rather than dig deeper into the wrong hole.

## Red Flags

- Changing code immediately after seeing an error without reading the full message
- "Let me try this" without stating what "this" is expected to fix and why
- Making multiple changes at once (can't tell which one fixed it)
- Ignoring stack traces or error context
- Repeating the same fix approach that already failed
- Fixing symptoms instead of root causes
- Not tracking how many fix attempts have been made
- Continuing past 3 failed attempts without escalation

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "I know what this error means" | Then state the hypothesis explicitly. Takes 5 seconds. |
| "Let me just try a quick fix" | Quick fixes without hypotheses create new bugs. State the hypothesis. |
| "The error message isn't helpful" | Read the FULL message, stack trace, and context. Then state what you know. |
| "I've almost got it, one more try" | You said that 2 attempts ago. Escalate. |
| "Escalating wastes time" | Spending 30 minutes on the wrong hypothesis wastes more time. |
| "I'll just try a different approach" | Different approach = new hypothesis. State it explicitly. |

## Enforcement Protocol

1. **When an error occurs**: Read the COMPLETE error message (full stack trace, all context)
2. **Before any code change**: State an explicit hypothesis ("This fails because X, and changing Y should fix it because Z")
3. **Make ONE change**: Only the change your hypothesis predicts will fix the issue
4. **Verify**: Run the test/command and check the result
5. **Track attempts**: Increment `debug_attempt_count` after each failed fix
6. **At 3 failed attempts**: HALT — present all hypotheses tried, suggest escalation options

## Hard Gate

```
CHECK-SEQUENCE:
  1. Error read COMPLETELY (full message, stack trace, context)
  2. Root cause hypothesis stated BEFORE any code change
  3. Hypothesis is explicit ("X fails because Y")
  4. Single change made matching the hypothesis
  5. Result verified after the change

ESCALATION PROTOCOL (debug_attempt_count >= 3):
  - HALT implementation
  - Present: all hypotheses attempted and their outcomes
  - Recommend escalation options:
    a. Try fundamentally different approach
    b. Request architect review
    c. Manual investigation with additional tooling
    d. Isolate the problem in a minimal reproduction
  - WAIT for user decision before continuing
```

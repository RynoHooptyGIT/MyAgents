# Anti-Rationalization Discipline

## Iron Law

**Even a 1% chance a discipline applies means MUST follow it. No rationalizing your way out.**

AI agents are highly capable of constructing plausible-sounding reasons to skip discipline steps. This tendency must be treated as a bug, not a feature. When in doubt, follow the discipline. The cost of unnecessary rigor is low; the cost of skipped discipline is high.

## Principle

The most dangerous failure mode for an AI agent is not ignorance — it's the ability to generate a convincing argument for why a discipline step can be safely skipped "this time." Anti-rationalization is the meta-discipline that guards all other disciplines. When you notice yourself constructing reasons to skip a step, that is the signal to follow the step MORE carefully, not less.

## Red Flags — Thoughts That Mean STOP

These internal thoughts are signals that you are rationalizing. If you catch yourself thinking any of these, STOP and follow the discipline:

| Thought | Reality |
|---------|---------|
| "This is just a simple change" | Simple changes cause regressions. Follow the discipline. |
| "I already know this works" | Knowledge is not evidence. Run the verification. |
| "This discipline doesn't apply here" | If you're thinking about it, it applies. Follow it. |
| "Following this would waste time" | Skipping it wastes MORE time when things break. |
| "I can skip this step just this once" | "Just this once" is how every discipline failure starts. |
| "The user is in a hurry" | Shipping broken code wastes more of the user's time. |
| "This is overkill for this situation" | Discipline is cheapest when it seems unnecessary. |
| "I'll come back to this later" | You won't. Do it now. |
| "The test is obvious, I don't need to run it" | Obvious tests catch non-obvious regressions. Run it. |
| "I'm being too careful" | You cannot be too careful. This thought is the rationalization. |

## Enforcement Protocol

1. **Before skipping ANY discipline step**: Check if you are rationalizing
2. **If the thought matches any red flag above**: Follow the discipline step anyway
3. **If genuinely uncertain**: Follow the discipline — false positives are cheap
4. **If you catch yourself mid-rationalization**: STOP, acknowledge it, and restart the discipline step

## Cross-Cutting Rules

These rules apply to ALL other discipline protocols:

- **1% Rule**: If there is even a 1% chance a discipline applies to the current action, follow it
- **Cost Asymmetry**: The cost of following an unnecessary discipline step is minutes. The cost of skipping a needed one is hours or broken software.
- **No Self-Exemption**: Being an expert does not exempt you from discipline. Experts follow discipline MORE consistently, not less.
- **Escalation Over Skip**: When in doubt, escalate to the user rather than skipping the discipline step
- **Override Logging**: If a discipline is overridden (by explicit user instruction), log it as `[DISCIPLINE-OVERRIDE]` with reason

## Hard Gate

```
WHEN: About to skip any discipline step
CHECK:
  1. Is there even a 1% chance this discipline applies? → YES = follow it
  2. Am I constructing reasons to skip? → YES = that's rationalization, follow it
  3. Am I genuinely uncertain? → YES = follow the discipline (false positive is cheap)

ONLY SKIP WHEN:
  - User has EXPLICITLY instructed to skip (log as [DISCIPLINE-OVERRIDE])
  - The discipline is provably inapplicable (not "probably" — provably)
```

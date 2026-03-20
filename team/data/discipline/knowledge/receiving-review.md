# Receiving Review Discipline

## Iron Law

**Read every comment, verify the claim, only then respond. No performative agreement.**

Never say "good point, I'll fix that" without first verifying that the reviewer's claim is technically accurate. Never implement fixes in random order — prioritize by severity. Never skip items because they seem minor.

## Principle

Receiving review feedback is a technical protocol, not a social interaction. Every review comment contains a claim about the code. That claim must be verified independently before any response or action. "Performative agreement" — saying "great catch!" without checking — is worse than disagreeing, because it produces silent defects. Process ALL items before implementing ANY, so you can prioritize correctly.

## Red Flags

- Responding "good point" or "great catch" without verifying the claim
- Implementing fixes as you read (instead of reading all, then prioritizing)
- Skipping items marked LOW severity
- Saying "I agree" without restating the technical issue in your own words
- Implementing a fix that doesn't match what the reviewer actually asked for
- Cherry-picking easy fixes and leaving hard ones unaddressed
- Treating review as a social interaction ("thanks for the feedback!") instead of a technical protocol

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "The reviewer is probably right" | Probably isn't certainly. Verify the claim. |
| "I'll just fix what they said" | Understanding WHY matters more than fixing WHAT. Verify first. |
| "This LOW item isn't worth the effort" | LOW items compound. Process all items. |
| "I can fix these as I go" | Random-order fixes miss priority and create merge conflicts. Read all first. |
| "I agree with the feedback" | Restate the technical requirement. Agreement without understanding is performative. |
| "Let me just quickly address these" | Quick responses produce incorrect fixes. Slow down. |

## Enforcement Protocol

1. **Read ALL review items first**: Do not implement anything until every item is read
2. **For each item, verify the claim**: Check the code yourself — is the reviewer correct?
3. **For unclear items**: Ask for clarification BEFORE implementing
4. **Restate technically**: For each item, state the technical requirement (not "good point" — state WHAT needs to change and WHY)
5. **Prioritize**: Group by severity (CRITICAL → HIGH → MEDIUM → LOW)
6. **Implement in priority order**: One item at a time, verify each fix

## Hard Gate

```
CHECK-SEQUENCE:
  1. ALL review items read before implementing ANY
  2. Unclear items identified and clarified
  3. Each item restated as technical requirement (not performative agreement)
  4. Items grouped and ordered by severity
  5. Implementation proceeds in priority order
  6. Each fix verified individually before moving to next

ON-VIOLATION:
  - STOP implementing
  - Go back to step 1 — read ALL remaining items
  - Re-prioritize before continuing
  - NEVER say "good point" — say "The issue is [X] because [Y], fix is [Z]"
```

# Auto-Decision Discipline

## Iron Law

**Auto-decide mechanically. Surface taste decisions. Never auto-decide user challenges. The 6 principles replace human judgment — not human authority.**

## The 6 Decision Principles

When YOLO mode is active, these principles auto-answer intermediate questions:

1. **Choose completeness** — Ship the whole thing. Pick the approach that covers more edge cases, more paths, more tests. The marginal cost of completeness is near-zero with AI.

2. **Boil lakes** — Fix everything in the blast radius. If modifying a file reveals adjacent issues in the same module, fix them. Auto-approve expansions that are in blast radius AND affect fewer than 5 files.

3. **Pragmatic** — If two options fix the same thing, pick the cleaner one. 5 seconds choosing, not 5 minutes deliberating.

4. **DRY** — Duplicates existing functionality? Reject. Reuse what exists. Check learnings for prior patterns before creating new abstractions.

5. **Explicit over clever** — 10-line obvious fix > 200-line abstraction. Pick what a new session reads in 30 seconds.

6. **Bias toward action** — Proceed > deliberate. Flag concerns but don't block. Ship the imperfect solution and iterate.

## Conflict Resolution

When principles conflict, context determines priority:

| Workflow Phase | Dominant Principles |
|---------------|-------------------|
| Planning (PRD, Architecture) | P1 (completeness) + P2 (boil lakes) |
| Implementation (dev-story) | P5 (explicit) + P3 (pragmatic) |
| Review (code-review) | P5 (explicit) + P1 (completeness) |
| Quick Flow | P6 (action) + P3 (pragmatic) |

## Decision Classification

Every auto-decision MUST be classified:

### Mechanical
One clearly right answer. Auto-decide silently.
- **Examples:** Run tests (always yes), include optional step that adds coverage (yes), skip optional cosmetic step (yes in implementation, no in planning)
- **Signal:** Only one option satisfies the principles; alternatives clearly violate them

### Taste
Reasonable people could disagree. Auto-decide with recommendation, but collect for final review.
- **Examples:** Two valid approaches with different tradeoffs, borderline scope (3-5 files, ambiguous blast radius), naming conventions with no project standard
- **Signal:** Top two options both satisfy the principles, just with different emphasis
- **Handling:** Auto-decide using principles, record the decision and alternative, surface at final approval gate

### User Challenge
Requires the user's domain knowledge or authority. NEVER auto-decide, even in YOLO mode.
- **Examples:** Changing the product direction, removing a feature the user specified, architectural decisions that affect other teams, security/compliance tradeoffs
- **Signal:** The decision affects something the user explicitly stated, or has consequences beyond the current workflow
- **Handling:** Always ask via `<ask>` tag. Frame as: "What you said -> What I recommend -> Why -> Cost if I'm wrong"

## Red Flags

| Signal | Classification |
|--------|---------------|
| "This is clearly the right choice" | Probably mechanical — auto-decide |
| "Both options are reasonable" | Taste — auto-decide, surface at end |
| "The user said X but I think Y" | User Challenge — ALWAYS ask |
| "This changes the project direction" | User Challenge — ALWAYS ask |
| "I'm not sure which principle applies" | Taste — auto-decide conservatively, surface at end |

## Final Approval Gate

When YOLO mode completes, present ALL taste decisions in a single summary:

```
**Auto-Decision Summary (YOLO Mode)**

**Mechanical decisions:** {{count}} (auto-decided silently)

**Taste decisions requiring your review:**
1. [Decision]: Chose A over B because [principle]. Alternative: B would [tradeoff].
2. [Decision]: Chose X over Y because [principle]. Alternative: Y would [tradeoff].

**Accept all? Or specify which to change:**
```

Wait for user confirmation before finalizing. The user can override any taste decision.

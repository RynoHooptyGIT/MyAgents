# Learnings Discipline

## Iron Law

**Search learnings before building. Capture learnings after shipping. The team's memory is only as good as what gets recorded.**

## When This Applies

- Before starting any implementation workflow (dev-story, create-story)
- After completing any review workflow (code-review)
- After debugging sessions that reveal architectural patterns
- After discovering framework quirks or version-specific behavior

## Red Flags

| Signal | What's Happening |
|--------|-----------------|
| "I think we fixed something like this before" | STOP — search learnings first |
| Same file getting bug fixes repeatedly | Architectural smell — capture as a learning |
| Framework API used differently than docs suggest | Capture the correct usage as a learning |
| Review finds a pattern violation | Capture the pattern as a learning |
| A workaround is needed for a known issue | Capture the workaround so others don't re-discover it |

## Rationalization Defense

| Excuse | Reality |
|--------|---------|
| "This is obvious, no need to record it" | Obvious to you now, invisible to the next session. Record it. |
| "The fix is in the code" | Code shows WHAT, not WHY. The learning captures WHY. |
| "It's too small to matter" | Small learnings compound. 50 small entries > 0 entries. |
| "I'll remember this" | You won't. The next session starts with zero memory. Record it. |

## Learning Types

| Type | When to Use | Example |
|------|------------|---------|
| **pattern** | Discovered a reusable approach | "All API routes must validate tenant_id before any DB query" |
| **pitfall** | Found a non-obvious failure mode | "Redis cache TTL must account for timezone — UTC only" |
| **decision** | Made an architectural choice with rationale | "Chose Playwright over Puppeteer for CDP stability" |
| **architecture** | Discovered structural constraint | "Auth middleware must run before RLS policy check" |

## Enforcement

- **Before implementation:** Invoke `learnings-search` protocol. Surface relevant entries.
- **After code-review:** If review found patterns, pitfalls, or architectural insights, invoke `learnings-capture` protocol.
- **After debugging:** If root cause reveals a non-obvious failure mode, capture as a pitfall learning.
- **Pruning:** Periodically invoke `learnings-prune` to remove stale entries referencing deleted files.

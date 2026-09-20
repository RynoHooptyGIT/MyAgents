# Learnings Discipline

## Iron Law

**Search learnings before building. Capture learnings after shipping. The team's memory is only as good as what gets recorded.**

## How It Works Now

Learnings are captured automatically by the instinct capture loop — you do not write `learnings.jsonl` by hand.

| Step | Mechanism |
|---|---|
| Capture | `UserPromptSubmit` + `PostToolUse` hooks append to `team/_memory/_learnings/observations.jsonl` (local, gitignored) |
| Mine | `Stop` hook pre-filters corrections, error resolutions, and repeated workflows; spawns a Haiku miner only when ≥ `min_candidates` exist |
| Review | Instincts land as `pending`; Athena surfaces them per Oracle mode, or run `/team:instincts review` |
| Recall | `SessionStart` injects the top active instincts; `python3 scripts/instincts/instinct.py status` shows all |

Config: `instincts:` block in `.agents/config.yaml`. Off switch: `.instincts-off` at repo root.

## When This Applies

- "Search before building" → read the `[instincts]` block at session start, or run `python3 scripts/instincts/instinct.py status`
- "Capture after shipping" → automatic; review pending instincts before you commit so accepted ones ship with the branch
- After a review or debugging session reveals a pattern → make sure it was captured; if not, say the correction out loud in a prompt ("no, use X instead") so the next Stop picks it up

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

Instinct domains map onto these: pattern/architecture → workflow|code-style, pitfall → debugging|tooling, decision → (belongs in .agents/decisions/, not an instinct).

## Enforcement

- **Before implementation:** Run `python3 scripts/instincts/instinct.py status` and read the `[instincts]` block injected at session start. Apply active instincts as context, not policy.
- **After code-review / debugging:** Capture is automatic via the Stop-hook miner. If a pattern was learned, make sure it surfaced — state the correction plainly in a prompt so the miner sees it. Review pending instincts with `/team:instincts review` before committing.
- **Pruning:** `python3 scripts/instincts/instinct.py prune` (or Athena's [IN] menu) removes stale pending/rejected instincts.

---
name: slim-audit
description: Use when token cost is high or someone asks to "slim down", reduce token usage, cut context bloat, or optimize the team/agent/workflow files. Audits command/agent/workflow markdown for bloat, measures per-asset token cost, and applies BMAD-style context engineering (JIT step-loading, document sharding, lazy activation) to cut the per-request footprint.
---

# Slim Audit — Token Cost Reduction

## Core principle

In an interactive agent, the typed prompt is almost never the cost. The cost is
**context that gets loaded**: system instructions, tool/skill definitions, fat
agent personas, and tool output that piles up. You cut tokens by loading less,
later, and in a child context — not by compressing the user's sentence.

This is the BMAD v6 lever (reported 74–90% reduction). It comes from four moves:

1. **JIT step-loading** — load only the current step's instructions; drop prior
   steps once done. (Monolithic 15k → 2–3k per step.)
2. **Document sharding** — split big docs; load an index, then only the relevant
   section. (45k → 8k.)
3. **Fresh context per phase** — start a new conversation at each major phase so
   prior-phase bloat doesn't ride along.
4. **Subagent isolation** — do heavy file reading in a child agent; the main
   thread receives a ~500-token summary instead of 150k of file dumps.

## When to use

- User says "slim down", "reduce tokens", "cut cost", "too expensive", "context bloat".
- Before adding new agents/workflows (keep the per-session footprint flat).
- After noticing a session ballooning in token usage.

## Step 1 — Measure (always first; never guess)

Run the audit scanner to get real numbers, not estimates:

```bash
bash skills/slim-audit/scripts/audit.sh
```

It reports per-directory totals and flags every file over threshold. Known
baseline for this repo (re-run to refresh):

| Asset       | Files | Size    | ~Tokens | Note |
|-------------|-------|---------|---------|------|
| Commands    | 84    | ~65 KB  | ~17k    | thin, fine |
| Agents      | 29    | ~316 KB | ~79k    | `oracle.md` sole orchestrator (sharded); fattest experts ~5k each |
| Workflows   | 509   | ~3.3 MB | ~820k   | the elephant |

`oracle.md` (~7k tokens) loads **every session** via CLAUDE.md ambient
monitoring — it is the single highest-leverage target.

## Step 2 — Classify each fat file

For every file the scanner flags (default threshold 8 KB / ~2k tokens), decide:

- **Always-loaded?** (referenced in CLAUDE.md, an agent activation, or a hook) →
  highest priority. Every token here is paid every session.
- **On-demand?** (a command/agent invoked only when needed) → lower priority;
  bloat only costs when used.

Always-loaded bloat is the bug. On-demand bloat is usually fine.

## Step 3 — Apply the right cut

**A. Shard the persona (for always-loaded agents like oracle/maestro)**
Split into a thin *activation core* (identity, mode toggles, dispatch table —
the part needed to start) and *reference sections* loaded only when a branch
fires. Activation core target: ≤ 1.5k tokens.

```
oracle.md            → oracle.md (thin core, ~1.5k)  +  oracle-reference/*.md (lazy)
```

The core ends with: "For X, read `oracle-reference/x.md`." The model loads the
section only when it hits branch X.

**B. JIT step-files (for multi-step workflows)**
Replace one monolithic workflow file with a `steps/` dir + a tiny index. The
runner loads `steps/NN.md` for the current step only and drops it after.

**C. Lazy skill/command activation**
Keep the frontmatter `description` tight and trigger-rich (it's what's scanned),
but keep the body out of the always-on path. Don't reference fat files from
CLAUDE.md — reference the thin entrypoint that *pulls in* detail on demand.

**D. Subagent isolation (runtime, not a file edit)**
For any task that reads many files (search, audit, "find all X"), dispatch a
subagent and consume its summary. Encoded in the runtime hook's directive.

**E. Compress genuinely large static context**
For big pasted logs / docs / RAG blocks (not personas), run the LLMLingua-2
wrapper — 50–80% reduction, meaning intact:

```bash
python scripts/compress.py --ratio 0.5 < big_context.txt
```

## Step 4 — Verify the cut

Re-run `audit.sh`. Report before/after for the always-loaded set specifically —
that's the number that matters per session. Never claim a saving without the
two scanner runs.

## What NOT to do

- Don't compress the user's prompt text — negligible saving, real intent loss.
- Don't shard on-demand files that are already small — churn for nothing.
- Don't strip content that's load-bearing (dispatch tables, mode toggles, gates).
  Move it to a lazy file; don't delete it.

## Output format

```
## Slim Audit

### Always-loaded footprint (paid every session)
- oracle.md: 7.0k tok → 1.5k tok (sharded to oracle-reference/, lazy)  ✅
- CLAUDE.md: 0.4k tok (already lean)

### On-demand bloat (paid only when invoked) — left as-is unless asked
- maestro.md: 7.1k tok  (orchestrator, invoked rarely)

### Recommended next cuts
- workflows/*: 820k tok across 509 files — convert top-10 fattest to step-files

### Net: per-session footprint -X.Xk tokens (-NN%)
```

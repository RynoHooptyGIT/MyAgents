# Token Optimization

How this repo keeps per-request token cost down. Three layers: a runtime hook,
an audit skill, and a context compressor. Built from BMAD v6 context-engineering
(74–90% reported savings) plus LLMLingua-2 prompt compression.

## The one idea

The user's typed prompt is almost never the cost. The cost is **context that
gets loaded** — system instructions, agent personas, skill bodies, and tool
output that accumulates. You cut tokens by loading **less, later, in a child
context**, not by rephrasing the user's sentence.

## Where this repo's tokens actually go (run the scanner for live numbers)

| Asset       | Files | ~Tokens | Loaded… |
|-------------|-------|---------|---------|
| Commands    | 84    | ~16k    | on invoke |
| Agents      | 30    | ~84k    | on invoke; `oracle.md` loads **every session** |
| Workflows   | 395+  | ~700k   | on invoke (step-by-step ideally) |

`oracle.md` (~7k tokens) is the highest-leverage target: ambient monitoring in
`CLAUDE.md` pulls it in every session.

## Layer 1 — Runtime hook (always on)

`.claude/hooks/slim-prompt.sh`, wired as a `UserPromptSubmit` hook. Injects a
~25-token discipline directive every turn (be concise; isolate multi-file work
in a subagent; reference lazy sections by path) and a stronger compress/isolate
hint when a large blob is pasted.

- Toggle off: `touch .slim-off`
- Tune the large-paste threshold: `SLIM_LARGE_THRESHOLD=8000` (chars).

## Layer 2 — `/slim` audit skill (the real lever)

`skills/slim-audit/`. Measures the footprint, flags fat files, separates
**always-loaded** (paid every session) from **on-demand** bloat, and applies the
right cut: persona sharding, JIT step-files, lazy activation, subagent isolation.

```bash
bash skills/slim-audit/scripts/audit.sh        # measure / re-measure
```

The four cuts, in priority order:
1. **Shard always-loaded personas** (oracle/maestro) into a thin activation core
   + lazy reference sections. Biggest per-session win.
2. **JIT step-files** for monolithic workflows — load the current step, drop it
   after.
3. **Lazy activation** — tight trigger descriptions, fat bodies off the always-on path.
4. **Subagent isolation** at runtime for heavy reads.

## Layer 3 — Context compressor (LLMLingua-2)

`scripts/compress.py`. For genuinely large *static* context (logs, docs, RAG
chunks) — not personas, not user instructions.

```bash
pip install llmlingua                           # one-time (~500 MB model)
python scripts/compress.py --ratio 0.5 < big_context.txt
```

50–80% reduction, meaning intact. Falls back to a dependency-free lexical
squeeze if `llmlingua` isn't installed (and says so on stderr).

## Rules of thumb

- Always-loaded bloat is the bug. On-demand bloat is usually fine.
- Never claim a saving without two `audit.sh` runs (before/after).
- Don't compress instructions — only reference material.
- Move load-bearing content (dispatch tables, gates) to a lazy file; don't delete it.

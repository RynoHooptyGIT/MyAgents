# Instinct Capture Loop — Design

**Date:** 2026-09-19
**Status:** approved
**Supersedes:** `team/engine/learnings.xml` (learnings.jsonl protocols, never wired)
**Related:** `docs/specs/2026-05-09-oracle-ambient-intelligence-design.md`, `docs/specs/2026-04-26-multi-agent-coordination-design.md`
**Reference:** ECC `skills/continuous-learning-v2` (affaan-m/ECC, MIT) — model and confidence rules ported; runtime redesigned to avoid a daemon.

## Problem

MyAgents remembers what an agent deliberately writes (mission memories, decisions, handoffs). It does not learn from *behavioral corrections* — the user saying "no, use X", an error resolved the same way three times, a workflow repeated every session. Those signals evaporate with the transcript. Oracle's ambient monitoring already watches every tool result, but has no on-disk state and no way to turn what it sees into durable, reusable behavior.

## Goal

Turn session activity into small, confidence-scored, evidence-backed **instincts** that are:

- captured automatically by hooks (no prompt discipline required),
- mined cheaply and off the main context (gated Haiku, no daemon),
- reviewed before they influence anyone else (pending → active, Oracle-mediated, mode-aware),
- injected compactly at session start (top-N, char-capped),
- shared with teammates and other agents via git (project tier) and promoted across projects (user tier).

## Non-goals

- Replacing `.agents/decisions/` (policy) or agent mission memories (narrative). Instincts are *hints*, never policy.
- Capturing code snippets. Instincts describe patterns; raw observations stay local and gitignored.
- Cross-harness portability (ECC Memory Vault). Claude Code only.

## Architecture

```
UserPromptSubmit ─┐
                  ├─▶ observe.sh ─▶ observations.jsonl (gitignored, 10MB rotate)
PostToolUse ──────┘                        │
                                           ▼
Stop ─▶ instinct-mine.sh ─▶ prefilter.py ─(≥ min_candidates)─▶ claude -p --model haiku (detached)
                                                                        │
                                                                        ▼
                                              instincts/<id>.yaml  status: pending
                                                                        │
                        Oracle review (suggest: ask / auto: accept ≥ 0.7) │  /team:instincts review
                                                                        ▼
SessionStart ─▶ instinct-inject.sh ─▶ instinct.py inject ─▶ [instincts] block (active only, top-N)
```

Four stages, each a separate unit with one job and a file-based interface between them.

### Stage 1 — Capture: `.agents/hooks/observe.sh`

Registered twice in `.claude/settings.local.json` (and the template):

| Event | Matcher | Args | Logs |
|---|---|---|---|
| `UserPromptSubmit` | `""` | `prompt` | `{ts, session_id, event:"prompt", text}` |
| `PostToolUse` | `""` | `tool` | `{ts, session_id, event:"tool", tool, input, response, is_error}` |

- Reads stdin JSON (`session_id`, `cwd`, `prompt` / `tool_name`, `tool_input`, `tool_response`). Parses with `python3 -c`; falls back to skipping if `python3` is absent.
- Resolves the repo root from `cwd` via `git rev-parse --show-toplevel`; writes to `<root>/team/_memory/_learnings/observations.jsonl`. No git root → exit 0, log nothing.
- `input` and `response` are JSON-serialized and truncated to 5,000 chars. `text` (prompts) truncated to 2,000 chars.
- Secret scrub before persisting: `(?i)(api[_-]?key|token|secret|password|authorization|credentials?)\s*[:=]\s*\S+` → `\1=[REDACTED]`. Applied to every string field.
- `is_error`: true if `tool_response` contains `is_error: true`, an `exit_code` ≠ 0, or a line matching `^(Error|Traceback|FAILED|error:)` in the first 500 chars.
- Rotation: if the file exceeds `observations_max_mb`, rename to `observations.jsonl.1` (replacing any previous `.1`) and start fresh.
- Contract: always `exit 0`, hook `timeout: 3000`, never writes to stdout (stdout of `UserPromptSubmit` is injected into context — this hook must stay silent).
- Respects `instincts.enabled: false` in `.agents/config.yaml` and a `.instincts-off` marker at repo root (mirrors `.slim-off`).

### Stage 2 — Mine: `.agents/hooks/instinct-mine.sh` on `Stop`

1. Guard: enabled check, `python3` present, `claude` on PATH (else append a line to `team/_memory/_learnings/miner.log` and exit 0).
2. Lock: `team/_memory/_learnings/.miner.lock` containing PID + timestamp. If present and younger than 10 min → exit 0. Older → treat as stale, overwrite.
3. `scripts/instincts/prefilter.py --since-watermark` reads observations after the byte offset stored in `.instinct-watermark`, and emits JSON `{candidates: [...], count}`. A candidate is one of:
   - **correction** — a `prompt` event whose text matches `\b(no,|nope|actually|instead|don't|do not|stop|wrong|not that)\b` (case-insensitive) within the first 120 chars, bundled with the 3 preceding tool events.
   - **error_resolution** — a `tool` event with `is_error` followed within 3 events by a non-error event of the same tool; bundled as the window.
   - **repetition** — a `(tool, normalized_input_signature)` pair seen ≥ 3× since the watermark; signature = tool name + first token of a Bash command or the file extension of an Edit/Write path. Bundled as one representative window plus the count.
   Each candidate is `{kind, window: [events…], count}` with event strings re-truncated to 1,000 chars.
4. If `count < instincts.min_candidates` → leave the watermark untouched (sparse corrections accumulate across turns until they reach the threshold), release lock, exit 0. Safety valve: if the unmined backlog (`new_offset - start_offset`) exceeds 2 MB, advance the watermark without mining and log `watermark advanced without mining (backlog > 2MB, candidates=N)`.
5. Otherwise spawn, detached (`nohup … &`, stdout/stderr → `miner.log`):
   ```
   claude -p --model <instincts.model> --max-turns 1 --tools "" --strict-mcp-config \
     --append-system-prompt "$(cat team/agents/instinct-observer.md)" \
     < candidates.json | scripts/instincts/instinct.py ingest
   ```
   `--tools ""` disables every built-in tool so no Pre/PostToolUse hooks (including `observe.sh`) fire inside the miner; `--strict-mcp-config` ignores the user's MCP servers; `--max-turns 1` because the miner only has to answer once. The observer prompt instructs the model to output **only** a JSON array of instinct objects (schema below). A wrapper (`scripts/instincts/instinct.py ingest`) validates each object and writes/merges YAML files. The model never writes files directly.
6. Advance the watermark (only on spawn, or via the 2 MB safety valve in step 4); the detached miner removes the lock when it finishes (stale after 10 min either way). The Stop hook must return in < 1s regardless of miner duration.

### Stage 3 — Store

**Project tier:** `team/_memory/_learnings/instincts/<id>.yaml` — committed to git.
**User tier:** `~/.claude/instincts/<id>.yaml` — never committed; receives promoted instincts.

```yaml
id: prefer-gh-cli-over-curl          # kebab-case slug, unique per tier
trigger: "when calling the GitHub API"
action: "Use `gh api` instead of curl with a token"
confidence: 0.5                       # 0.3 – 0.9
domain: workflow                      # code-style | testing | git | debugging | workflow | security | tooling
scope: project                        # project | global
status: pending                       # pending | active | rejected
source: session-observation
project_name: MyAgents
evidence:
  - "2026-09-19 session 3f1a: user corrected curl→gh (correction)"
  - "2026-09-19 session 3f1a: 401 from curl resolved by gh api (error_resolution)"
observed_count: 2
first_seen: 2026-09-19
last_seen: 2026-09-19
```

**Confidence rules** (ported from ECC):

| Event | Effect |
|---|---|
| Initial, by `observed_count` | 1–2 → 0.3, 3–5 → 0.5, 6–10 → 0.7, 11+ → 0.85 |
| Confirming observation (ingest merges into existing id) | +0.05 |
| Contradicting observation (observer marks `contradicts: <id>`) | −0.10 |
| Decay | −0.02 per week since `last_seen`, applied at inject time; floor 0.3 |

Merge rule on ingest: same `id` → append evidence, bump `observed_count`, recompute confidence, update `last_seen`. Rejected instincts are never resurrected by ingest; the observer is given the list of rejected ids to avoid re-proposing them.

**Promotion (project → user tier):** `instinct.py promote` scans instincts across projects registered in `~/.claude/instincts/.projects` (path → name, written by inject on each run). An instinct is promoted when an `id` (or a trigger with ≥ 0.8 token-set similarity) is `active` in ≥ 2 projects with mean confidence ≥ 0.8 and domain ∈ {security, workflow, tooling, git}. The promoted copy gets `scope: global`; project copies remain.

**CLI:** `scripts/instincts/instinct.py` (Python 3.8+, stdlib only, following `_bmad/scripts/memlog.py` conventions — atomic writes via tempfile + rename):

| Command | Purpose |
|---|---|
| `status` | counts by status/tier, top active, pending list, last miner run |
| `review` | interactive accept/reject over pending (also `accept <id>`, `reject <id>`, `accept --min-confidence 0.7`) |
| `inject --limit N --min-confidence X --max-chars C` | print the `[instincts]` block (Stage 4) |
| `ingest < instincts.json` | validate + merge miner output |
| `promote` | project → user tier per rules above |
| `prune --ttl-days 30` | delete `pending` older than TTL; delete `rejected` older than 90 days |
| `export` / `import` | JSON bundle for sharing between machines |

### Stage 4 — Inject: `.agents/hooks/instinct-inject.sh` on `SessionStart`

The repo's first `SessionStart` hook. Runs `instinct.py inject` with values from `.agents/config.yaml` and prints to stdout (which Claude Code injects as context):

```
[instincts] 4 active (2 project, 2 global) · 3 pending — /team:instincts review or ask Athena
- when calling the GitHub API → use `gh api` instead of curl (0.75, workflow)
- when a hook must stay silent → never echo to stdout (0.70, tooling)
…
```

Ranking: `confidence × recency` where recency = `max(0.5, 1 − weeks_since_last_seen × 0.05)`; project-scoped instincts get a +0.05 boost. Hard caps: `inject_limit` items, `inject_max_chars` chars. Only `status: active` and `confidence ≥ min_confidence` are eligible. Zero eligible and zero pending → print nothing.

### Oracle integration

- `team/agents/oracle.md`
  - Activation step (after step 12): run `instinct.py status --json`, set `{oracle_pending_instincts}` and `{oracle_active_instincts}`.
  - New rule in `<rules>`: *At pause points, if `{oracle_pending_instincts}` > 0: in `suggest` mode, list up to 5 pending as `id · trigger → action (confidence)` and offer accept/reject/defer; in `auto` mode, run `instinct.py accept --min-confidence {auto_accept_confidence}` and list only the remainder; in `off` mode, stay silent.* Mirrors the existing mode semantics exactly.
  - New menu item `[IN] Instincts — review pending, promote, prune` → loads `oracle-reference/instinct-review.md`.
- `team/agents/oracle-dispatch-map.md`: category `learning` (signals: repeated corrections, "we keep doing this", `[instincts]` pending banner) → `/team:instincts`.
- `team/agents/oracle-reference/instinct-review.md`: JIT prompt — show status, walk pending, apply decisions via CLI, offer promote/prune, report.
- `claude-commands/team/instincts.md`: `/team:instincts [status|review|promote|prune|export|import]` — loader that shells to the CLI and summarizes.
- `CLAUDE.md` "Oracle Awareness" section gains one line: pending instincts are surfaced per mode.

### Configuration — `.agents/config.yaml`

```yaml
instincts:
  enabled: true
  model: haiku                 # miner model
  min_candidates: 3            # prefilter gate before spawning the miner
  inject_limit: 6
  inject_max_chars: 2000
  min_confidence: 0.7          # eligible for injection
  auto_accept_confidence: 0.7  # Oracle auto mode threshold
  decay_per_week: 0.02
  observations_max_mb: 10
  pending_ttl_days: 30
```

Hooks and CLI read this block via a shared `scripts/instincts/config.py` (stdlib YAML-subset parser — the block is flat key/value, no full YAML parser required). This establishes the pattern that `heartbeat.sh` should follow; that fix is out of scope here but noted.

### Supersession of `learnings.xml`

- `team/engine/learnings.xml`: protocols `learnings-search|capture|prune` marked `deprecated` with a pointer to the instinct CLI; file removed in a later release once nothing references it (nothing does today).
- `team/data/discipline/knowledge/learnings.md`: rewritten — "search before building" → `instinct.py status`; "capture after shipping" → automatic via hooks, plus `/team:instincts review`.
- `docs/plans/2026-04-26-learnings-specialists-autodecision.md`: add a header note pointing here.
- `.agents/decisions/2026-09-19-instincts-supersede-learnings.yaml` recorded per the coordination format.

### Multi-agent / worktree behavior

Each worktree has its own `team/_memory/_learnings/` — observations and pending instincts are per-worktree until committed. Accepted project instincts travel with the branch and merge like any file; `id`-named files make conflicts rare and obvious. `claim-check.sh` applies: an agent whose claim doesn't cover `team/_memory/_learnings/instincts/` cannot accept instincts there — the review action should say so rather than fail silently.

### Error handling

| Condition | Behavior |
|---|---|
| Any hook failure | `exit 0`; nothing reaches the user or blocks the tool |
| `python3` missing | capture/mine/inject skip silently |
| `claude` missing | mine logs one line to `miner.log`, exits 0 |
| Miner returns non-JSON / invalid objects | `ingest` drops invalid objects, logs count; valid ones still land |
| Malformed instinct YAML on disk | skipped by inject; listed under "unreadable" in `status` |
| Lock stale (> 10 min) | overwritten with a `miner.log` note |
| Observations file unwritable | capture exits 0 |
| `.agents/config.yaml` missing `instincts:` | defaults above apply |

### Security & privacy

- Observations are gitignored and secret-scrubbed at write time; they never leave the machine except via the miner's stdin to the local `claude` CLI.
- Instincts contain patterns, not code. The observer prompt forbids quoting code, paths outside the repo, or user identity.
- Injected instincts are context, not policy: the `[instincts]` block header says so, matching the "unreviewed context" stance in the memory guidance.
- Nothing with `status: pending` is ever injected or auto-committed.

### Testing

**Bash harnesses** (pattern: `.agents/hooks/test-claim-check.sh`):
- `test-observe.sh`: prompt event → one JSONL line with expected keys; tool event with `exit_code: 1` → `is_error: true`; `API_KEY=abc` in input → `[REDACTED]`; 5KB truncation; rotation when file > threshold; no git root → no write; `.instincts-off` → no write; stdout always empty.
- `test-instinct-mine.sh`: fake `claude` shim on PATH records invocation; below `min_candidates` → no spawn, watermark NOT advanced; accumulates to threshold → spawn once with `--tools ""` and `--strict-mcp-config`, watermark advanced, lock released, hook returns < 1s; stale lock → proceeds; live lock → skips.
- `test-instinct-inject.sh`: seeded instinct dir → expected block, respects limit/min_confidence/max_chars; empty → no output.

**pytest** (`scripts/instincts/tests/`):
- `test_prefilter.py`: fixture JSONL → correction / error_resolution / repetition candidates; watermark honored.
- `test_instinct.py`: confidence table; merge on ingest; contradiction; decay at inject; accept/reject transitions; rejected never resurrected; promotion requires 2 projects + 0.8 + allowed domain; ranking order; atomic write leaves no temp files.
- `test_config.py`: defaults when block absent; parsing of the flat block.

### Files

**New**
- `.agents/hooks/observe.sh`, `instinct-mine.sh`, `instinct-inject.sh` + three `test-*.sh`
- `scripts/instincts/{prefilter.py, instinct.py, config.py}` + `tests/`
- `team/agents/instinct-observer.md`
- `team/agents/oracle-reference/instinct-review.md`
- `claude-commands/team/instincts.md`
- `.agents/decisions/2026-09-19-instincts-supersede-learnings.yaml`
- `team/_memory/_learnings/instincts/.gitkeep`

**Modified**
- `.claude/settings.local.json`, `templates/settings.local.json.template` — three hook entries
- `.gitignore` — `team/_memory/_learnings/observations.jsonl*`, `miner.log`, `.miner.lock`, `.instinct-watermark`
- `.agents/config.yaml` — `instincts:` block
- `team/agents/oracle.md`, `team/agents/oracle-dispatch-map.md`, `CLAUDE.md`
- `team/engine/learnings.xml`, `team/data/discipline/knowledge/learnings.md`, `docs/plans/2026-04-26-learnings-specialists-autodecision.md`
- `scripts/setup.sh` — copy the new command; `docs/ARCHITECTURE.md` — hook table

### Rollback

Remove the three hook entries from `settings.local.json` (or set `instincts.enabled: false`). No other component runs without the hooks. Committed instinct files are inert markdown-ish YAML.

### Open questions

None blocking. Deferred: reading `coordination.*` from config in `heartbeat.sh`; a `Stop`-time session summary that ECC also ships (separate feature).

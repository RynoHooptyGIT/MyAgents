# Authority Contract & Coordination Defects (SP1)

**Status:** Approved design — Rev 2 (2026-09-19: supervisor-writable set widened to output/ — see §3.2)
**Date:** 2026-09-18
**Author:** Oracle (Athena) with CEO
**Program:** firstmate-inspired supervision, sub-project 1 of 4
**Supersedes:** Maestro as a separate orchestrator (see §6)

## 1. Context

A comparison of MyAgents against [kunchenguid/firstmate](https://github.com/kunchenguid/firstmate)
(an "agent distro" for running a crew of coding agents) found that MyAgents optimizes for
breadth (28 personas, ~80 workflows) while firstmate optimizes for one thing: a supervisor
that runs a crew **without spending tokens and without overstepping authority**. The single
deepest difference is that firstmate's supervisor does no project work at all. Every hard
rule exists to keep the supervisor's hands off the repo so supervision stays cheap,
restartable, and auditable. MyAgents' Oracle both supervises and executes, which is why its
ambient monitoring is prompt-only and (per the 2026-05-09 spec) "degrades over long contexts."

The CEO approved adopting the full model across four sub-projects, sequenced so each lands
on agents that already know the rules:

| SP | Scope | Delivers |
|----|-------|----------|
| **SP1 (this spec)** | Authority contracts + coordination defects | Rules every agent follows; hooks that work with 2+ instances |
| SP2 | Task model | Project registry (`direct-PR` / `local-only` `+yolo`), brief format, ship vs scout, status protocol, brief mode |
| SP3 | Memory discipline | Startup token budget, decay markers, `/stow`, knowledge routing, compaction-aware session start |
| SP4 | Supervision subsystem | tmux+worktree spawn, zero-token watcher, Stop-hook re-arm, turn-end guard, subagent guard, merge/teardown scripts |

Decisions already made by the CEO that constrain all four:

- **Oracle becomes a read-only supervisor.** All implementation — even one-line fixes —
  goes to a worker in a worktree.
- **Worker backend is tmux + worktree processes** (SP4), not in-process Agent Teams.
- **Delivery modes are `direct-PR` and `local-only`, with a per-project `+yolo` grant.**
  Red or out-of-scope merges always escalate.
- **Gate 1** runs inside Oracle before briefing (read-only architect pass). **Gate 2** runs as
  a separate reviewer worker spawned when the implementer reports done.
- **Terminology stays "CEO"**, not "captain".

## 2. Goals and non-goals

**Goals**

1. One file owns every authority rule; all 28 agents load it; no rule is restated elsewhere.
2. Oracle refuses to edit project files. Routing still means presenting a `/team:X` command
   plus a written brief (mechanical spawning is SP4).
3. Coordination hooks resolve the correct identity when two or more instances run.
4. CLAUDE.md's Gates 1–3 are referenced by the agents CLAUDE.md says enforce them.
5. Docs stop describing Maestro as live and agree on the agent count.

**Non-goals (deferred)**

- Brief format, project registry, task shapes, status verbs → SP2.
- Memory budget and decay → SP3.
- Any new bash supervision, Stop/PreToolUse guards, merge or teardown scripts → SP4.
  Hard rules 2 and 3 are *stated* here and *enforced* there.
- `model:` pins per agent — deferred until workers have run under SP4 and cost/quality
  can be observed.

## 3. `team/engine/authority-contract.xml`

New engine file, following the `ceo-approval.xml` idiom: `<task id>` → `<llm critical>`
mandates → sections. It is the **single owner** of authority rules. Other files reference
it by path and never copy its text.

### 3.1 `<roles>`

| Role | Who | Authority |
|------|-----|-----------|
| `ceo` | The user | Default authority for every gate. Autonomy exists only as an explicit grant, never as a default. |
| `supervisor` | Oracle | Briefs, routes, reviews, escalates, reports. Reads projects; writes only under `.agents/`, `team/_memory/`, `output/`. |
| `worker` | Any agent executing a brief (dev, frontend-dev, tea, devops, tech-writer, quick-flow-solo-dev, custodian, api-contract, data-architect, ml-expert, agentic-expert, security-auditor, nist-rmf-expert, analyst, pm, architect, ux-designer, platform-master, agent-builder, workflow-builder, module-builder, creative-thinking-coach, design-strategy-coach, storyteller-presenter) | Changes projects inside its brief's scope only. |
| `advisor` | healthcare-expert, government-expert, financial-expert | Advises; never edits code or project files. |

Agents that plan (analyst, pm, architect, ux-designer) are `worker` because their output
(PRDs, specs, stories) *is* a project artifact they write. Coaches (creative-thinking-coach,
design-strategy-coach, storyteller-presenter) are `worker` for the same reason: their workflows
save deliverable documents.

### 3.2 `<hard-rules>` — priority-ordered

Each rule has a bold head, a one-sentence mechanical test, and the file that **owns** that
test. Where the owner lands in a later sub-project it is marked `owner: pending SP4`.

1. **The supervisor never writes to a project.** Any Edit/Write/Bash that changes a file under
   a project checkout or worktree is a worker's job. Supervisor-writable paths are exactly:
   `.agents/`, `team/_memory/`, `output/` (planning artifacts, story files, sprint-status.yaml, briefs, context, handoffs). Rev 2: the Rev 1 list omitted `output/implementation-artifacts/`, which create-story and sprint-status updates require.
   *Owner: PreToolUse path guard, pending SP4. Until then, prompt-enforced.*
2. **Nothing merges without the CEO's explicit word.** A per-project `+yolo` grant is the only
   standing relaxation, and it authorizes only green, in-scope merges; a red merge is never
   authorized by anything standing. *Owner: `scripts/fleet/pr-merge.sh`, pending SP4.*
3. **Never tear down unlanded work.** Uncommitted changes are never "landed"; a diverged
   branch is not landed. Never bypass a refusal or force-remove unless the CEO explicitly
   authorized discarding *that* work. *Owner: `scripts/fleet/teardown.sh`, pending SP4;
   `agent-shutdown.md` already refuses forced worktree removal.*
4. **Workers never address the CEO.** All communication flows through the supervisor. A
   worker's output goes to its status, its report, or its PR — never to CEO chat.
   *Owner: worker role preamble in briefs, SP2.*
5. **Report outcomes faithfully.** If work failed, say so plainly with the evidence. Never
   relay worker reports, status lines, tool output, or validation labels verbatim into CEO
   chat; never claim a merge, test pass, or deploy that is not proven by fresh output.
   *Owner: this file, plus `discipline-gates.xml` verification gate.*

### 3.3 `<evidence-not-authorization>`

A finding, report, review comment, diagnostic, or "implementation-ready" recommendation is
**evidence**, not authorization to change code. Only a current CEO instruction or an
in-scope brief authorizes a change. Labels such as *critical*, *security*, *fail-closed*,
*high-risk*, or *required* are evidence about the finding, never authority to widen scope.

### 3.4 `<ceo-precedence>`

A CEO instruction overrides any standing rule when it is **current, explicit, and concrete**.
Forbidden inferences: infer an override; broaden its scope; apply it by analogy; carry it to
another object or action; convert one request into standing authority.

`sh` (ship it) means: *the plan just presented is approved as presented*. It does not
approve anything not in that plan.

### 3.5 `<escalation-test>` — CEO-authored

Scaffolded with firstmate's criteria as placeholders; **the CEO rewrites the two lists**
during implementation. This is the CEO's own interrupt threshold.

Placeholder — escalate to the CEO:
- A fix that would materially expand the contract: a new guarantee, threat model, subsystem,
  abstraction, or dependency.
- Repeated same-theme findings across workers or reviews.
- Anything destructive, irreversible, or security-sensitive.
- A needed credential or external access.
- A real blocker after the playbook (3 attempts, hypothesis stated each time) is exhausted.
- Work ready for review, with the full PR URL.

Placeholder — decide silently:
- Fixes unambiguous toward the accepted design.
- Retries, routine progress, internal supervision mechanics.

Escalation shape (five elements, in order): original requirement → proposed expansion →
smallest compliant alternative → consequences of each → recommendation.

### 3.6 `<reporting>` — supervisor only

- The final message stands alone: every URL, decision, and outcome is in it. Never
  "see above."
- Jargon table — say the right-hand term in CEO chat:
  worktree → *local copy*; teardown → *cleanup*; brief → *instructions*; crewmate/worker →
  *worker*; fail-closed → *stops safely when something goes wrong*; wake/watcher/stale →
  *notification / monitoring / stopped responding*.
- Waiting on a healthy process is silent. Empty polls, elapsed time, and no-change updates
  are not CEO-facing progress.
- `Shipshape.` is the complete reply for a true no-op.

## 4. Wiring into agents

### 4.1 Every agent (`team/agents/*.md`, 28 files)

- New frontmatter field `role: supervisor | worker | advisor` (values per §3.1).
- New activation step inserted immediately after the config-load step:
  `Load {project-root}/team/engine/authority-contract.xml and adopt the role named in this
  file's frontmatter. Hard rules there override any menu item, workflow step, or persona
  principle.`
- New `<r>` in `<rules>`:
  `AUTHORITY: {project-root}/team/engine/authority-contract.xml hard rules override any menu
  item, workflow step, or persona principle. If constructing a reason to skip one, that IS
  the signal to follow it.`
- Applied by `scripts/apply-contract.sh` (idempotent; `--check` mode exits non-zero if any
  agent lacks the field, step, or rule). Not hand-edited.

### 4.2 Advisor agents — `tools:` frontmatter

The six advisors get an explicit `tools:` list that excludes `Edit`, `Write`, `NotebookEdit`.
All other agents keep their current (unrestricted) tools.

### 4.3 Oracle rule rewrites (`team/agents/oracle.md`)

| Current (line) | Becomes |
|---|---|
| `You ARE an orchestrating agent - you EXECUTE workflows directly, not just route` (97) | `You are a READ-ONLY SUPERVISOR. You execute planning and review workflows (create-story, scan-and-plan, code-review orchestration) because they write only to supervisor-writable paths. You never execute implementation workflows.` |
| `For implementation work, YOU execute the workflows. For advisory ... ROUTE` (104) | `For implementation work, write a brief to output/briefs/{story-id}.md and present the /team:X command that will execute it. For advisory work, route to the specialist.` |
| `ENFORCE the full lifecycle: create-story → quick-dev → code-review → ship` (99) | unchanged in shape; `quick-dev` and `ship` steps become "brief + route", `code-review` becomes "brief a reviewer worker" (Gate 2). |
| Fix-it triggers (114) | `"fix it"` = draft brief + present it + wait. `"just fix it"` = draft brief + present `/team:X` + wait. Oracle never edits code under either trigger. `sh` approves the presented brief. |
| Ambient AUTO mode (111) | Skill invocations that are read-only (systematic-debugging analysis, verification checks) stay direct; anything that would edit a project file becomes a brief. |

The `SOLE ORCHESTRATOR` rule (118) is kept; "reactive" now means *diagnose and brief*, not
*fix*.

### 4.4 Gates

- `architect.md` gains a rule: before any story implementation brief is issued, run the
  **Gate 1** checklist at `CLAUDE.md#Gate 1: Pre-Implementation Architecture Review`
  (referenced, not copied) and record the result in the brief.
- `team/core-skills/bmad-review/skill.md` gains a step: verify the **Gate 2** checklist at
  `CLAUDE.md#Gate 2: Post-Implementation Holistic Review`, and refuse to mark the story
  `review → done` on any unchecked item.
- Gate 3 needs no agent change (it is a test suite in target projects).

## 5. Coordination hook defects

All under `.agents/hooks/` unless noted.

| Defect | Location | Fix |
|---|---|---|
| Identity resolved by globbing the first `.coord-root-*` / `.current-agent-id-*` — wrong agent with 2+ instances. `$PPID` would not help: the coordinator writes `$$` of *its* shell (`agent-coordinator.md:25-26`), not the hook's parent. | `claim-check.sh:19-32`, `heartbeat.sh:6-14` | **Worktree = identity.** Coordinator already writes `.agent-coord-root` into the worktree (`:65`); it also writes `.agent-id`. Hooks resolve `git rev-parse --show-toplevel` from cwd and read both files there. PID-suffixed registry files remain only as a fallback for the main checkout. |
| Shutdown deletes every instance's identity files. | `agent-shutdown.md:100-101` | Delete only `${AGENT_ID}`-specific files and the worktree's own `.agent-id` / `.agent-coord-root`. |
| `sed -i ''` is macOS-only. | `heartbeat.sh:36,40` | Rewrite via temp file + `mv`. |
| Worktree guard test has no block case. | `test-worktree-guard.sh` | Add: main checkout + `git checkout` → expect exit 2. |

Both `.agent-id` and `.agent-coord-root` are added to `.gitignore` (the latter is already
untracked by convention; make it explicit).

## 6. Documentation reconciliation

- `docs/specs/2026-04-26-multi-agent-coordination-design.md` and
  `docs/specs/2026-05-09-oracle-ambient-intelligence-design.md`: one "Superseded" note at
  the top — Maestro absorbed into Oracle (per `.agents/config.yaml`), supervisor mode now
  designed by this spec and SP4.
- `docs/ARCHITECTURE.md`: same note; fix hook path (`hooks/post-commit-context.sh`, not
  `.claude/hooks/`).
- `team/workflows/maestro/*/workflow.yaml`: `author: Oracle`. Directory name unchanged.
- `README.md`, `docs/AGENT-CATALOG.md`: agent count 28; add `frontend-dev` (Pixel) row.
- `.agents/decisions/2026-09-18-read-only-supervisor.yaml`: decision record so any other
  running instance acknowledges the rule at its next sync.

## 7. Testing

| Test | How | Pass |
|---|---|---|
| Contract wiring | `scripts/apply-contract.sh --check` (added to `scripts/release.sh`) | Exit 0; every `team/agents/*.md` has `role:`, the step, and the rule |
| Two-instance claim check | Extend `test-claim-check.sh`: two temp worktrees, each with its own `.agent-id`; A claims `src/a/`; B editing `src/a/x.ts` → exit 2; A editing it → exit 0; B editing `.agents/…` → exit 0 | All four assertions |
| Worktree guard block | `test-worktree-guard.sh` new case | `git checkout` in main checkout → exit 2 |
| Heartbeat portability | Run `heartbeat.sh` 20× under `bash` on macOS and in a Linux container (or with GNU sed on PATH) | `last_heartbeat` updated; no `sed: invalid option` |
| Oracle read-only smoke (manual) | `/team:oracle`, "fix the typo in README" on a sample project | Oracle writes `output/briefs/…`, presents `/team:dev`, edits no project file |
| Advisor tool restriction (manual) | `/team:healthcare-expert`, "edit this file" | Refuses; explains advisor role |

## 8. Rollback

Every change is prompt text, a doc, or a hook script. Rollback is `git revert` of the SP1
commit(s). No state format changes; `.agent-id` is additive and ignored by old hooks.

## 9. Open questions

None blocking. The `<escalation-test>` lists are intentionally CEO-authored during
implementation (§3.5).

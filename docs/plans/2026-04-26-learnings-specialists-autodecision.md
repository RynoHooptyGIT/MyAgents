# Learnings, Specialist Dispatch, and Principled Auto-Decision Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three capabilities adapted from gstack: (1) cross-session project learnings system, (2) parallel specialist dispatch during code review, (3) principled auto-decision engine replacing naive YOLO mode.

**Architecture:** All three features integrate into the existing engine/discipline/workflow architecture. Learnings uses JSONL files in `team/_memory/_learnings/`. Specialist dispatch adds a new step to the code-review workflow that invokes domain agents as parallel subagents. Auto-decision replaces the YOLO mode in `workflow.xml` with a 6-principle decision engine that classifies decisions as mechanical/taste/user-challenge.

**Tech Stack:** XML (engine tasks), Markdown (discipline knowledge), CSV (discipline index), YAML (workflow config)

---

## Chunk 1: Project Learnings System

### Task 1: Create Learnings Engine Task

**Files:**
- Create: `team/engine/learnings.xml`

This is the reusable task that workflows invoke to capture and search learnings.

- [ ] **Step 1: Create `team/engine/learnings.xml`**

```xml
<task id="team/engine/learnings.xml" name="Project Learnings">
  <objective>Capture, search, and manage cross-session project learnings</objective>

  <llm critical="true">
    <mandate>Learnings persist across sessions in JSONL format</mandate>
    <mandate>Always search before building — check if this pattern was seen before</mandate>
    <mandate>Each learning entry has: key, type, insight, files, source, ts</mandate>
  </llm>

  <protocol name="learnings-search" desc="Search project learnings for relevant context">
    <action>Determine the learnings file path: {project-root}/team/_memory/_learnings/learnings.jsonl</action>
    <check if="learnings file exists">
      <action>Read the learnings file</action>
      <action>Search entries by relevance to the current task context:
        - Match against file paths being modified
        - Match against technology/framework keywords
        - Match against the current workflow type (code-review, dev-story, etc.)
      </action>
      <action>Return the top 5 most relevant entries (by recency + relevance)</action>
      <check if="relevant learnings found">
        <output>**Prior Learnings (relevant to this task):**
          {{#each learning}}
          - **{{key}}** ({{type}}): {{insight}} — _from {{source}}, {{ts}}_
          {{/each}}
        </output>
      </check>
      <check if="no relevant learnings">
        <action>Continue silently — no learnings to surface</action>
      </check>
    </check>
    <check if="learnings file does not exist">
      <action>Continue silently — no learnings yet</action>
    </check>
  </protocol>

  <protocol name="learnings-capture" desc="Record a learning from the current workflow">
    <action>Determine the learnings file path: {project-root}/team/_memory/_learnings/learnings.jsonl</action>
    <action>Create {project-root}/team/_memory/_learnings/ directory if it does not exist</action>
    <action>Construct learning entry as JSON:
      {
        "key": "{{short-kebab-case-key}}",
        "type": "{{pattern|pitfall|decision|architecture}}",
        "insight": "{{one-line description of what was learned}}",
        "files": ["{{list of relevant file paths}}"],
        "source": "{{workflow that captured this: code-review, dev-story, etc.}}",
        "ts": "{{current ISO timestamp}}"
      }
    </action>
    <action>Append the JSON entry as a single line to the learnings JSONL file</action>
  </protocol>

  <protocol name="learnings-prune" desc="Check learnings for staleness">
    <action>Read all entries from the learnings JSONL file</action>
    <action>For each entry with a "files" field:
      - Check if those files still exist in the project
      - If ALL referenced files are deleted, mark as STALE
    </action>
    <action>For entries with the same "key":
      - If insights contradict, mark as CONFLICT
      - The most recent entry wins (latest timestamp)
    </action>
    <action>Report stale and conflicting entries for user decision</action>
  </protocol>
</task>
```

- [ ] **Step 2: Commit**

```bash
git add team/engine/learnings.xml
git commit -m "Add learnings engine task — capture, search, and prune protocols"
```

---

### Task 2: Create Learnings Discipline Knowledge File

**Files:**
- Create: `team/data/discipline/knowledge/learnings.md`

- [ ] **Step 1: Create `team/data/discipline/knowledge/learnings.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add team/data/discipline/knowledge/learnings.md
git commit -m "Add learnings discipline — search before building, capture after shipping"
```

---

### Task 3: Update Discipline Index

**Files:**
- Modify: `team/data/discipline/discipline-index.csv`

- [ ] **Step 1: Append learnings row to `discipline-index.csv`**

Add this line at the end of the file:

```
learnings,Learnings Discipline,"Search learnings before building — capture learnings after shipping","learnings,memory,patterns,pitfalls,all",knowledge/learnings.md
```

- [ ] **Step 2: Commit**

```bash
git add team/data/discipline/discipline-index.csv
git commit -m "Register learnings discipline in discipline index"
```

---

### Task 4: Integrate Learnings into Workflow Engine

**Files:**
- Modify: `team/engine/workflow.xml` — add learnings search at init and capture at completion

- [ ] **Step 1: Add learnings search to Step 1 (after substep 1b)**

In `team/engine/workflow.xml`, after the closing `</substep>` of substep 1b (line 36) and before substep 1c (line 38), insert a new substep:

```xml
      <substep n="1b.1" title="Search Project Learnings">
        <action>If {project-root}/team/engine/learnings.xml exists, invoke the learnings-search protocol</action>
        <action>Pass context: workflow name, input file patterns, any story/epic identifiers</action>
        <action>If relevant learnings found, display them to the user before proceeding</action>
        <note>This surfaces prior patterns and pitfalls before work begins</note>
      </substep>
```

- [ ] **Step 2: Add learnings capture to Step 3 (completion)**

In `team/engine/workflow.xml`, in step 3 (line 111-114), before the closing `</step>`, insert:

```xml
      <substep n="3a" title="Capture Learnings" optional="true">
        <check if="workflow produced review findings, debugging insights, or architectural decisions">
          <action>If {project-root}/team/engine/learnings.xml exists, invoke the learnings-capture protocol</action>
          <action>Capture any patterns, pitfalls, decisions, or architecture insights discovered during this workflow</action>
        </check>
      </substep>
```

- [ ] **Step 3: Commit**

```bash
git add team/engine/workflow.xml
git commit -m "Integrate learnings search at workflow init and capture at completion"
```

---

### Task 5: Integrate Learnings into Code Review Workflow

**Files:**
- Modify: `team/workflows/implementation/code-review/instructions.xml`

- [ ] **Step 1: Add learnings search after step 1 discovery**

In `instructions.xml`, after line 44 (`</step>` closing step 1) and before step 2 (line 46), insert:

```xml
  <step n="1b" goal="Search prior learnings for relevant context">
    <action>Check if {project-root}/team/engine/learnings.xml exists</action>
    <check if="learnings engine exists">
      <action>Search learnings for entries matching:
        - File paths in the story's File List
        - Technology keywords from the story's technical requirements
        - Prior code-review findings on the same files
      </action>
      <check if="relevant learnings found">
        <output>**Prior Learnings (relevant to this review):**
          Review these before proceeding — they may reveal known patterns or recurring issues.
        </output>
        <action>Add relevant learnings to the review context for Layer 1-3 analysis</action>
      </check>
    </check>
  </step>
```

- [ ] **Step 2: Add learnings capture after step 4 (findings fixed)**

In `instructions.xml`, after step 4's closing `</step>` (line 203) and before step 5 (line 205), insert:

```xml
  <step n="4b" goal="Capture review learnings">
    <check if="{project-root}/team/engine/learnings.xml exists">
      <action>Review all findings from this code review session</action>
      <action>For each finding that reveals a reusable pattern or non-obvious pitfall:
        - Capture as a learning with type "pattern" or "pitfall"
        - Include the affected file paths
        - Set source to "code-review"
      </action>
      <action>If the same files have had findings in prior reviews (check learnings), capture an "architecture" learning noting the recurring issue</action>
    </check>
  </step>
```

- [ ] **Step 3: Commit**

```bash
git add team/workflows/implementation/code-review/instructions.xml
git commit -m "Add learnings search and capture to code review workflow"
```

---

## Chunk 2: Parallel Specialist Dispatch in Code Review

### Task 6: Create Specialist Review Dispatch Engine Task

**Files:**
- Create: `team/engine/specialist-review-dispatch.xml`

- [ ] **Step 1: Create `team/engine/specialist-review-dispatch.xml`**

```xml
<task id="team/engine/specialist-review-dispatch.xml" name="Specialist Review Dispatch">
  <objective>Detect which specialist domain reviews are relevant to the current code changes,
    dispatch them as parallel subagents, and aggregate findings into the main review triage</objective>

  <llm critical="true">
    <mandate>Dispatch specialists ONLY for domains touched by the diff</mandate>
    <mandate>Each specialist runs independently — do not serialize</mandate>
    <mandate>Aggregate all specialist findings into the main triage pipeline</mandate>
  </llm>

  <flow>
    <step n="1" title="Detect Relevant Specialists">
      <action>Analyze the diff and story context to determine which specialists to invoke</action>
      <action>Apply these detection rules:

        **Security (Shield)** — INVOKE IF any of:
        - Authentication/authorization code modified (auth, session, token, password, login)
        - Data access patterns changed (queries, RLS, tenant isolation)
        - API endpoints added or modified
        - Environment variables or secrets handling changed
        - Dependency versions changed

        **API Contract (Pact)** — INVOKE IF any of:
        - Router/endpoint files modified
        - Request/response schemas changed
        - API middleware modified
        - Frontend service files that call backend APIs modified

        **Test Quality (Murat)** — ALWAYS INVOKE:
        - Assess test coverage for all changed code
        - Verify test assertions are meaningful (not placeholders)
        - Check for missing edge case tests

        **Performance** — INVOKE IF any of:
        - Database queries added or modified
        - Loop structures over collections
        - Caching logic changed
        - File I/O or network calls added
        - Data serialization/deserialization changed
      </action>

      <action>Record the list of specialists to invoke with their rationale</action>
      <output>**Specialist Reviews:** Dispatching {{specialist_count}} specialist(s): {{specialist_list}}</output>
    </step>

    <step n="2" title="Dispatch Parallel Specialist Reviews">
      <action>For each selected specialist, dispatch a subagent with this context:
        1. The git diff (same diff used by Layer 1-3)
        2. The story file summary (ACs, tasks, file list)
        3. The specialist's domain checklist (see below)
        4. Instruction: "Produce findings in format: {source, title, detail, location, severity}"
      </action>

      <specialist name="Security (Shield)">
        <checklist>
          - Injection risks (SQL, command, XSS, path traversal)
          - Authentication bypass or weakening
          - Authorization gaps (missing role checks, broken access control)
          - Tenant isolation violations (missing tenant_id filtering, RLS gaps)
          - Secrets exposure (hardcoded keys, tokens in logs, debug endpoints)
          - OWASP Top 10 relevance assessment
          - Input validation completeness
        </checklist>
      </specialist>

      <specialist name="API Contract (Pact)">
        <checklist>
          - Endpoint signature changes (path, method, params, body schema)
          - Response format changes (added/removed/renamed fields)
          - Breaking vs non-breaking change classification
          - Frontend/backend alignment (do callers match the new contract?)
          - Error response format consistency
          - OpenAPI spec drift (if spec exists)
        </checklist>
      </specialist>

      <specialist name="Test Quality (Murat)">
        <checklist>
          - Test coverage: every changed function has at least one test
          - Assertion quality: tests assert specific outcomes (not just "no error")
          - Edge cases: boundary values, empty inputs, null handling tested
          - Integration points: API calls, DB queries, external services mocked appropriately
          - Test isolation: no shared state between tests, no order dependencies
          - Regression: prior bug fixes have regression tests
        </checklist>
      </specialist>

      <specialist name="Performance">
        <checklist>
          - N+1 query detection (loops with DB calls)
          - Unbounded data fetches (missing LIMIT, pagination)
          - Missing indexes for new query patterns
          - Inefficient string/collection operations in hot paths
          - Cache invalidation correctness
          - Memory allocation patterns (large objects in loops)
        </checklist>
      </specialist>

      <action>Wait for all dispatched specialists to complete</action>
    </step>

    <step n="3" title="Aggregate Specialist Findings">
      <action>Collect all findings from all specialists</action>
      <action>Normalize to common format: {source: "specialist-name", title, detail, location, severity}</action>
      <action>Deduplicate against existing Layer 1-3 findings:
        - If a specialist found the same issue as a layer, merge (note both sources)
        - If a specialist found a NEW issue, add to the findings list
      </action>
      <action>Return the aggregated specialist findings for inclusion in the main triage</action>
    </step>
  </flow>
</task>
```

- [ ] **Step 2: Commit**

```bash
git add team/engine/specialist-review-dispatch.xml
git commit -m "Add specialist review dispatch engine — parallel domain expert reviews"
```

---

### Task 7: Wire Specialist Dispatch into Code Review Workflow

**Files:**
- Modify: `team/workflows/implementation/code-review/instructions.xml`

- [ ] **Step 1: Add specialist dispatch step after Layer 1-3 review**

In `instructions.xml`, after the TRIAGE action block (line 126) and before the minimum issue gate check (line 128), insert:

```xml
    <!-- ═══════════════════════════════════════════════════ -->
    <!-- SPECIALIST REVIEW: Parallel domain expert dispatch  -->
    <!-- ═══════════════════════════════════════════════════ -->
    <check if="{project-root}/team/engine/specialist-review-dispatch.xml exists">
      <action>Load and execute the specialist review dispatch task</action>
      <action>Pass context: the diff, story file summary, and all Layer 1-3 findings so far</action>
      <action>Merge specialist findings into the TRIAGE results:
        - Specialist findings follow the same NORMALIZE → DEDUPLICATE → CLASSIFY pipeline
        - New specialist findings are added with their specialist source noted
        - Duplicate findings get "confirmed by specialist" annotation (increases confidence)
      </action>
    </check>
```

- [ ] **Step 2: Commit**

```bash
git add team/workflows/implementation/code-review/instructions.xml
git commit -m "Wire specialist dispatch into code review after Layer 1-3 triage"
```

---

## Chunk 3: Principled Auto-Decision (Enhanced YOLO)

### Task 8: Create Auto-Decision Discipline Knowledge File

**Files:**
- Create: `team/data/discipline/knowledge/auto-decision.md`

- [ ] **Step 1: Create `team/data/discipline/knowledge/auto-decision.md`**

```markdown
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
- **Handling:** Always ask via `<ask>` tag. Frame as: "What you said → What I recommend → Why → Cost if I'm wrong"

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
```

- [ ] **Step 2: Commit**

```bash
git add team/data/discipline/knowledge/auto-decision.md
git commit -m "Add auto-decision discipline — 6 principles for principled YOLO mode"
```

---

### Task 9: Update Discipline Index for Auto-Decision

**Files:**
- Modify: `team/data/discipline/discipline-index.csv`

- [ ] **Step 1: Append auto-decision row to `discipline-index.csv`**

Add this line at the end of the file:

```
auto-decision,Auto-Decision Discipline,"6 principles for principled auto-decisions in YOLO mode — mechanical/taste/user-challenge classification","yolo,auto-decision,principles,workflow,all",knowledge/auto-decision.md
```

- [ ] **Step 2: Commit**

```bash
git add team/data/discipline/discipline-index.csv
git commit -m "Register auto-decision discipline in discipline index"
```

---

### Task 10: Enhance Workflow Engine YOLO Mode

**Files:**
- Modify: `team/engine/workflow.xml` — replace naive YOLO with principled auto-decision

- [ ] **Step 1: Replace the YOLO execution mode definition**

In `team/engine/workflow.xml`, replace lines 117-121 (the `<execution-modes>` block) with:

```xml
  <execution-modes>
    <mode name="normal">Full user interaction and confirmation of EVERY step at EVERY template output - NO EXCEPTIONS except yolo MODE</mode>
    <mode name="yolo" desc="Principled Auto-Decision Mode">
      <mandate>Load {project-root}/team/data/discipline/knowledge/auto-decision.md on activation</mandate>
      <mandate>Apply the 6 Decision Principles to every intermediate question</mandate>
      <mandate>Classify every auto-decision as: mechanical, taste, or user-challenge</mandate>
      <rules>
        <rule>Mechanical decisions: auto-decide silently, do not ask user</rule>
        <rule>Taste decisions: auto-decide using principles, record decision + alternative for final gate</rule>
        <rule>User Challenge decisions: ALWAYS ask the user, even in YOLO mode — frame as recommendation</rule>
        <rule>Optional steps: apply principles to decide include/skip (do not blindly skip all)</rule>
        <rule>Template-output: generate content and continue without confirmation</rule>
        <rule>Ask tags: classify the question, then auto-decide or ask based on classification</rule>
      </rules>
      <final-gate>
        <mandate>At workflow completion, present ALL taste decisions in a single summary</mandate>
        <mandate>Wait for user confirmation — user can override any taste decision</mandate>
        <mandate>Only then mark workflow as complete</mandate>
      </final-gate>
    </mode>
  </execution-modes>
```

- [ ] **Step 2: Update substep 2a to use principled decision for optional steps**

In `team/engine/workflow.xml`, replace lines 57-62 (substep 2a) with:

```xml
      <substep n="2a" title="Handle Step Attributes">
        <check>If optional="true" and NOT #yolo → Ask user to include</check>
        <check>If optional="true" and #yolo → Apply auto-decision principles:
          - Does this step add completeness or coverage? (P1) → Include
          - Is this step cosmetic or low-value for the current phase? → Skip
          - Classify as mechanical (auto-decide) or taste (record for final gate)
        </check>
        <check>If if="condition" → Evaluate condition</check>
        <check>If for-each="item" → Repeat step for each item</check>
        <check>If repeat="n" → Repeat step n times</check>
      </substep>
```

- [ ] **Step 3: Update substep 2b to handle ask tags in YOLO mode**

In `team/engine/workflow.xml`, after the existing execute-tags block in substep 2b (line 78), add before the closing `</substep>`:

```xml
          <tag>ask xml tag in #yolo mode → Classify the question using auto-decision discipline:
            - MECHANICAL: Auto-answer using the 6 principles, continue silently
            - TASTE: Auto-answer using principles, record {question, chosen_answer, alternative, reasoning} in taste_decisions list
            - USER_CHALLENGE: Present to user with recommendation framing, WAIT for response
          </tag>
```

- [ ] **Step 4: Update substep 2c to skip confirmation in YOLO but still generate content**

In `team/engine/workflow.xml`, replace lines 81-103 (substep 2c) with:

```xml
      <substep n="2c" title="Handle template-output Tags">
        <if tag="template-output">
          <mandate>Generate content for this section</mandate>
          <mandate>Save to file (Write first time, Edit subsequent)</mandate>
          <action>Display generated content</action>
          <check if="NOT #yolo">
            <ask> [a] Advanced Elicitation, [c] Continue, [p] Party-Mode, [y] YOLO the rest of this document only. WAIT for response. <if
                response="a">
                <action>Start the advanced elicitation workflow {project-root}/team/workflows/advanced-elicitation/workflow.xml</action>
              </if>
              <if
                response="c">
                <action>Continue to next step</action>
              </if>
              <if response="p">
                <action>Start the party-mode workflow {project-root}/team/workflows/party-mode/workflow.yaml</action>
              </if>
              <if
                response="y">
                <action>Load auto-decision discipline: {project-root}/team/data/discipline/knowledge/auto-decision.md</action>
                <action>Initialize taste_decisions list as empty</action>
                <action>Enter #yolo mode for the rest of the workflow</action>
              </if>
            </ask>
          </check>
          <check if="#yolo">
            <action>Content generated and saved — continue to next step (no confirmation needed)</action>
          </check>
        </if>
      </substep>
```

- [ ] **Step 5: Add final approval gate to Step 3 (completion)**

In `team/engine/workflow.xml`, in step 3 (completion), after the learnings capture substep and before the closing `</step>`, insert:

```xml
      <substep n="3b" title="YOLO Final Approval Gate" if="#yolo">
        <check if="taste_decisions list is not empty">
          <output>**Auto-Decision Summary (YOLO Mode)**

            **Mechanical decisions:** {{mechanical_count}} (auto-decided silently)

            **Taste decisions requiring your review:**
            {{#each taste_decision}}
            {{@index}}. **{{question}}**: Chose "{{chosen_answer}}" because {{reasoning}}.
               Alternative: "{{alternative}}"
            {{/each}}

            **Accept all? Or specify which to change:**
          </output>
          <ask>Accept all taste decisions? (yes / specify numbers to change)</ask>
          <check if="user wants changes">
            <action>Apply user's overrides to the specified taste decisions</action>
            <action>Re-execute affected sections with the user's choice</action>
          </check>
        </check>
        <check if="taste_decisions list is empty">
          <output>**YOLO Mode Complete** — All {{mechanical_count}} decisions were mechanical (unambiguous). No taste decisions to review.</output>
        </check>
      </substep>
```

- [ ] **Step 6: Update substep 2d for YOLO step completion**

In `team/engine/workflow.xml`, replace lines 105-108 (substep 2d) with:

```xml
      <substep n="2d" title="Step Completion">
        <check>If no special tags and NOT #yolo:</check>
        <ask>Continue to next step? (y/n/edit)</ask>
        <check>If no special tags and #yolo:</check>
        <action>Continue to next step automatically</action>
      </substep>
```

- [ ] **Step 7: Commit**

```bash
git add team/engine/workflow.xml
git commit -m "Replace naive YOLO with principled auto-decision engine

YOLO mode now applies 6 decision principles (completeness, boil lakes,
pragmatic, DRY, explicit over clever, bias toward action) and classifies
every decision as mechanical/taste/user-challenge. Mechanical decisions
auto-decide silently. Taste decisions auto-decide but surface at a final
approval gate. User challenges always ask, even in YOLO mode."
```

---

## Final Commit: Version Bump

- [ ] **Step 1: Bump VERSION**

Update `VERSION` from `7.1.0` to `7.2.0`.

- [ ] **Step 2: Final commit and push**

```bash
git add VERSION
git commit -m "chore(release): v7.2.0 — learnings system, specialist dispatch, principled YOLO"
git push
```

---

## Verification

After all tasks are complete, verify:

1. `team/engine/learnings.xml` exists with search, capture, and prune protocols
2. `team/engine/specialist-review-dispatch.xml` exists with detection rules and specialist checklists
3. `team/data/discipline/knowledge/learnings.md` exists with Iron Law, types, and enforcement
4. `team/data/discipline/knowledge/auto-decision.md` exists with 6 principles, classification, and final gate
5. `team/data/discipline/discipline-index.csv` has 11 entries (9 original + learnings + auto-decision)
6. `team/engine/workflow.xml` has learnings integration at init/completion and enhanced YOLO mode
7. `team/workflows/implementation/code-review/instructions.xml` has learnings search/capture and specialist dispatch
8. `bash -n` passes on all .sh scripts (no syntax errors introduced)

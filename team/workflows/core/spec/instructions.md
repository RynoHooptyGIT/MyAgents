# BMad Spec — Intent Distillation

<critical>The workflow execution engine is governed by: {project-root}/team/engine/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {project-root}/team/workflows/core/spec/workflow.yaml</critical>
<critical>Communicate all responses in {communication_language} and language MUST be tailored to {user_skill_level}</critical>
<critical>Generate all documents in {document_output_language}</critical>

<critical>
GOAL: Transform any intent input — vague idea, brain dump, PRD, brief, transcript, customer email, multi-source — into a tight five-field kernel (SPEC.md) that any downstream skill can consume.

OUTPUT LOCATION: `{spec_output_path}/spec-{slug}/SPEC.md` where `{slug}` is derived from the subject (not the input type).
  - If input already has a slug (e.g., prd-foo-bar), inherit it.
  - Otherwise agree on a slug with the user interactively, or derive from the topic.
  - Same slug = same folder (second run updates in place).

FIVE-FIELD KERNEL (SPEC.md):
1. **Why** — The problem being solved; why it matters now; who suffers without it.
2. **Capabilities** — What the system must do (stable IDs: CAP-1, CAP-2, ...); each gets a globally unique, never-reused ID.
3. **Constraints** — What the system must not do, cost/time/regulatory limits, and hard technical boundaries.
4. **Non-goals** — What explicitly is out of scope for this effort.
5. **Success signal** — How to know it worked; measurable where possible.

SPEC LAW (apply strictly):
1. Every sentence earns its place — no filler, no decoration.
2. Capabilities have stable IDs (CAP-N) — never reused, never renumbered. On update, new capabilities get the next unused N.
3. Non-goals cut scope — if it does not actively cut something, it is not a non-goal.
4. Success signal is falsifiable — "users are happy" fails; "P90 checkout time < 2s" passes.
5. The kernel holds decisions, not options — resolve uncertainty before writing.
6. Companion files for overflow — multi-item catalogs, tables, and diagrams live in named companions (e.g., `glossary.md`, `archetypes.md`); SPEC.md cites them.
7. Load-bearing test — if a downstream consumer would change a decision without this claim, it is load-bearing and belongs in the contract.
8. Lean prose discipline — no padding to look thorough.

WHEN TO USE COMPANIONS:
Spawn a companion file when content needs more than one kernel-shape line: multi-item catalogs (per-entity matrices), tables, diagrams (always in companions), editorial voice rules, long-form reference material. Name spec-authored companions for their content type: `glossary.md`, `archetypes.md`, `stack.md`, `conventions.md`. Diagrams always land in companions — SPEC.md prose only.

DETECT INTENT:
- **Create** — No SPEC.md exists at target path.
- **Update** — SPEC.md exists; new information changes or extends it.
- **Validate** — Critique without changing: check Spec Law compliance, internal consistency, downstream readiness.
</critical>

<workflow>

<step n="1" goal="Receive input and bind workspace">
  <action>Read the provided input (file path, paste, or description). If no input is given, ask: "Share a file path, paste content, or describe the idea in as much detail as you have. I'll distill it."</action>
  <action>Determine slug — from input artifact, from topic discussion, or propose one and confirm with user.</action>
  <action>Check if `{spec_output_path}/spec-{slug}/SPEC.md` already exists → Update mode. Otherwise → Create mode.</action>
  <action>Create the folder `{spec_output_path}/spec-{slug}/` if it does not exist. Tell the user the output path.</action>
  <action>Load `{project_context}` if it exists — use for project conventions awareness.</action>
</step>

<step n="2" goal="Choose working mode">
  <check if="input is structured and pre-sorted (PRD, brief, GDD, RFC)">
    <action>Trust the authored separation. Lift kernel-fitting content directly — no elicitation needed. Skip to Step 4.</action>
  </check>
  <check if="input is sparse (less than one paragraph of real context)">
    <action>Tell the user: "This is thin for distillation. Would you like to flesh it out via `bmad-prd` first, or should I distill with best-effort and mark gaps as open questions?"</action>
  </check>
  <action>For mixed input (brain dump, transcript, customer email), ask the user to choose working mode:
    - **Express** — I batch all gaps, distill a best-effort SPEC.md, and mark every uncertainty as an open question `[?]`. Fast.
    - **Guided** — We walk each of the five fields together. Thorough.
  </action>
  <action>WAIT for user choice. Store as {{working_mode}}.</action>
</step>

<step n="3" goal="Guided mode — walk five fields (skip in Express)">
  <check if="{{working_mode}} is Guided">
    <action>Walk the five fields one at a time. For each field, ask an open-ended question, listen, and confirm before moving on. Do NOT author content — pull the user's vision out. Use "I'm assuming X means Y — right?" to confirm inferences.</action>
    <action>Field order: Why → Capabilities → Constraints → Non-goals → Success signal.</action>
    <action>When a user volunteers architecture, implementation details, or technical-how content, note it but route it to a companion (`conventions.md` or `stack.md`) — it does not belong in the kernel.</action>
  </check>
</step>

<step n="4" goal="Distill to SPEC.md">
  <action>Write the five-field kernel to `{spec_output_path}/spec-{slug}/SPEC.md`. Include YAML frontmatter:
    ```yaml
    ---
    title: "{slug}"
    status: draft
    created: {date}
    updated: {date}
    ---
    ```
  </action>
  <action>Apply Spec Law to every sentence — no filler. Each capability gets a stable CAP-N ID.</action>
  <action>Mark gaps as `[?]` with a one-line description of what would resolve them.</action>
  <action>If companion content was identified, write named companion files as siblings of SPEC.md and add a `companions:` list to the frontmatter.</action>
  <action>On Update mode: read the existing SPEC.md first. Preserve capability IDs — new capabilities get the next unused N. Superseded decisions are overwritten; the diff in git is the history.</action>
</step>

<step n="5" goal="Present and iterate">
  <action>Show the user the completed SPEC.md kernel. Walk any `[?]` items — the user can resolve them now or leave them for later.</action>
  <action>Offer:
    - **[AE] Advanced Elicitation** — push deeper on any field
    - **[U] Update** — apply user feedback and regenerate
    - **[V] Validate** — run Spec Law compliance check
    - **[X] Done** — proceed to next step (suggest downstream: PRD, architecture, epics)
  </action>
  <action>WAIT for user choice.</action>
</step>

<step n="6" goal="Validate (if chosen)">
  <action>Run a Spec Law compliance pass on SPEC.md:
    1. Does every sentence earn its place? Flag decoration.
    2. Are CAP-N IDs stable and non-duplicated?
    3. Do Non-goals actively cut scope?
    4. Is the Success signal falsifiable?
    5. Does the kernel hold decisions (not options)?
    6. Is companion-worthy content (tables, diagrams, catalogs) in companions rather than the kernel?
    7. Is every load-bearing claim present?
    8. Is prose lean with no padding?
  </action>
  <action>Output findings as a numbered list, severity-tagged (SPEC LAW VIOLATION / SUGGESTION). Offer to auto-fix violations.</action>
</step>

</workflow>

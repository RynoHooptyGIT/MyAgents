# Investigate - Forensic Case Investigation

<critical>The workflow execution engine is governed by: {project-root}/team/engine/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {project-root}/team/workflows/implementation/investigate/workflow.yaml</critical>
<critical>Communicate all responses in {communication_language} and language MUST be tailored to {user_skill_level}</critical>
<critical>Generate all documents in {document_output_language}</critical>

<critical>
GOAL: Reconstruct what's happening — or what an unfamiliar area does — from the available evidence.
Produce a structured case file another engineer can pick up cold.
Calibrate continuously between defect-chasing (symptom-driven) and area-exploration (no symptom); same discipline applies on both ends.

EVIDENCE GRADING:
- **Confirmed** — Directly observed; cite `path:line`, log timestamp, or commit hash.
- **Deduced** — Logically follows from Confirmed evidence; show the chain.
- **Hypothesized** — Plausible but unconfirmed; state what would confirm or refute it.

CORE PRINCIPLES:
- Stronghold first — anchor in one Confirmed piece of evidence, expand outward. Never start from a theory and hunt for support.
- Challenge the premise — the user's description is a hypothesis, not a fact.
- Follow the evidence, not the narrative — when evidence contradicts the working theory, update the theory.
- Hypotheses are never deleted — update Status (Open / Confirmed / Refuted) and add a Resolution.
- Missing evidence is itself a finding — document the gap and how to obtain it.
- Write it down early — initialize the case file as soon as the slug is agreed.
- Issue independent operations in parallel (multi-grep, multi-read, parallel inventories).
- Communication: evidence-first language ("the evidence shows", "unconfirmed, requires X to verify"). No hedging.

OUTPUT: `{case_file_dir}/{slug}.md` where `{slug}` is the ticket ID (if provided) or a short descriptive name (lowercase-alphanumeric-hyphens agreed with the user).
On path collision with an existing case file: ask whether to rename to `{slug}-{date}.md` or resume the existing file.

After every outcome, present what was learned and PAUSE for the user before continuing.
</critical>

<workflow>

<step n="0" goal="Route: New case or resume">
  <action>Acknowledge the input as a reference — record paths/IDs, do NOT read bulk content yet</action>
  <check if="input is a path to an existing case file in {case_file_dir}">
    <action>Read the case file. Surface in order: open hypotheses (Status=Open) with confirm/refute criteria; open backlog items; missing-evidence rows; last Conclusion with confidence. Ask which thread to pull. New evidence opens a new `## Follow-up: {date}` block. PAUSE for direction.</action>
  </check>
  <action>Otherwise → proceed to Step 1</action>
</step>

<step n="1" goal="Establish scope and stronghold">
  <action>For each input shape, record location/scope/time window ONLY (do not read bulk content here):
    - Issue tracker ticket → fetch title and description via available tools
    - Diagnostic archive → record path, file count, time window
    - Log file or stack trace → record path and time window; only the frame already in user's message is in scope
    - Free-text description → capture verbatim; treat as hypothesis
    - Code area name (no symptom) → record entry point
    - Recent commit area → record commit range
  </action>
  <action>If the user arrived with a hypothesis, register it as Hypothesis #1. Find the stronghold independently.</action>
  <action>Find a stronghold: a Confirmed piece of evidence (error message, function name, HTTP route, config parameter, test case). Anchor here.</action>
  <action>Initialize case file at `{case_file_dir}/{slug}.md` before branching. Fill: Hand-off Brief (rough), Case Info, Problem Statement, initial Evidence Inventory.</action>
  <check if="no Confirmed evidence is reachable">
    <action>Mark the case evidence-light. Populate Investigation Backlog with prioritized data-collection items. Record "to make progress, I need one of: …". PAUSE for user to provide evidence or authorize Step 2 broader scan.</action>
  </check>
  <action>Present scope, stronghold, file path, proposed approach. PAUSE for user direction.</action>
</step>

<step n="2" goal="Map evidence perimeter">
  <action>Survey the scene in parallel across independent categories: diagnostic archives; issue tracker; version control (`git log`, `git blame`); test results; static analysis; source code inventory.</action>
  <action>For any category exceeding ~10K tokens, delegate to a subagent that returns a JSON manifest (paths, sizes, time windows, key fragments cited as `path:line`).</action>
  <action>Classify each: Available / Partial / Missing — Missing is itself a finding.</action>
  <action>Update Evidence Inventory and Investigation Backlog. PAUSE for user direction.</action>
</step>

<step n="3" goal="Reason about cause with discipline">
  <action>Trace causality: symptom-driven → trace backward from symptom to producing conditions. Exploration → trace backward from outputs (returns, side effects, messages sent) to producing conditions.</action>
  <action>Reconstruct the timeline by cross-referencing logs, system events, version control, user observations.</action>
  <action>Form and test hypotheses: state, identify confirming/refuting evidence, search, grade (Confirmed / Refuted / Open). Update Status. Never delete.</action>
  <action>Refutation pass: each time a hypothesis approaches Confirmed, actively look for refuting evidence first. Record the attempt.</action>
  <action>Verify the user's premise independently. If evidence contradicts, say so explicitly.</action>
  <action>Update: Confirmed Findings, Deduced Conclusions, Hypothesized Paths, Backlog, Timeline. PAUSE for user direction.</action>
</step>

<step n="4" goal="Trace source where it matters">
  <action>Issue first-pass scans as parallel tool calls in one message: grep for exact error strings; glob the affected directory; `git log` for recent changes in affected area.</action>
  <action>Then sequentially: read surrounding code; follow the caller chain; watch for boundary crossings (compiled→scripts, IPC, configuration flow).</action>
  <action>Lean by case type:
    - Exploration: I/O mapping (triggers, outputs, dependencies); control-flow filtering (branches, loops, error handling, state-machine transitions).
    - Symptom-driven: depth assessment — is root cause reachable from local context? Surface escalations; never silently expand scope. Trivial fix → one-line code suggestion or draft diff; non-trivial → stop at root cause area.
  </action>
  <action>Investigation stops at the diagnosis — implementation is out of scope.</action>
  <action>Update Source Code Trace (error origin, trigger, condition, related files). PAUSE for user direction.</action>
</step>

<step n="5" goal="Finalize report and hand off clean">
  <action>Update case file with final content:
    - Hand-off Brief rewritten to final form (3 sentences, 15-second read)
    - Final Conclusion with confidence: High (Confirmed root cause, deterministic repro) / Medium (Deduced; minor uncertainty) / Low (Hypothesized; clear data gap)
    - Fix direction when applicable
    - Diagnostic steps if uncertainty remains
    - Reproduction Plan when applicable (or verification plan for exploration cases)
    - Status: Active / Concluded / Blocked on evidence
  </action>
  <action>Present conclusion, then a concrete next-steps menu:
    - Trivial fix → use Dev Story workflow [DS]
    - Scope/plan adjustment → use Correct Course workflow [CC]
    - Tracked story → use Create Story workflow [CS]
    - Fresh review → use Code Review workflow [CR]
    Recommend the highest-value action. Mitigations/workarounds generated only on explicit request.
  </action>
  <action>PAUSE for user direction.</action>
</step>

</workflow>

## Follow-up Iterations

Continue work by appending to the case file under a new `## Follow-up: {date}` block (`#2`, `#3` on same-day reentry). The investigation is complete when:
- Root cause is Confirmed.
- Root cause is Hypothesized with a clear data gap.
- The mental model is sufficient for the user's stated goal (exploration cases).
- The backlog contains only items requiring unavailable evidence.
- The user explicitly concludes.

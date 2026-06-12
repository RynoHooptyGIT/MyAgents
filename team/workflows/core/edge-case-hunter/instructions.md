# Edge Case Hunter Review

<critical>The workflow execution engine is governed by: {project-root}/team/engine/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {project-root}/team/workflows/core/edge-case-hunter/workflow.yaml</critical>
<critical>Communicate all responses in {communication_language} and language MUST be tailored to {user_skill_level}</critical>

<critical>
ROLE: You are a pure path tracer. Never comment on whether code is good or bad — only list missing handling.
METHOD: Exhaustive path enumeration — mechanically walk every branch, not hunt by intuition.
SCOPE: When a diff is provided, scan only the diff hunks and list boundaries directly reachable from changed lines. When full file or function is provided, treat entire content as scope. Ignore the rest of the codebase unless content explicitly references external functions.
OUTPUT: ONLY unhandled paths. Discard handled ones silently. Do NOT editorialize or add filler — findings only.
</critical>

<workflow>

<step n="1" goal="Receive content">
  <action>Load content to review strictly from provided input</action>
  <check if="content is empty or cannot be decoded as text">
    <action>Report: "Content is empty or unreadable. Please provide valid content to review." Then HALT.</action>
  </check>
  <action>Identify content type: diff / full file / function — this determines scope rules</action>
</step>

<step n="2" goal="Exhaustive path analysis">
  <action>Walk every branching path and boundary condition within scope. Report ONLY unhandled ones.</action>
  <action>Derive relevant edge classes from the content itself. Walk these systematically:
    - Control flow: conditionals (missing else/default), loops (off-by-one, infinite, empty collection), error handlers (uncaught exceptions, unhandled error codes), early returns
    - Domain boundaries: where values, states, or conditions transition
    - Input boundaries: null/undefined/empty, zero/negative/max values, wrong types, malformed data
    - Arithmetic: overflow/underflow, division by zero, floating-point edge cases
    - Concurrency: race conditions (shared state, non-atomic read-modify-write), timeout gaps
    - Implicit type coercion: language-specific gotchas
    - Resource lifecycle: files/connections opened but not closed on error paths
    - External call failures: no retry, no timeout, error not propagated
  </action>
  <action>For each path: determine whether the content handles it. Collect ONLY unhandled paths.</action>
</step>

<step n="3" goal="Validate completeness">
  <action>Revisit each edge class from Step 2 — add any newly found unhandled paths; discard confirmed-handled ones</action>
</step>

<step n="4" goal="Present findings">
  <action>Output findings as a Markdown table with columns: Location | Trigger Condition | Suggested Guard | Potential Consequence</action>
  <action>Location format: `file:line` (or `file:hunk` when exact line unavailable)</action>
  <action>Trigger Condition: one-line description, max 15 words</action>
  <action>Suggested Guard: minimal code sketch that closes the gap (single line where possible)</action>
  <action>Potential Consequence: what could actually go wrong, max 15 words</action>
  <action>If no unhandled paths found, report: "No unhandled edge cases found within the provided scope." — this IS a valid result (unlike adversarial review).</action>
</step>

</workflow>

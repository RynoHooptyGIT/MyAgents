# Advanced Elicitation

<critical>The workflow execution engine is governed by: {project-root}/team/engine/workflow.xml</critical>
<critical>You MUST have already loaded and processed: {project-root}/team/workflows/core/advanced-elicitation/workflow.yaml</critical>
<critical>Communicate all responses in {communication_language} and language MUST be tailored to {user_skill_level}</critical>

<critical>
GOAL: Push deeper on prior output. Reconsider, refine, and improve using structured critique methods.
TRIGGER: User asks for deeper critique, mentions a known method (Socratic, pre-mortem, red team, first principles, etc.), or invokes this workflow after generating content.
CONTEXT: Apply methods to the most recently generated content in context, or ask the user what to elicit on.
</critical>

<workflow>

<step n="1" goal="Identify content and present method menu">
  <action>Identify the content to improve: most recent output in context, or ask the user if unclear</action>
  <action>Present the elicitation method menu (pick 5 contextually relevant, or show all with [a]):

```
**Advanced Elicitation — Choose a critique method:**

**Foundational**
1. **Socratic Questioning** — Surface hidden assumptions; ask "why" until the foundation is clear
2. **First Principles** — Strip back to fundamental truths; rebuild reasoning from scratch
3. **Pre-Mortem** — Project forward: this failed. What went wrong and why?
4. **Red Team** — Argue against this output as an adversary; find the weakest points
5. **Devil's Advocate** — Steel-man the strongest counterargument to this approach

**Structural**
6. **Six Thinking Hats** — Rotate through facts, emotions, risks, benefits, creativity, process
7. **SCAMPER** — Substitute, Combine, Adapt, Modify, Put to other uses, Eliminate, Reverse
8. **Morphological Analysis** — Decompose into independent dimensions; explore all combinations
9. **Abstraction Laddering** — Move up (why?) or down (how?) the abstraction ladder to find better framings

**Risk & Framing**
10. **Inversion** — What would make this maximally bad? Avoid those things.
11. **Second-Order Effects** — What are the unintended consequences of this approach?
12. **Cascading Failure Simulation** — Trace failure propagation: if X breaks, what else breaks?
13. **Boundary & Edge Case Sweep** — What happens at the edges, limits, and corners?
14. **Steelmanning** — Build the strongest possible version of the opposing view

**Research & Reasoning**
15. **Chain-of-Thought Scaffolding** — Walk through reasoning step-by-step; expose hidden leaps
16. **Rubber Duck** — Explain the logic aloud to surface gaps
17. **Delphi Method** — Multiple expert perspectives converge through structured rounds

**Creative & Systems**
18. **Jobs-to-be-Done Reframe** — What job is the user hiring this to do?
19. **Empathy Mapping** — Think, feel, say, do, gain, pain from the user's perspective
20. **Blue Ocean Canvas** — Eliminate-reduce-raise-create to find uncontested space
21. **Systems Thinking** — Map feedback loops, leverage points, and emergent behavior
22. **Reverse Brainstorming** — How do we make this fail? Invert to find improvements
23. **TRIZ Contradiction Analysis** — Identify and resolve the core technical or physical contradiction
24. **Impact / Effort Matrix** — Plot every item; focus on high-impact low-effort wins
25. **Five Whys** — Ask "why" five times to find the root cause beneath the surface
26. **Analogical Reasoning** — How did a completely different domain solve an analogous problem?
27. **Perspective Rotation** — View from: end user, ops, competitor, regulator, skeptic, 10-year future
28. **Assumption Surfacing** — List every assumption; which would be fatal if wrong?
29. **Constraint Removal** — Remove each constraint in turn; what new possibilities appear?

[r] Describe a custom method
[a] List all methods with descriptions
[x] Accept current output and proceed
```
  </action>
  <action>WAIT for user selection</action>
</step>

<step n="2" goal="Execute selected method">
  <check if="user selects 1-10">
    <action>Apply the selected method to the identified content. Show the analysis and the improved/refined version.</action>
    <action>Ask: "Apply these changes? [y] Yes / [n] Discard / [e] Edit further"</action>
    <action>If yes: apply changes to content and re-present the Step 1 menu for additional elicitation</action>
    <action>If no: discard proposed changes and re-present the Step 1 menu</action>
    <action>If edit: accept user's modifications, then re-present Step 1 menu</action>
  </check>
  <check if="user selects r (custom method)">
    <action>Ask the user to describe the method. Apply it. Then re-present Step 1 menu.</action>
  </check>
  <check if="user selects x">
    <action>Confirm the final enhanced content. Signal completion. Return to the invoking workflow or agent.</action>
  </check>
</step>

<step n="3" goal="Iterate until user exits">
  <action>Re-present the Step 1 menu after every method execution. Continue until user selects [x].</action>
  <action>Track all enhancements made during the session. The final accepted version is the deliverable.</action>
</step>

</workflow>

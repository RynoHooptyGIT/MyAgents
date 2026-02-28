# Agentic Flow Design

Design multi-agent workflows with routing logic, agent handoff patterns, and state checkpointing.

## Step 1: Survey Existing Agents

- Read all files under `backend/app/agents/` to understand current agent implementations.
- Document each agent's role, input/output contracts, and tool access.
- Review supporting services in `backend/app/services/` that agents depend on.
- Check `backend/app/schemas/` for Pydantic models defining agent request/response contracts.
- Map existing inter-agent dependencies and communication patterns.
- `[INFO]` Note which agents are tenant-aware (accept `tenant_id`) -- all new agents must enforce tenant isolation.

---

## Step 2: Define the Flow Objective

- Clarify the goal of the workflow being designed (user will provide context).
- Identify the participating agents and their responsibilities.
- Define the entry point and terminal conditions.
- Specify success criteria: what constitutes a completed workflow vs a failed one.
- `[WARNING]` If the flow spans more than 5 agents, consider decomposing into sub-flows to limit blast radius.

---

## Step 3: Design Routing Logic

- Specify the routing strategy: deterministic (rule-based), LLM-driven (classifier), or hybrid.
- Define routing conditions: input type, confidence thresholds, error states.
- Document fallback routes for unhandled inputs or low-confidence classifications.
- Produce a routing decision table or flowchart.
- Place routing logic in `backend/app/agents/` as a dedicated orchestrator module.
- `[CRITICAL]` Every routing decision must be logged with the decision reason for auditability.

**Pass/fail criteria for routing design:**
- PASS: All input classes have a defined route, including a fallback.
- FAIL: Any input class can reach a dead end with no handler.

---

## Step 4: Define Handoff Protocol

- Specify the data contract passed between agents at each handoff point.
- Define contracts as Pydantic schemas in `backend/app/schemas/` for validation.
- Include: task context, accumulated state, original user request, intermediate results.
- Define handoff acknowledgment (how the receiving agent confirms it accepted the task).
- Specify timeout and retry policies for each handoff.
- `[WARNING]` Handoff payloads must not include raw credentials or secrets -- pass references only.

---

## Step 5: Design Checkpointing

- Identify checkpointable states in the workflow (after each agent completes its step).
- Define the checkpoint schema: agent ID, step, input, output, timestamp, status.
- Define a SQLAlchemy model in `backend/app/models/` for persisting checkpoints with `tenant_id`.
- Specify storage strategy: database table via the model, with JSON columns for input/output state.
- Design recovery logic: on failure, resume from the last successful checkpoint.
- `[INFO]` Checkpoints enable workflow replay for debugging -- include enough context to reproduce the step.

---

## Step 6: Error Handling & Escalation

- Define per-agent error handling: retry (max 3 attempts), skip, or escalate to human.
- Specify a global escalation path when the workflow cannot proceed.
- Include observability: log each routing decision, handoff, and checkpoint via `backend/app/services/`.
- `[CRITICAL]` Agent failures must not leave orphaned state -- checkpoint status must be updated to FAILED.

**Decision outcomes per check:**
- Retryable error (transient): Retry up to 3 times with exponential backoff.
- Non-retryable error (bad input): Mark step FAILED, skip or escalate based on flow config.
- Timeout: Mark step TIMED_OUT, escalate to human review queue.

---

## Step 7: Generate Report

Write the flow design report to `{output_folder}/agentic-expert/flow-design.md` containing:

- Flow diagram in Mermaid format showing agents, routing, and handoff points.
- Structured flow definition (YAML or JSON) that can be consumed programmatically.
- Checkpoint schema definition.
- Example traces showing successful and failure paths.
- File paths for all new modules to be created.

---

## Step 8: Present Results

- Display the flow diagram and routing decision table to the user.
- Highlight any `[CRITICAL]` or `[WARNING]` findings from the design review.
- Walk through the example traces (success and failure) to validate the design.
- Confirm the user agrees with the agent responsibilities and handoff contracts before proceeding.
- Offer to scaffold the orchestrator, schemas, and checkpoint model if the user approves.

# AI vs Traditional Code Decision Framework

Evaluate features and components to determine whether AI/LLM-based or traditional deterministic code is the right approach.

## Step 1: Gather Feature Requirements

- Collect the feature description, inputs, outputs, and success criteria from the user.
- Identify the data types involved (structured, unstructured, mixed).
- Note latency requirements, accuracy expectations, and cost constraints.
- `[INFO]` If the feature touches tenant-scoped data, confirm `tenant_id` isolation requirements early.

---

## Step 2: Apply the Decision Matrix

Evaluate each dimension and score the feature:

| Dimension | Favors AI | Favors Traditional Code |
|---|---|---|
| **Input variability** | Unstructured, natural language, ambiguous | Structured, well-defined schemas |
| **Output determinism** | Approximate/creative acceptable | Exact, reproducible results required |
| **Rule complexity** | Too many rules to enumerate | Finite, well-understood business rules |
| **Data dependency** | Needs world knowledge or reasoning | Operates on known, bounded data |
| **Latency tolerance** | Seconds acceptable | Sub-millisecond required |
| **Cost sensitivity** | Per-call cost acceptable | High-volume, cost must be near-zero |
| **Auditability** | Explanations acceptable | Deterministic audit trail required |
| **Error tolerance** | Graceful degradation OK | Zero-tolerance for errors |

- **Pass criteria**: 5+ dimensions favor one approach clearly.
- **Hybrid trigger**: 3-4 dimensions favor each side -- recommend a hybrid architecture.

---

## Step 3: Review Existing AI Usage

- Scan `backend/app/agents/` for current AI-powered agent implementations.
- Scan `backend/app/services/` for services that call LLM APIs or orchestrate agent flows.
- Review `backend/app/models/` for any AI-related SQLAlchemy models (prompt logs, inference results).
- Review `backend/app/schemas/` for Pydantic schemas tied to AI request/response contracts.
- Categorize each as: well-suited for AI, could be traditional, or hybrid.
- `[INFO]` Note any agents that share service dependencies -- these influence the candidate design.

---

## Step 4: Analyze the Candidate Feature

- Score the candidate feature against the decision matrix from Step 2.
- If the score is mixed, design a **hybrid approach**: AI for the ambiguous parts, traditional code for the deterministic parts.
- Consider a **tiered strategy**: fast traditional path for common cases, AI fallback for edge cases.
- `[WARNING]` If the feature requires strict auditability (e.g., compliance workflows), document why AI is still acceptable or recommend traditional code.
- **Decision outcome**: Record PASS (clear winner), HYBRID (split approach), or ESCALATE (needs human architect review).

---

## Step 5: Cost-Benefit Analysis

- Estimate per-request cost for the AI approach (tokens, API calls).
- Estimate development cost for the traditional approach (engineering hours, maintenance).
- Project volume: at what request rate does the AI cost exceed the engineering cost?
- Factor in accuracy: what is the cost of errors in each approach?
- `[CRITICAL]` If projected monthly AI cost exceeds the engineering break-even within 6 months, flag for review.
- `[INFO]` Consider multi-tenant volume -- multiply per-request cost by expected tenant count.

---

## Step 6: Recommend Architecture

For AI-recommended features:
- Specify the model tier (small/fast for classification, large for generation).
- Define prompt templates, input/output schemas, and validation layers.
- Place agent code in `backend/app/agents/`, supporting service logic in `backend/app/services/`.
- Define Pydantic schemas in `backend/app/schemas/` for AI request/response validation.
- Include fallback behavior when the AI service is unavailable.

For traditional-code-recommended features:
- Outline the algorithmic approach.
- Place business logic in `backend/app/services/`, expose via `backend/app/routers/`.
- Define test cases in `backend/tests/unit/` for completeness.

For hybrid features:
- Draw the boundary between AI and traditional components.
- Specify the handoff contract between them in `backend/app/schemas/`.
- `[WARNING]` Ensure the traditional path can operate independently if the AI path is degraded.

---

## Step 7: Generate Report

Write the decision report to `{output_folder}/agentic-expert/ai-decision-framework.md` containing:

- Decision summary: AI, traditional, or hybrid with rationale.
- Decision matrix scorecard with per-dimension scores.
- Architecture diagram if hybrid (Mermaid format).
- Cost-benefit summary table.
- Implementation plan with concrete file paths relative to the project structure.
- Risk factors and mitigations.

---

## Step 8: Present Results

- Display the decision summary and recommendation to the user.
- Highlight any `[CRITICAL]` or `[WARNING]` findings that require immediate attention.
- If HYBRID or ESCALATE, walk through the boundary design and ask for user confirmation.
- Offer to proceed with implementation scaffolding if the user approves the recommendation.

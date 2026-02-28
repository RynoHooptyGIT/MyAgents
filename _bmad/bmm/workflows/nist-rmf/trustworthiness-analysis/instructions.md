# NIST AI RMF - Trustworthiness Characteristics Analysis

Analyze AI tools registered in the {project_name} platform against the seven NIST AI RMF trustworthiness characteristics, producing a structured assessment with severity-marked findings and actionable recommendations.

---

## Step 1: Valid and Reliable (MEASURE 2.1, MEASURE 2.3, MEASURE 2.4)

Assess whether the AI system produces accurate, consistent, and dependable outputs.

1. Check `backend/app/routers/rmf_trustworthiness.py` for endpoints that capture validity and reliability metrics.
2. Search `backend/app/models/rmf_trustworthiness.py` for fields tracking accuracy benchmarks, consistency scores, and degradation thresholds.
3. Verify `backend/app/routers/rmf_assessments.py` includes assessment questions covering real-world accuracy validation.
4. Check `backend/app/models/rmf_assessment_question.py` for questions addressing data drift detection and ground truth collection.
5. `[CRITICAL]` Verify mechanisms exist for detecting performance degradation over time (drift monitoring, alert thresholds).
6. `[WARNING]` Check that accuracy is measured across disaggregated subgroups and deployment contexts, not just aggregate metrics.
7. `[INFO]` Verify rollback and recovery procedures are documented for reliability failures.

---

## Step 2: Safe (MAP 3.2, MAP 3.5, MANAGE 2.3)

Evaluate safeguards preventing AI system failure from causing harm.

1. Search `backend/app/routers/rmf_risk_tiers.py` for safety-critical tier definitions and escalation rules.
2. Check `backend/app/models/rmf_risk_tier.py` for safety impact fields and constraint enforcement.
3. Verify `backend/app/routers/rmf_classification.py` captures safety impact scoring per AI tool (Negligible through Critical).
4. Check `packages/frontend/src/features/ai-rmf/components/SubcategoryDetailPage.tsx` for user-facing safety boundary displays.
5. `[CRITICAL]` Verify human override and emergency deactivation capabilities exist for high-risk AI tools.
6. `[CRITICAL]` Check that safety-critical output constraints and guardrails are enforced before AI recommendations reach users.
7. `[WARNING]` Verify safety testing covers edge cases, adversarial scenarios, and healthcare-specific failure modes.

---

## Step 3: Secure and Resilient (GOVERN 6.2, MANAGE 4.3, MAP 3.4)

Assess protection against adversarial attacks and operational failures.

1. Check `backend/app/middleware/tenant_isolation.py` for cross-tenant data leakage prevention in AI operations.
2. Search `backend/app/middleware/audit_logging.py` for AI-specific audit trail coverage.
3. Verify `backend/app/middleware/rate_limiting.py` protects AI endpoints from abuse.
4. Check `backend/app/routers/ai_rmf.py` for access control on AI tool registration and assessment data.
5. `[CRITICAL]` Verify tenant isolation prevents AI model data, assessments, and recommendations from leaking across organizations.
6. `[WARNING]` Check for adversarial input protections (prompt injection, model evasion) where AI tools process user content.
7. `[WARNING]` Verify supply chain security for third-party AI model dependencies and API integrations.

---

## Step 4: Accountable and Transparent (GOVERN 2.1, GOVERN 3.1, MAP 1.1)

Verify accountability structures and transparency of AI system operations.

1. Check `backend/app/routers/rmf_governance_policies.py` for role-based accountability assignments tied to AI tools.
2. Verify `backend/app/middleware/audit_logging.py` creates audit trails connecting AI decisions to responsible parties and tenants.
3. Search `packages/frontend/src/features/ai-rmf/components/AIRMFHubPage.tsx` for transparency disclosures visible to users.
4. Check `backend/app/models/rmf_governance_policy.py` for policy fields covering third-party AI component accountability.
5. `[CRITICAL]` Verify that users are informed when interacting with AI-generated content or recommendations.
6. `[WARNING]` Check that AI tool documentation (purpose, capabilities, limitations) is accessible through the frontend.
7. `[INFO]` Verify escalation paths exist for AI-related concerns within governance structures.

---

## Step 5: Explainable and Interpretable (MEASURE 2.5, MEASURE 2.8, MAP 1.6)

Assess whether AI outputs can be understood by relevant stakeholders.

1. Check `backend/app/routers/rmf_trustworthiness.py` for explainability scoring endpoints.
2. Search `backend/app/schemas/rmf_trustworthiness.py` for fields capturing explanation quality and audience appropriateness.
3. Verify `packages/frontend/src/features/ai-rmf/components/SuggestionBadge.tsx` communicates confidence levels with AI suggestions.
4. Check `packages/frontend/src/features/ai-rmf/hooks/useAutoCompletionSuggestions.ts` for how AI recommendations are surfaced to users.
5. `[CRITICAL]` Verify AI-generated risk classifications include explanations that healthcare administrators can understand and act on.
6. `[WARNING]` Check that uncertainty and confidence levels are reported alongside AI outputs, not hidden.
7. `[INFO]` Verify technical explanations (feature importance, decision rationale) are available for developers and auditors.

---

## Step 6: Privacy-Enhanced and Fair (MEASURE 2.10, MEASURE 2.11, GOVERN 1.2)

Evaluate privacy protections and fairness in AI system operations.

1. Check `backend/app/middleware/tenant_isolation.py` for data minimization in AI processing contexts.
2. Verify `backend/app/models/ai_tool.py` captures data types processed (PII, PHI) and consent requirements.
3. Search `backend/app/schemas/rmf_classification.py` for rights impact and equity assessment fields.
4. Check `backend/app/routers/rmf_assessments.py` for assessment questions covering bias measurement and fairness metrics.
5. `[CRITICAL]` Verify PHI/PII handling in AI tool data flows complies with HIPAA requirements (data at rest, in transit, in processing).
6. `[CRITICAL]` Check that bias measurement across protected classes is included in assessment questionnaires.
7. `[WARNING]` Verify fairness assessments are periodic (not just pre-deployment) and results are tracked over time.
8. `[INFO]` Check for privacy-preserving techniques documentation (anonymization, differential privacy) where applicable.

---

## Step 7: Produce Report

Output a structured trustworthiness report to `{output_folder}/nist-rmf/trustworthiness-analysis.md` with:

1. **Executive Summary** - overall trustworthiness posture, highest-risk characteristics, top-3 priority actions
2. **Characteristic Scorecard**:

| Characteristic | Maturity | Score (1-5) | Key Strengths | Key Gaps | Severity |
|---------------|----------|-------------|---------------|----------|----------|

   Maturity levels: 1-Initial, 2-Developing, 3-Defined, 4-Managed, 5-Optimizing

3. **Radar Chart Data** - characteristic/score pairs for visualization
4. **Detailed Findings** - per-characteristic breakdown with `[CRITICAL]`, `[WARNING]`, `[INFO]` markers
5. **Recommendations** - mapped to specific NIST AI RMF subcategories with implementation guidance

---

## Step 8: Present Results

Summarize findings for the requesting agent or user:

1. State the overall trustworthiness score (average across seven characteristics).
2. Highlight any characteristic scoring below 3 as a `[CRITICAL]` gap requiring immediate attention.
3. Call out the strongest characteristic as a model for improving weaker areas.
4. List top-3 priority improvements with the NIST subcategories and {project_name} files they affect.
5. Flag any healthcare-specific trustworthiness concerns (patient safety, PHI privacy, clinical fairness).

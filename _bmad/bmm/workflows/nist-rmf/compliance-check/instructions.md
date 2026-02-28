# NIST AI RMF 1.0 - Compliance Check

Evaluate the {project_name} platform against the NIST AI Risk Management Framework 1.0 across all four core functions (GOVERN, MAP, MEASURE, MANAGE) to identify compliance gaps, score maturity, and recommend improvements.

---

## Step 1: GOVERN Function Audit

Assess organizational AI risk management policies and governance structures.

1. Search `backend/app/routers/rmf_governance_policies.py` and `backend/app/routers/rmf_governance_dashboard.py` for implemented governance endpoints.
2. Check `backend/app/models/rmf_governance_policy.py` for policy data model completeness (fields for ownership, review cadence, approval status).
3. Verify `backend/app/middleware/tenant_isolation.py` enforces tenant-scoped governance policies.
4. Check `packages/frontend/src/features/ai-rmf/` for governance UI components enabling policy creation and review.
5. Verify GOVERN subcategories against implementation:
   - `[CRITICAL]` GOVERN 1.1-1.7: Regulatory requirements, risk thresholds, and tolerance documented in system
   - `[CRITICAL]` GOVERN 2.1-2.3: Roles, training, and executive engagement modeled
   - `[WARNING]` GOVERN 3.1-3.2: Decision-making and third-party policies captured
   - `[WARNING]` GOVERN 4.1-4.2: Risk culture and awareness program support
   - `[INFO]` GOVERN 5.1-5.2: Stakeholder engagement and feedback mechanisms
   - `[CRITICAL]` GOVERN 6.1-6.2: Lifecycle policies and incident response plans

---

## Step 2: MAP Function Audit

Verify AI risk identification and contextual categorization capabilities.

1. Search `backend/app/routers/rmf_classification.py` for risk classification endpoints.
2. Check `backend/app/schemas/rmf_classification.py` for impact dimension coverage (safety, rights, economic, operational, reputational).
3. Verify `backend/app/routers/ai_rmf.py` captures intended purpose, user population, and deployment context per AI tool.
4. Check `backend/app/models/ai_tool.py` for fields documenting beneficial uses, known limitations, and data types processed.
5. Verify MAP subcategories against implementation:
   - `[CRITICAL]` MAP 1.1-1.6: Purpose documentation, stakeholder involvement, impact assessment
   - `[WARNING]` MAP 2.1-2.3: User identification, deployment assumptions, scientific integrity
   - `[CRITICAL]` MAP 3.1-3.5: Benefit/cost analysis, harm assessment, risk prioritization
   - `[WARNING]` MAP 4.1-4.2: Third-party risk identification, measurement approaches
   - `[INFO]` MAP 5.1-5.2: Broader impact assessment, continuous risk identification

---

## Step 3: MEASURE Function Audit

Assess AI risk quantification, tracking, and measurement capabilities.

1. Search `backend/app/routers/rmf_assessments.py` and `backend/app/routers/rmf_assessment_questions.py` for assessment implementation.
2. Check `backend/app/models/rmf_assessment.py` and `backend/app/models/rmf_assessment_question.py` for question coverage across MEASURE subcategories.
3. Verify `backend/app/services/ai_rmf_automation_service.py` supports automated assessment generation.
4. Check `backend/app/routers/rmf_trustworthiness.py` and `backend/app/models/rmf_trustworthiness.py` for trustworthiness scoring.
5. Verify MEASURE subcategories against implementation:
   - `[CRITICAL]` MEASURE 1.1-1.3: Risk metrics, contextual measurement, validation
   - `[CRITICAL]` MEASURE 2.1-2.13: Performance evaluation, disaggregated analysis, drift detection, privacy, fairness, interpretability
   - `[WARNING]` MEASURE 3.1-3.3: Risk tracking, enterprise integration, feedback loops
   - `[WARNING]` MEASURE 4.1-4.2: Decision-informing results, periodic review

---

## Step 4: MANAGE Function Audit

Verify risk response, resource allocation, and recovery capabilities.

1. Search `backend/app/routers/rmf_risk_tiers.py` for risk tier management and response workflows.
2. Check `backend/app/models/rmf_risk_tier.py` for tier definitions including mitigation requirements per level.
3. Verify `backend/app/routers/ai_rmf_gap_analysis.py` and `backend/app/services/ai_rmf_gap_analysis_service.py` implement gap-to-action tracking.
4. Check for incident response and deactivation mechanisms across routers.
5. Verify MANAGE subcategories against implementation:
   - `[CRITICAL]` MANAGE 1.1-1.4: Risk treatment plans, residual risk, stakeholder communication
   - `[WARNING]` MANAGE 2.1-2.4: Resource allocation, sustainability, human override, appeals
   - `[CRITICAL]` MANAGE 3.1-3.2: Pre-deployment testing, deployment approval gates
   - `[WARNING]` MANAGE 4.1-4.3: Post-deployment monitoring, incident reporting, AI-specific response procedures

---

## Step 5: Evidence Collection and Maturity Scoring

Collect evidence artifacts and assign maturity scores per function.

1. For each function, catalog evidence files (models, routers, services, schemas, migrations, frontend components).
2. Score each function using the NIST-aligned maturity rubric:
   - **1 - Initial**: No implementation; subcategory not addressed in code or documentation
   - **2 - Developing**: Partial implementation; some endpoints or models exist but incomplete coverage
   - **3 - Defined**: Documented and standardized; schemas, models, and routers cover the subcategory
   - **4 - Managed**: Measured and monitored; automated assessments, dashboards, and tracking in place
   - **5 - Optimizing**: Continuous improvement; gap analysis, auto-completion suggestions, and feedback loops active
3. Produce a maturity scorecard:

| Function | Score (1-5) | Subcategories Implemented | Subcategories Missing | Evidence Files |
|----------|-------------|---------------------------|----------------------|----------------|

4. Flag any function scoring below 3 as `[CRITICAL]`, below 4 as `[WARNING]`, 4+ as `[INFO]`.

---

## Step 6: Produce Report

Output a structured compliance report to `{output_folder}/nist-rmf/compliance-check.md` with:

1. **Executive Summary** - overall maturity level, highest-risk function, top-5 remediation items
2. **Maturity Scorecard** - table with per-function scores and evidence
3. **Compliance Matrix** - full subcategory-level status using:

| Subcategory | Status | Evidence File(s) | Gap Description | Severity | Priority |
|-------------|--------|-------------------|-----------------|----------|----------|

   Status values: Implemented, Partially Implemented, Not Implemented, Not Applicable

4. **Gap Analysis** - grouped by severity (`[CRITICAL]` > `[WARNING]` > `[INFO]`)
5. **Remediation Roadmap** - prioritized action items with estimated effort

---

## Step 7: Present Results

Summarize findings for the requesting agent or user:

1. State the overall maturity level (average across four functions).
2. Highlight any `[CRITICAL]` gaps that block compliance claims.
3. List the top-3 priority remediation actions with the specific NIST subcategories they address.
4. Note any functions at maturity level 4+ as strengths to preserve.
5. Recommend a re-assessment cadence based on current maturity (monthly if below 3, quarterly if 3-4, semi-annually if 4+).

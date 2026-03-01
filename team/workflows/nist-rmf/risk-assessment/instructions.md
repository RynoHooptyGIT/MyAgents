# NIST AI RMF - Risk Assessment for AI Tool Classification

Provide structured risk assessment for AI tools within the {project_name} platform, applying NIST AI RMF principles to determine impact levels, risk tiers, stakeholder effects, and mitigation strategies.

---

## Step 1: Define Context and Scope (MAP 1.1, MAP 1.5, MAP 1.6)

Establish the AI tool's operational boundaries and regulatory environment.

1. Search `backend/app/models/ai_tool.py` for the tool's registered purpose, domain, and deployment context fields.
2. Check `backend/app/routers/ai_rmf.py` for endpoints capturing intended users and affected parties.
3. Verify `backend/app/schemas/rmf_classification.py` includes fields for data types processed (PII, PHI, financial, public).
4. Document the AI tool's decision-making role from classification data: autonomous, assistive, or informational.
5. `[CRITICAL]` Confirm the regulatory environment is identified (HIPAA for healthcare, GDPR if applicable, state AI laws).
6. `[INFO]` Verify deployment context assumptions (on-premise vs. cloud, single-tenant vs. multi-tenant) are captured.

---

## Step 2: Impact Level Assessment (MAP 3.1, MAP 3.2, MAP 3.5)

Evaluate the AI tool across five impact dimensions using the platform's classification system.

1. Check `backend/app/routers/rmf_classification.py` for impact scoring endpoints across all five dimensions.
2. Verify `backend/app/schemas/rmf_classification.py` defines the five-level scale (Negligible / Low / Moderate / High / Critical) for each:
   - **Safety Impact**: Could failure cause physical harm or endanger patient life?
   - **Rights Impact**: Could the tool affect civil rights, health equity, or informed consent?
   - **Economic Impact**: What financial harm could result from failure or misuse to the organization or patients?
   - **Operational Impact**: How would failure affect clinical workflows or administrative operations?
   - **Reputational Impact**: What reputational damage to the healthcare organization could result?
3. `[CRITICAL]` Flag any AI tool processing PHI with Safety or Rights impact below Moderate as potentially under-classified.
4. `[WARNING]` Verify impact assessments consider downstream effects, not just direct tool outputs.

---

## Step 3: Stakeholder Impact Analysis

Assess risks to each stakeholder group affected by the AI tool.

1. For each stakeholder group, evaluate exposure and potential harm:
   - **Patients**: Incorrect recommendations affecting care decisions, privacy breaches of PHI, biased assessments across demographics
   - **Healthcare Workers**: Over-reliance on AI tool output, alert fatigue from excessive warnings, workflow disruption from failures
   - **Administrators**: Compliance liability from AI governance gaps, resource misallocation from inaccurate risk scoring, audit exposure
2. Check `backend/app/routers/rmf_assessments.py` for assessment questions that address stakeholder-specific impacts.
3. `[CRITICAL]` Verify patient-facing AI tools have higher scrutiny than internal administrative tools.
4. `[WARNING]` Check that healthcare worker feedback mechanisms exist for reporting AI tool issues.

---

## Step 4: Risk Scenario Analysis and Heat Map (MAP 3.3, MAP 3.4, MEASURE 1.1)

Identify specific risk scenarios and map them on a likelihood-by-impact matrix.

1. Evaluate {project_name}-specific risk scenarios:
   - `[CRITICAL]` **Incorrect tool recommendation**: AI suggests inappropriate tool for a clinical use case
   - `[CRITICAL]` **Cross-tenant data leakage**: AI assessments or recommendations expose data between organizations
   - `[CRITICAL]` **Biased risk classification**: AI auto-classification systematically under-rates risk for certain tool categories
   - `[WARNING]` **Assessment question staleness**: Seeded questions become outdated as NIST guidance evolves
   - `[WARNING]` **Automation over-reliance**: Auto-generated assessments accepted without human review
   - `[INFO]` **Dashboard misinterpretation**: Governance dashboard data displayed without sufficient context
2. Check `backend/app/services/ai_rmf_automation_service.py` for guardrails on automated assessment generation.
3. Check `backend/app/middleware/tenant_isolation.py` for cross-tenant protections on AI data flows.
4. Construct a risk heat map (Likelihood: Rare/Unlikely/Possible/Likely/Almost Certain vs. Impact: Negligible/Low/Moderate/High/Critical).
5. Plot each scenario on the heat map and assign risk ratings (Low / Medium / High / Extreme).

---

## Step 5: Risk Tier Classification and Mitigation Mapping (GOVERN 1.3, MANAGE 1.1, MANAGE 1.2)

Assign the overall risk tier and map mitigations to identified risks.

1. Check `backend/app/routers/rmf_risk_tiers.py` and `backend/app/models/rmf_risk_tier.py` for tier definitions:
   - **Tier 1 - Minimal**: Informational tools, standard monitoring, no decision authority
   - **Tier 2 - Low**: Assistive tools with human oversight, periodic review
   - **Tier 3 - Moderate**: Decision-influencing tools, human-in-the-loop, regular assessment
   - **Tier 4 - High**: Significant autonomy or sensitive domains, continuous monitoring, executive oversight
   - **Tier 5 - Unacceptable**: Critical safety/rights risk, executive review required, may prohibit deployment
2. For each risk scenario, map mitigations to existing controls in the codebase:
   - **Technical**: `backend/app/middleware/tenant_isolation.py`, `backend/app/middleware/rate_limiting.py`, `backend/app/middleware/audit_logging.py`
   - **Process**: Assessment workflows in `backend/app/routers/rmf_assessments.py`, approval gates in risk tier definitions
   - **Governance**: Policies in `backend/app/routers/rmf_governance_policies.py`, gap tracking in `backend/app/services/ai_rmf_gap_analysis_service.py`
3. `[CRITICAL]` Flag any Tier 4-5 risk without a documented mitigation control.
4. `[WARNING]` Identify residual risks that remain after mitigations and determine if they fall within organizational tolerance.

---

## Step 6: Produce Report

Output a structured risk assessment report to `{output_folder}/nist-rmf/risk-assessment.md` with:

1. **AI Tool Profile** - name, purpose, domain, data types, decision role, regulatory environment
2. **Impact Assessment Matrix** - scores across all five dimensions with justification
3. **Stakeholder Impact Summary** - findings per stakeholder group with severity markers
4. **Risk Heat Map** - likelihood-by-impact matrix with plotted scenarios
5. **Risk Tier Assignment** - tier level with justification and comparison to similar tools
6. **Mitigation Plan** - prioritized controls mapped to risks with responsible codebase files
7. **Residual Risk Statement** - accepted risks with rationale and owner
8. **Review Schedule** - re-assessment frequency (monthly for Tier 4-5, quarterly for Tier 3, semi-annually for Tier 1-2)

---

## Step 7: Present Results

Summarize findings for the requesting agent or user:

1. State the assigned risk tier and the primary justification for that classification.
2. Highlight all `[CRITICAL]` risk scenarios and whether mitigations are in place.
3. Present the risk heat map summary: count of scenarios at each risk rating (Low/Medium/High/Extreme).
4. List the top-3 unmitigated or under-mitigated risks requiring immediate attention.
5. Identify any stakeholder group bearing disproportionate risk exposure.
6. Recommend next steps: mitigation implementation, escalation to governance, or re-classification.

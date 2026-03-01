# Bias Detection Workflow

Detect and analyze bias and fairness issues in AI models used by the {project_name} platform.

## Step 1: Identify Protected Attributes

- Catalog sensitive attributes in the dataset (demographics, geography, organization size)
- Map indirect proxies that may correlate with protected attributes
- Review {project_name}'s 76+ SQLAlchemy models in `backend/app/models/` for fields that could introduce bias
- Scan agent definitions in `backend/app/agents/*.py` for hardcoded demographic assumptions
- Document which attributes are used as features vs. available only for auditing
- `[CRITICAL]` Any protected attribute used directly as a model feature must be flagged immediately
- `[WARNING]` Proxy attributes (e.g., zip code correlating with race) require documented justification
- `[INFO]` Log the complete attribute inventory for traceability

**Pass/Fail**: Fail if any protected attribute is used as a direct feature without explicit regulatory justification.

---

## Step 2: Define Fairness Criteria

- Select applicable fairness definitions for the use case:
  - **Demographic parity**: Equal positive prediction rates across groups
  - **Equalized odds**: Equal TPR and FPR across groups
  - **Calibration**: Predicted probabilities reflect true outcomes per group
  - **Individual fairness**: Similar individuals receive similar predictions
- Document trade-offs between fairness definitions (impossibility theorem)
- Justify chosen criteria with business and regulatory context
- `[CRITICAL]` At least one group-level and one individual-level fairness criterion must be selected
- `[INFO]` Reference NIST AI RMF MAP and MEASURE functions for alignment

**Pass/Fail**: Fail if no fairness criteria are formally selected and justified.

---

## Step 3: Analyze Training Data Distribution

- Compute representation statistics for each protected group
- Identify underrepresented groups with insufficient samples
- Check label distribution across groups (outcome bias)
- Detect historical bias in labels (feedback loops)
- Verify multi-tenant data does not systematically over/under-represent groups
- Query data through `backend/app/services/*.py` to confirm tenant-level distribution
- `[CRITICAL]` Any group with fewer than 30 samples must be flagged as unreliable for statistical analysis
- `[WARNING]` Label imbalance exceeding 80/20 across any protected group requires mitigation plan

**Pass/Fail**: Fail if underrepresented groups are present without a documented mitigation strategy.

---

## Step 4: Measure Model Bias Metrics

- Compute per-group performance: accuracy, precision, recall, F1
- Calculate disparate impact ratio (80% rule threshold)
- Measure equalized odds difference and predictive parity difference
- Generate calibration curves per group
- Run intersectional analysis (combinations of protected attributes)
- `[CRITICAL]` Disparate impact ratio below 0.8 is a blocking finding
- `[WARNING]` Equalized odds difference exceeding 0.1 requires documented justification
- `[INFO]` Record all metric values with confidence intervals for audit trail

**Pass/Fail**: Fail if disparate impact ratio is below 0.8 for any protected group without approved mitigation.

---

## Step 5: Apply Mitigation Strategies

- **Pre-processing**: Resampling, reweighting, representation learning
- **In-processing**: Adversarial debiasing, fairness constraints in loss
- **Post-processing**: Threshold adjustment per group, reject option classification
- Document trade-off between fairness improvement and overall performance
- Re-measure all bias metrics after each mitigation
- `[CRITICAL]` Every mitigation must include before/after metric comparison
- `[WARNING]` Overall model performance drop exceeding 5% requires stakeholder sign-off
- `[INFO]` Record mitigation approach rationale in `backend/app/agents/` docstrings where applicable

**Pass/Fail**: Fail if mitigation is applied without documented before/after metric comparison.

---

## Step 6: Validate Tenant-Level Fairness

- Run bias analysis per `tenant_id` to detect tenant-specific disparities
- Verify `apply_multi_tenant_rls()` does not introduce selection bias in evaluation data
- Check that tenant data isolation does not mask systemic bias patterns
- Review Alembic migrations in `backend/alembic/versions/` for schema changes affecting protected fields
- Flag tenants where sample sizes are too small for reliable fairness assessment
- `[CRITICAL]` Cross-tenant data leakage during bias evaluation is a blocking security finding
- `[WARNING]` Tenants with fewer than 50 records must be excluded from per-tenant fairness reporting

**Pass/Fail**: Fail if any cross-tenant data leakage is detected during evaluation.

---

## Step 7: Generate Report

- Write the full bias detection report to `{output_folder}/ml-expert/bias-detection.md`
- Summarize bias findings with severity ratings (`[CRITICAL]` / `[WARNING]` / `[INFO]`)
- Visualize metric disparities across groups (bar charts, calibration plots)
- Document mitigation actions taken and residual bias
- Provide monitoring recommendations for ongoing fairness tracking
- List compliance-relevant findings (NIST AI RMF alignment)
- Include per-tenant fairness summary table
- `[CRITICAL]` Report must include explicit pass/fail verdict for each step

---

## Step 8: Present Results

- Present the report to the requesting agent or user
- Highlight all `[CRITICAL]` findings first, then `[WARNING]`, then `[INFO]`
- Summarize overall bias risk level: **Low** / **Medium** / **High** / **Critical**
- Recommend next steps: approve, approve with conditions, or block deployment
- If any step received a Fail verdict, the overall workflow result is **Fail**

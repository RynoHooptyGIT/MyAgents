# Evaluation Methodology Workflow

Design evaluation methodology with appropriate metrics for AI models in the {project_name} platform.

## Step 1: Define Evaluation Objectives

- Identify the prediction task (binary classification, multi-class, ranking, regression)
- Determine business-critical outcomes (false positives vs. false negatives cost)
- Map model outputs to {project_name} domain concepts (risk scores, classifications, recommendations)
- Review agent definitions in `backend/app/agents/*.py` to understand how predictions are consumed
- `[CRITICAL]` The primary business objective must be explicitly stated and agreed upon before proceeding
- `[INFO]` Document the relationship between model output and downstream API responses in `backend/app/routers/`

**Pass/Fail**: Fail if the prediction task type and business-critical outcome are not formally documented.

---

## Step 2: Select Primary Metrics

- **Classification tasks**: Precision, Recall, F1-score (macro/micro/weighted)
- **Binary classification**: AUC-ROC, AUC-PR, specificity, sensitivity
- **Regression tasks**: MAE, RMSE, R-squared, MAPE
- **Ranking tasks**: NDCG, MAP, MRR
- Choose the primary metric that aligns with business priority
- Document why secondary metrics are tracked but not optimized for
- `[CRITICAL]` Exactly one primary metric must be designated; all others are secondary
- `[WARNING]` If AUC-ROC is chosen for imbalanced datasets, AUC-PR must also be tracked
- `[INFO]` Record metric definitions in evaluation script headers for reproducibility

**Pass/Fail**: Fail if no primary metric is designated or if metric selection contradicts task type.

---

## Step 3: Design Cross-Validation Strategy

- Select CV method: k-fold, stratified k-fold, time-series split, or group k-fold
- For multi-tenant data: use group k-fold with `tenant_id` as the group to prevent leakage
- Define fold count (minimum 5 for stable estimates, 10 for final evaluation)
- Ensure class balance is maintained across folds (stratification)
- Document holdout test set creation (never used during development)
- Verify data extraction queries in `backend/app/services/*.py` respect `apply_multi_tenant_rls()` boundaries
- `[CRITICAL]` Data leakage between train and test splits is a blocking finding
- `[CRITICAL]` Cross-tenant leakage via shared folds must be prevented when using group k-fold
- `[WARNING]` Fewer than 5 folds requires documented justification (e.g., compute constraints)

**Pass/Fail**: Fail if data leakage is detected or tenant isolation is violated in fold assignment.

---

## Step 4: Establish Baselines

- Define naive baselines (majority class, mean prediction, random)
- Identify existing heuristic or rule-based approaches in {project_name}'s `backend/app/agents/*.py`
- Set minimum performance thresholds relative to baselines
- Document human-level performance estimates where applicable
- Review {project_name}'s 76+ SQLAlchemy models in `backend/app/models/` for domain rules that inform baselines
- `[CRITICAL]` The candidate model must exceed the best baseline on the primary metric to proceed
- `[WARNING]` If baseline performance is already high (>0.95), marginal model improvements need cost-benefit analysis
- `[INFO]` Record baseline results alongside model results for every evaluation run

**Pass/Fail**: Fail if candidate model does not statistically exceed the best baseline on the primary metric.

---

## Step 5: Design Statistical Significance Testing

- Select appropriate tests (paired t-test, Wilcoxon signed-rank, McNemar's)
- Define confidence level (95% minimum)
- Plan for multiple comparison correction (Bonferroni, Holm) when comparing 3+ models
- Determine minimum sample size for reliable comparisons
- `[CRITICAL]` All model comparison claims must be backed by a significance test at p < 0.05
- `[WARNING]` Effect size must be reported alongside p-values to avoid trivially significant results
- `[INFO]` Document the test assumptions and verify they hold for the data distribution

**Pass/Fail**: Fail if model superiority is claimed without a passing significance test.

---

## Step 6: Plan Per-Tenant Evaluation

- Break down metrics by `tenant_id` to detect performance disparities
- Flag tenants with insufficient data for reliable evaluation (minimum 50 records)
- Design aggregation strategy (micro vs. macro averaging across tenants)
- Set minimum per-tenant sample thresholds for reporting
- Cross-reference tenant schemas in `backend/app/models/` for tenant-specific feature availability
- Review Alembic migrations in `backend/alembic/versions/` for schema changes affecting evaluation data
- `[CRITICAL]` Performance variance exceeding 20% across tenants must be investigated and documented
- `[WARNING]` Tenants below the minimum sample threshold must be excluded from per-tenant reporting

**Pass/Fail**: Fail if cross-tenant performance variance exceeds 20% without documented root cause.

---

## Step 7: Generate Report

- Write the full evaluation methodology report to `{output_folder}/ml-expert/evaluation-methodology.md`
- Write reproducible evaluation script specifications
- Define metric reporting format (mean +/- std, confidence intervals)
- Create comparison tables template for model selection
- Specify when re-evaluation is triggered (data drift, model update, schema change)
- Include per-tenant evaluation breakdown table
- Tag all findings with severity markers (`[CRITICAL]` / `[WARNING]` / `[INFO]`)
- `[CRITICAL]` Report must include explicit pass/fail verdict for each step

---

## Step 8: Present Results

- Present the report to the requesting agent or user
- Highlight all `[CRITICAL]` findings first, then `[WARNING]`, then `[INFO]`
- Summarize overall evaluation readiness: **Ready** / **Conditional** / **Not Ready**
- Recommend next steps: proceed to training, revise methodology, or collect more data
- If any step received a Fail verdict, the overall workflow result is **Fail**

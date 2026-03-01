# Model Review Workflow

Review ML model architecture, training pipeline, and deployment readiness for the {project_name} platform.

## Step 1: Gather Model Specification

- Identify the model type (classification, regression, NLP, embedding, etc.)
- Collect architecture details: layers, parameters, input/output shapes
- Document framework and version (PyTorch, TensorFlow, scikit-learn, HuggingFace)
- Locate model definition files in `backend/app/agents/*.py` or dedicated ML module paths
- `[CRITICAL]` Framework version must be pinned; floating versions are a blocking finding
- `[INFO]` Record total parameter count and estimated memory footprint

**Pass/Fail**: Fail if model type, framework, or architecture details are undocumented.

---

## Step 2: Review Architecture Design

- Validate layer composition and activation functions for the task
- Check for appropriate regularization (dropout, L1/L2, batch norm)
- Assess model complexity vs. dataset size (overfitting risk)
- Verify input preprocessing matches expected data from {project_name}'s 76+ SQLAlchemy models in `backend/app/models/`
- Confirm output format aligns with downstream consumers in `backend/app/routers/` and `backend/app/services/`
- `[CRITICAL]` Model with >10x parameters relative to training samples must include regularization justification
- `[WARNING]` Custom activation functions require documented rationale and testing evidence
- `[INFO]` Note any architecture decisions that deviate from standard practices

**Pass/Fail**: Fail if overfitting risk is high and no regularization strategy is documented.

---

## Step 3: Evaluate Training Pipeline

- Review data loading and batching strategy
- Validate train/validation/test split methodology
- Check for data leakage between splits (temporal, group, or feature leakage)
- Assess augmentation techniques (if applicable)
- Verify loss function selection for the task objective
- Review optimizer choice and learning rate schedule
- Confirm reproducibility (random seeds, deterministic operations)
- `[CRITICAL]` Data leakage between splits is a blocking finding
- `[CRITICAL]` Non-reproducible training (missing seeds or non-deterministic ops) must be resolved
- `[WARNING]` Learning rate schedule without warmup for transformer models requires justification
- `[INFO]` Document expected training time and compute requirements

**Pass/Fail**: Fail if data leakage is detected or reproducibility cannot be confirmed.

---

## Step 4: Assess Multi-Tenant Data Isolation

- Verify training data respects `tenant_id` boundaries
- Confirm model inference does not leak cross-tenant information
- Validate that `apply_multi_tenant_rls()` patterns are honored in data extraction queries
- Check that `AsyncSession` queries used for training data use proper tenant filters
- Review Alembic migrations in `backend/alembic/versions/` for RLS policy changes affecting training data
- Inspect `backend/app/services/*.py` for data extraction functions feeding the training pipeline
- `[CRITICAL]` Cross-tenant data leakage in training or inference is a blocking security finding
- `[CRITICAL]` Missing tenant filters on any training data query must be fixed before proceeding
- `[WARNING]` Shared model weights across tenants require documented privacy analysis

**Pass/Fail**: Fail if any cross-tenant data leakage is detected in training or inference paths.

---

## Step 5: Review Deployment Readiness

- Verify model serialization format (ONNX, TorchScript, SavedModel, or other safe format)
- Check inference latency against API SLA requirements
- Validate memory footprint for containerized deployment
- Confirm model versioning and rollback strategy
- Review monitoring hooks (prediction distribution drift, latency tracking)
- Assess batch vs. real-time inference requirements
- Verify integration points with `backend/app/routers/` API endpoints
- `[CRITICAL]` Inference latency exceeding API SLA is a blocking finding
- `[CRITICAL]` No rollback strategy is a blocking finding for production deployment
- `[WARNING]` Memory footprint exceeding 512MB per instance requires infrastructure review
- `[INFO]` Document expected QPS capacity and scaling characteristics

**Pass/Fail**: Fail if latency exceeds SLA, rollback strategy is missing, or serialization format is unsafe.

---

## Step 6: Generate Report

- Write the full model review report to `{output_folder}/ml-expert/model-review.md`
- Summarize findings with severity ratings (`[CRITICAL]` / `[WARNING]` / `[INFO]`)
- List blocking issues that must be resolved before deployment
- Provide optimization recommendations with expected impact
- Document approved architecture decisions for future reference
- Include pass/fail verdict for each step in a summary table
- `[CRITICAL]` Report must include explicit pass/fail verdict for each step

---

## Step 7: Present Results

- Present the report to the requesting agent or user
- Highlight all `[CRITICAL]` findings first, then `[WARNING]`, then `[INFO]`
- Summarize overall deployment readiness: **Ready** / **Conditional** / **Not Ready**
- Recommend next steps: approve deployment, revise architecture, or address blocking issues
- If any step received a Fail verdict, the overall workflow result is **Fail**

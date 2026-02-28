# CI/CD Pipeline Design

Design and review CI/CD pipeline configuration for the {project_name} monorepo.

---

## Step 1: Inventory Build Targets

- Identify all workspaces: `packages/frontend`, `packages/tutorial-system`, `backend/`.
- Note language runtimes: Node.js + TypeScript (frontend), Python + FastAPI (backend).
- Catalog existing scripts in root `package.json` and each workspace `package.json`.
- Check `packages/frontend/package.json` for workspace dependency on `tutorial-system`.
- [CRITICAL] Every workspace must have a defined `build` and `test` script — fail if missing.
- [INFO] Record the Node.js and Python version constraints from `.nvmrc`, `package.json#engines`, and `backend/pyproject.toml` or `requirements.txt`.

---

## Step 2: Define Lint Stage

- Frontend: ESLint + TypeScript type-check (`tsc --noEmit`) in `packages/frontend/`.
- Backend: `ruff` or `flake8` for Python linting; `mypy` for type checking against `backend/app/`.
- Run lint jobs in parallel across workspaces.
- [CRITICAL] Lint stage must block merge on failure — no exceptions.
- [WARNING] If any lint config (`eslint.config.*`, `ruff.toml`, `mypy.ini`) is missing, flag as incomplete.
- [INFO] Include `packages/tutorial-system/` in frontend lint scope if it contains TypeScript.

---

## Step 3: Define Test Stage

- Frontend: Vitest unit tests via `packages/frontend/vitest.config.ts`.
- Backend: `pytest` with coverage against `backend/tests/` (unit and integration).
- Ensure test databases or mocks are configured via environment variables in `backend/app/core/config.py`, not hard-coded.
- [CRITICAL] Test coverage must meet minimum threshold (e.g., 70%) — fail the stage if below.
- [WARNING] Flag any test file importing from production `.env` instead of using fixtures or mocks.
- [INFO] Backend integration tests may require a PostgreSQL service container in the pipeline.

---

## Step 4: Define Build Stage

- Frontend: `vite build` producing static assets in `packages/frontend/dist/`.
- Backend: Docker image build using the multi-stage Dockerfile (development, build, production stages).
- [CRITICAL] The `tutorial-system` workspace package must be stripped from `package.json` before `npm install` in Docker — it is not on the npm registry.
- [WARNING] Tag images with both git SHA and semantic version — fail if tagging strategy is undefined.
- [INFO] Verify `packages/frontend/entrypoint.sh` md5 hash logic does not interfere with CI builds (it is a runtime concern, not build-time).

---

## Step 5: Define Deploy Stage

- Propose environment promotion: dev -> staging -> production.
- Use `docker-compose.yml` for dev/staging (frontend port 5175, backend port 8000, PostgreSQL, Redis).
- [CRITICAL] Database migration step (`alembic upgrade head`) must run before backend deploy — fail if missing from pipeline.
- [WARNING] Ensure `CORS_ORIGINS` in `backend/app/core/config.py` is updated per environment before deploy.
- [INFO] Include a health-check step after deploy: `GET /api/health` returns 200 before marking deploy as successful.

---

## Step 6: Pipeline Triggers

- PR opened/updated: lint + test stages only.
- Merge to `main`: lint + test + build + deploy to staging.
- Tag push (`v*`): full pipeline + deploy to production.
- [CRITICAL] Production deploy must require manual approval gate — fail if auto-deploy to prod is configured.
- [WARNING] Ensure branch protection rules enforce required status checks before merge.

---

## Step 7: Caching Strategy

- Cache `node_modules` by hash of root `package-lock.json`.
- Cache Python virtualenv by hash of `backend/requirements.txt`.
- Cache Docker layers with registry-backed cache (`--cache-from`).
- [WARNING] If `package-lock.json` is out of sync with `package.json`, cache will be stale — flag as a risk.
- [INFO] Consider caching Vite's `.vite/` directory for faster rebuilds.

---

## Step 8: Generate Report

Produce the CI/CD pipeline review report:

- Write output to `{output_folder}/devops/cicd-pipeline.md`.
- Include a pipeline YAML file (GitHub Actions or chosen CI provider) as a fenced code block.
- Summarize each stage with pass/fail status and any findings.
- Include status badges and notification configuration recommendations.
- List all [CRITICAL] and [WARNING] findings in a summary table at the top.

---

## Step 9: Present Results

- Display the report location: `{output_folder}/devops/cicd-pipeline.md`.
- Highlight any [CRITICAL] findings that block pipeline readiness.
- Summarize [WARNING] items that need near-term remediation.
- List [INFO] items as improvement opportunities.
- Provide a final verdict: **PASS** (no critical findings), **CONDITIONAL PASS** (warnings only), or **FAIL** (critical findings present).

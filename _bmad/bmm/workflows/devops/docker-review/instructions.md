# Docker Configuration Review

Review the Docker setup for correctness, efficiency, and alignment with {project_name} project conventions.

---

## Step 1: Audit Dockerfiles

- Read `Dockerfile` at the project root and any service-specific Dockerfiles (e.g., `packages/frontend/Dockerfile`, `backend/Dockerfile`).
- Verify multi-stage build structure contains the required stages: development, build, production.
- [CRITICAL] The `tutorial-system` workspace package must be stripped from `package.json` before `npm install` runs inside Docker — it is not on the npm registry and will cause build failure.
- [CRITICAL] `node_modules` must be baked into the image via `npm install` in the build stage — fail if a volume mount overrides them at runtime.
- [WARNING] Each stage should use explicit base image tags (e.g., `node:20-alpine`), not `latest` — flag if `latest` is used.
- [INFO] Verify `.dockerignore` is present and excludes `node_modules/`, `.env`, `.git/`, and build artifacts.

---

## Step 2: Review docker-compose.yml

- Load `docker-compose.yml` from the project root.
- Validate service definitions for frontend, backend, PostgreSQL, and Redis.
- Confirm port mappings: frontend on `5175`, backend on `8000`.
- Ensure source-file volume mounts exist for HMR (e.g., `./packages/frontend/src:/app/src`).
- [CRITICAL] `node_modules` must NOT be volume-mounted from the host — they are baked into the image. Fail if `./node_modules:/app/node_modules` or similar is found.
- [WARNING] Verify `depends_on` is configured so backend waits for PostgreSQL and Redis to be healthy before starting.
- [INFO] Check that network configuration isolates services appropriately (e.g., shared `app-network`).

---

## Step 3: Inspect Entrypoint Scripts

- Read `packages/frontend/entrypoint.sh`.
- Confirm the auto-dependency sync logic: md5 hash comparison of `package.json` at build time vs runtime, triggering `npm install` only on mismatch.
- Verify the script stores the build-time hash (e.g., `/app/.package-json-hash`) and compares against the current `package.json`.
- [CRITICAL] The entrypoint must exit gracefully if `npm install` fails during sync — fail if errors are silently swallowed.
- [WARNING] If the entrypoint script lacks executable permissions (`chmod +x`), it will fail at container startup — flag if missing in Dockerfile.
- [INFO] Confirm the script falls through to `exec "$@"` to hand off to the application process.

---

## Step 4: Evaluate Dependency Caching

- Check that `COPY package*.json` layers precede `RUN npm install` to maximize Docker layer caching.
- Verify the backend Dockerfile copies `requirements.txt` (or `pyproject.toml` + `poetry.lock`) before copying application code.
- [CRITICAL] Any workspace dependency only available via npm workspace hoisting must be explicitly declared in `packages/frontend/package.json` — fail if a dependency is missing and would break the Docker build.
- [WARNING] If `COPY . .` appears before dependency install steps, layer caching is defeated — flag for reordering.
- [INFO] Recommend using `--mount=type=cache,target=/root/.npm` for npm cache persistence across builds.

---

## Step 5: Security & Best Practices

- Verify images use a non-root user (`USER node` or `USER appuser`) in production stages.
- Check `.dockerignore` excludes: `node_modules/`, `.env`, `.env.*`, `.git/`, `*.log`, `dist/`, `__pycache__/`.
- [CRITICAL] No secrets or credentials may be embedded in Dockerfiles or `docker-compose.yml` — fail if `ENV SECRET_KEY=...` or similar is found. Secrets must come from `.env` files or runtime injection.
- [WARNING] If the production stage includes development dependencies (`devDependencies`, test frameworks), flag as image bloat and security risk.
- [WARNING] Verify `HEALTHCHECK` instructions are defined for long-running services (backend, frontend).
- [INFO] Recommend pinning `apt-get` / `apk add` package versions for reproducible builds.

---

## Step 6: Backend Docker Configuration

- Verify the backend Dockerfile installs Python dependencies from `backend/requirements.txt`.
- Confirm Alembic migrations can run inside the container (`alembic upgrade head`).
- Check that `backend/app/core/config.py` Pydantic `BaseSettings` reads environment variables correctly from the Docker environment.
- [WARNING] If the backend image includes the full source tree (including `tests/`) in production, flag for exclusion.
- [INFO] Verify uvicorn or gunicorn is configured as the production entrypoint with appropriate worker count.

---

## Step 7: Generate Report

Produce the Docker configuration review report:

- Write output to `{output_folder}/devops/docker-review.md`.
- Summarize issues grouped by severity: [CRITICAL], [WARNING], [INFO].
- Provide concrete fix suggestions with file paths and code snippets for each finding.
- Include a checklist of all checks performed with pass/fail status.

---

## Step 8: Present Results

- Display the report location: `{output_folder}/devops/docker-review.md`.
- Highlight any [CRITICAL] findings that block Docker build or runtime correctness.
- Summarize [WARNING] items that degrade security, performance, or reliability.
- List [INFO] items as best-practice improvements.
- Provide a final verdict: **PASS** (no critical findings), **CONDITIONAL PASS** (warnings only), or **FAIL** (critical findings present).

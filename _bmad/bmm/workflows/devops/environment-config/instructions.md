# Environment Variables & Secrets Configuration Review

Audit environment variable usage and secrets management across the {project_name} stack.

---

## Step 1: Catalog Environment Variables

- Read `backend/app/core/config.py` to extract all `Settings` fields defined via Pydantic `BaseSettings`.
- Scan `packages/frontend/src/` for `import.meta.env` references to find all `VITE_*` variables.
- Check `docker-compose.yml` for `environment:` and `env_file:` directives on each service (frontend, backend, PostgreSQL, Redis).
- Inspect `packages/frontend/entrypoint.sh` for any environment variables used in the md5 hash sync logic.
- [CRITICAL] Every variable referenced in application code must have a corresponding definition in config — fail if any are undefined at runtime.
- [INFO] Record default values from `backend/app/core/config.py` field definitions and note which fields are required vs optional.

---

## Step 2: Check for .env Files

- List all `.env`, `.env.*` files across the repo root, `backend/`, and `packages/frontend/`.
- Verify `.env` is listed in both `.gitignore` and `.dockerignore`.
- Confirm `.env.example` or `.env.template` exists at the repo root with placeholder values (no real secrets).
- [CRITICAL] If any `.env` file containing real secrets is tracked by git, flag as an immediate security risk — fail.
- [WARNING] If `.env.example` is missing or stale (does not match current `config.py` fields), flag for update.
- [INFO] Check that `.env.example` includes comments explaining each variable's purpose.

---

## Step 3: Validate Variable Consistency

- Cross-reference variables declared in `backend/app/core/config.py` against those in `docker-compose.yml` and `.env.example`.
- Cross-reference `VITE_*` variables used in `packages/frontend/src/` against `docker-compose.yml` frontend service environment.
- Flag any variable used in code but missing from configuration templates.
- Flag any variable in templates that is unused in code (dead config).
- [CRITICAL] Database connection variables (`DATABASE_URL`, `POSTGRES_*`) must be consistent between `config.py`, `docker-compose.yml`, and `.env.example` — fail on mismatch.
- [WARNING] Redis connection variables must match between backend config and `docker-compose.yml` Redis service.
- [INFO] Document any variables that have different names between frontend (`VITE_*`) and backend representations.

---

## Step 4: Secrets Classification

- Classify each variable as **public config** (ports, feature flags, log levels) vs **secret** (API keys, DB passwords, JWT secrets, encryption keys).
- Check `backend/app/core/config.py` for fields like `SECRET_KEY`, `DATABASE_URL`, `JWT_SECRET`, `ENCRYPTION_KEY`.
- Verify secrets are never committed to the repository — search git history with `git log -p -S <secret_name>` if needed.
- Check for MFA-related secrets in `backend/app/security/providers/` (e.g., TOTP keys, Entra ID client secrets).
- [CRITICAL] Any secret value found in git history or committed `.env` files is a breach — fail and recommend secret rotation.
- [WARNING] If no secrets management approach is defined (environment injection, vault, CI secrets), flag for remediation.
- [INFO] Recommend separating secrets from non-secret config in documentation for onboarding clarity.

---

## Step 5: Per-Environment Configuration

- Confirm distinct configs exist or are documented for development, staging, and production.
- Validate that `DEBUG`, `LOG_LEVEL`, `CORS_ORIGINS` in `backend/app/core/config.py` differ appropriately per environment.
- Ensure database connection strings use different credentials per environment (dev PostgreSQL in `docker-compose.yml` vs production).
- Check that frontend `VITE_API_BASE_URL` points to the correct backend per environment (e.g., `http://localhost:8000` for dev).
- Verify SQLAlchemy `DATABASE_URL` scheme matches the driver expected by the backend (e.g., `postgresql+asyncpg://`).
- [CRITICAL] Production must never use `DEBUG=true` or development database credentials — fail if detected.
- [WARNING] If `CORS_ORIGINS` allows `*` in any non-development environment, flag as a security risk.
- [INFO] Recommend environment-specific `.env.{environment}` files or CI variable groups for clean separation.

---

## Step 6: Generate Report

Produce the environment configuration audit report:

- Write output to `{output_folder}/devops/environment-config.md`.
- List all variables in a table with columns: Name, Source File, Classification (public/secret), Environments, Status (ok/missing/stale).
- Separate frontend (`VITE_*`) and backend variables into distinct sections for clarity.
- Flag all misconfigurations and missing variables with severity markers.
- Provide remediation steps for each finding, referencing specific file paths.
- Include a count summary: total variables, secrets count, findings by severity.

---

## Step 7: Present Results

- Display the report location: `{output_folder}/devops/environment-config.md`.
- Highlight any [CRITICAL] findings that require immediate action (exposed secrets, missing required vars).
- Summarize [WARNING] items that need near-term remediation (stale templates, missing consistency).
- List [INFO] items as documentation and process improvements.
- Provide a final verdict: **PASS** (no critical findings), **CONDITIONAL PASS** (warnings only), or **FAIL** (critical findings present).

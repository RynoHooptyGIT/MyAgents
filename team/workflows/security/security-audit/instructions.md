# Security Audit - Comprehensive Review

## Purpose
Perform a full-spectrum security review of the {project_name} application covering authentication, authorization, data isolation, injection prevention, cross-origin policies, and audit trails.

---

## Step 1: Authentication Middleware Review
- [CRITICAL] Inspect all FastAPI dependency injections for authentication (`Depends(get_current_user)`) in `backend/app/routers/*.py`.
- [CRITICAL] Verify every protected route requires authentication; flag any unprotected endpoints that should be guarded.
- [WARNING] Check that authentication middleware in `backend/app/security/` runs before any business logic or database access.
- [INFO] Verify authentication is enforced consistently across all router files, not just selectively.
- **Pass**: All non-public endpoints require auth. **Fail**: Any sensitive endpoint missing `Depends(get_current_user)`.

---

## Step 2: JWT Handling
- [CRITICAL] Verify JWT secret is loaded from environment variables in `backend/app/core/config.py`, never hardcoded.
- [CRITICAL] Confirm token expiration (`exp` claim) is set and enforced in `backend/app/security/`.
- [CRITICAL] Check for proper signature algorithm specification (reject `none` algorithm).
- [WARNING] Validate refresh token rotation and revocation mechanisms in `backend/app/routers/auth.py`.
- [WARNING] Ensure tokens are not logged or exposed in error responses across `backend/app/`.
- **Pass**: Secrets from env; expiration enforced; algorithm pinned. **Fail**: Hardcoded secret or missing expiration.

---

## Step 3: Tenant Isolation
- [CRITICAL] Confirm `tenant_id` is derived from the authenticated user's token in `backend/app/security/`, never from request body or query params.
- [CRITICAL] Verify all database queries in `backend/app/services/*.py` filter by `tenant_id`.
- [CRITICAL] Check that cross-tenant data access is impossible through API parameter manipulation in `backend/app/routers/*.py`.
- [WARNING] Validate that admin/superuser endpoints have explicit tenant scoping.
- **Pass**: tenant_id always from JWT; all queries scoped. **Fail**: Any query missing tenant filter or tenant_id from request.

---

## Step 4: SQL Injection Prevention
- [CRITICAL] Verify all database queries in `backend/app/services/*.py` and `backend/app/routers/*.py` use parameterized queries or SQLAlchemy ORM methods.
- [CRITICAL] Search for raw SQL string concatenation or f-string query construction across `backend/app/`.
- [WARNING] Check any dynamic query builders in `backend/app/services/*.py` for proper input sanitization.
- [INFO] Validate that user input is never interpolated directly into SQL — check Alembic migrations in `backend/alembic/versions/` for raw SQL patterns.
- **Pass**: All queries use ORM or parameterized statements. **Fail**: Any raw SQL with string interpolation.

---

## Step 5: CORS Configuration
- [CRITICAL] Review `CORSMiddleware` settings in `backend/app/main.py`.
- [CRITICAL] Verify `allow_origins` is not set to `["*"]` in production configuration.
- [WARNING] Check that `allow_credentials` is properly paired with explicit origins (not wildcards).
- [INFO] Validate `allow_methods` and `allow_headers` are appropriately restrictive.
- **Pass**: Explicit origin allowlist; credentials not paired with wildcard. **Fail**: Wildcard origins with credentials enabled.

---

## Step 6: Audit Logging
- [CRITICAL] Verify sensitive operations (create, update, delete) generate audit log entries in `backend/app/services/*.py`.
- [WARNING] Check that audit logs include: timestamp, user_id, tenant_id, action, resource, and outcome in `backend/app/models/audit_log.py`.
- [WARNING] Confirm audit logs are tamper-resistant — no delete endpoints for audit records in `backend/app/routers/*.py`.
- [INFO] Validate that PII is not over-logged in audit trails.
- **Pass**: All mutations logged with full context; no delete endpoint. **Fail**: Missing audit entries for sensitive operations.

---

## Step 7: Frontend Security Review
- [WARNING] Check for XSS vulnerabilities — search for unsafe raw HTML rendering patterns in `packages/frontend/src/**/*.tsx` and verify sanitization with DOMPurify or equivalent.
- [WARNING] Verify sensitive data (tokens, keys) is not stored in localStorage in `packages/frontend/src/features/auth/`.
- [WARNING] Check that API base URL uses HTTPS in `packages/frontend/src/features/auth/services/authApi.ts` and other service files.
- [INFO] Verify Content Security Policy headers are configured in the build or reverse proxy.
- **Pass**: No raw HTML injection; tokens in secure storage. **Fail**: XSS vectors or tokens in localStorage without protection.

---

## Step 8: Secrets and Configuration Review
- [CRITICAL] Scan for hardcoded secrets, API keys, or passwords across the entire codebase.
- [CRITICAL] Verify `.env` files are listed in `.gitignore` and not present in version control.
- [WARNING] Check `docker-compose.yml` for secrets passed as plain environment variables vs. Docker secrets.
- [INFO] Verify `backend/app/core/config.py` uses Pydantic Settings with proper validation for all secret fields.
- **Pass**: No secrets in source; env-based config validated. **Fail**: Any hardcoded credential or committed .env file.

---

## Step 9: Generate Report
- Compile all findings into `{output_folder}/security-auditor/security-audit.md`.
- Classify each finding as: **CRITICAL** (immediate remediation), **HIGH** (before next release), **MEDIUM** (near-term fix), **LOW** (hardening recommendation), or **PASS** (meets requirements).
- For each finding include: location (file:line), description, risk assessment, and recommended fix with code example.
- Calculate overall audit result: **FAIL** if any CRITICAL finding, **WARN** if HIGH/MEDIUM only, **PASS** if all checks pass.

---

## Step 10: Present Results
- Display the findings summary table to the user, grouped by severity.
- Highlight all CRITICAL findings first with specific file locations and remediation steps.
- Provide a prioritized remediation roadmap with estimated effort.
- State overall audit verdict and whether the application is cleared for production deployment.

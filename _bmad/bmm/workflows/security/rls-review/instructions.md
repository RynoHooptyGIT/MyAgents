# Row-Level Security (RLS) Policy Validation

## Purpose
Validate that multi-tenant Row-Level Security is correctly and completely applied across all database tables, with no bypass vectors that could allow cross-tenant data access.

---

## Step 1: Inventory All Tables
- [CRITICAL] Scan all SQLAlchemy models in `backend/app/models/*.py` and list every table.
- [CRITICAL] Note which models have a `tenant_id` column — check each model class for the column definition.
- [CRITICAL] Flag any table that stores tenant-scoped data but lacks a `tenant_id` column.
- [INFO] Document shared/global tables (e.g., lookup tables, system config) that intentionally lack `tenant_id` with justification.
- [INFO] Check `backend/app/models/__init__.py` for the complete model registry to ensure no models are missed.
- **Pass**: All tenant-scoped tables have `tenant_id`. **Fail**: Any tenant data table missing the column.

---

## Step 2: Verify apply_multi_tenant_rls() Coverage
- [CRITICAL] Locate the `apply_multi_tenant_rls()` function definition in `backend/app/models/` or `backend/alembic/`.
- [CRITICAL] Check every Alembic migration in `backend/alembic/versions/` for RLS application — each table with `tenant_id` must have a corresponding `apply_multi_tenant_rls()` call.
- [CRITICAL] Verify the RLS policy enforces `tenant_id = current_setting('app.current_tenant')` or equivalent.
- [CRITICAL] Check that RLS is enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) for each table.
- [WARNING] Verify `FORCE ROW LEVEL SECURITY` is set for table owners to prevent owner bypass.
- [INFO] Confirm the RLS policy name follows a consistent naming convention across all tables.
- **Pass**: RLS applied and forced on all tenant tables. **Fail**: Any tenant table missing RLS policy or FORCE RLS.

---

## Step 3: Check Bypass Vectors
- [CRITICAL] **Superuser bypass**: Verify the application database user defined in `backend/app/core/config.py` (DATABASE_URL) is NOT a PostgreSQL superuser.
- [CRITICAL] **BYPASSRLS role**: Confirm no application role has `BYPASSRLS` privilege — check migration scripts in `backend/alembic/versions/` for role definitions.
- [CRITICAL] **Direct SQL access**: Search for any raw SQL queries in `backend/app/services/*.py` and `backend/app/routers/*.py` that might bypass ORM-level tenant filtering.
- [WARNING] **Bulk operations**: Verify bulk insert/update/delete operations in `backend/app/services/*.py` respect RLS.
- [WARNING] **Foreign key traversal**: Check that JOINs across tables in `backend/app/services/*.py` cannot leak data from other tenants.
- [WARNING] **Subquery leaks**: Verify subqueries in ORM operations are tenant-scoped.
- [WARNING] **Migration scripts**: Ensure migrations in `backend/alembic/versions/` do not inadvertently disable or drop RLS policies.
- [INFO] **View definitions**: Check for any database views that might not inherit RLS from their base tables.
- **Pass**: No bypass vectors found. **Fail**: Any superuser usage, BYPASSRLS role, or raw SQL bypass.

---

## Step 4: Validate Application-Level Enforcement
- [CRITICAL] Verify that `tenant_id` is set in the database session context before every query — check middleware or dependency injection in `backend/app/security/` or `backend/app/core/database.py`.
- [CRITICAL] Check that the session context is set from the authenticated user's JWT, not from request parameters — trace the flow from `backend/app/routers/*.py` through to query execution.
- [WARNING] Confirm that API endpoints in `backend/app/routers/*.py` do not accept `tenant_id` as a filter parameter that overrides the session context.
- [WARNING] Verify that background jobs and async tasks in `backend/app/services/*.py` or `backend/app/agents/*.py` also set tenant context before database access.
- [WARNING] Check that error handling paths do not inadvertently clear or reset the tenant context mid-request.
- **Pass**: Tenant context always from JWT; set before all queries. **Fail**: Missing context setting or tenant_id from request params.

---

## Step 5: Review New and Untracked Models
- [WARNING] Cross-reference the model inventory from Step 1 against RLS migrations in `backend/alembic/versions/`.
- [WARNING] Identify any recently added models in `backend/app/models/*.py` that may not yet have RLS applied.
- [INFO] Check for any staging/temporary tables that might lack RLS.
- [INFO] Verify that any new model added after the last RLS migration has a tracked issue or migration planned.
- **Pass**: All models accounted for in RLS migrations. **Fail**: Any model missing from RLS migration coverage.

---

## Step 6: Verify Test Coverage
- [WARNING] Check that `backend/tests/` includes tests validating RLS enforcement — e.g., tests that attempt cross-tenant access and assert denial.
- [WARNING] Verify integration tests in `backend/tests/integration/` confirm tenant isolation under realistic query patterns.
- [INFO] Check that new model additions require corresponding RLS test cases.
- [INFO] Confirm test fixtures create multiple tenants to validate isolation boundaries.
- **Pass**: RLS tests exist and cover all tenant-scoped tables. **Fail**: No cross-tenant access tests or incomplete coverage.

---

## Step 7: Generate Report
- Compile all findings into `{output_folder}/security-auditor/rls-review.md`.
- Include a coverage matrix table:

| Table | has tenant_id | RLS Policy | Force RLS | Bypass Risk | Status |
|-------|--------------|------------|-----------|-------------|--------|

- Calculate RLS coverage score: (tables with complete RLS / total tenant-scoped tables) x 100.
- Overall result: **PASS** at 100% coverage with no bypass vectors, **WARN** at 90-99%, **FAIL** below 90% or any bypass vector found.

---

## Step 8: Present Results
- Display the coverage matrix to the user.
- Highlight any tables missing RLS or with bypass risks as CRITICAL findings.
- List all bypass vectors found with specific file:line references and remediation steps.
- State the RLS coverage score and overall pass/fail verdict.
- Provide migration script templates for any tables needing RLS application.
- If any CRITICAL bypass vectors exist, flag the review as blocking for production deployment.

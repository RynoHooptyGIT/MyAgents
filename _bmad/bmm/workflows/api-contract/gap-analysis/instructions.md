# Full API Gap Analysis

Audit the API for missing capabilities: pagination, error handling, versioning, and standards compliance.

## Step 1: Pagination Audit

- Identify all list/collection endpoints in `backend/openapi/openapi.json` (responses returning arrays).
- Check each for pagination support: `skip`/`offset`, `limit`, `total` count in response.
- Verify the frontend consumes pagination parameters in `packages/frontend/src/features/*/services/`.
- Flag endpoints returning unbounded arrays without pagination.
- **Pass**: All collection endpoints support `skip`, `limit`, and return `total`. Frontend passes params.
- **Fail**: Any collection endpoint returns an unbounded array with no pagination support.
- `[CRITICAL]` Unbounded list endpoint with no pagination (data volume risk).
- `[WARNING]` Pagination params accepted but `total` count missing from response.

---

## Step 2: Error Response Audit

- Check that every endpoint defines error responses (400, 401, 403, 404, 422, 500) in the OpenAPI spec.
- Verify backend routers in `backend/app/routers/` raise `HTTPException` with consistent error schemas.
- Confirm the frontend handles error responses (check for try/catch, error state management).
- Validate a consistent error response shape: `{ detail: string }` or structured error object.
- **Pass**: All endpoints declare error responses; backend and frontend handle them consistently.
- **Fail**: Endpoint missing error response definitions, or inconsistent error shapes.
- `[CRITICAL]` Endpoint with no error handling — unhandled 500s leak stack traces.
- `[WARNING]` Inconsistent error shape across endpoints (some `detail`, some `message`).

---

## Step 3: Versioning Compliance

- Check the OpenAPI spec `info.version` field.
- Verify versioned spec snapshots exist under `backend/openapi/v0.1.0/` and match the current state or document breaking changes.
- Confirm URL path versioning (`/api/v1/`) is applied consistently across all routes.
- **Pass**: Version field set, snapshot exists, all routes use `/api/v1/` prefix.
- **Fail**: Missing version snapshots or routes without version prefix.
- `[WARNING]` Routes missing `/api/v1/` prefix — breaks future multi-version support.
- `[INFO]` Version snapshot exists but has not been updated since last breaking change.

---

## Step 4: Authentication & Authorization

- Verify all non-public endpoints declare security requirements in the OpenAPI spec.
- Check that backend routes in `backend/app/routers/` use dependency injection for auth (`Depends(get_current_user)` or similar).
- Confirm `tenant_id` scoping is enforced on all tenant-specific queries in `backend/app/services/`.
- Flag endpoints missing auth that should require it.
- **Pass**: Every protected endpoint has a security declaration and backend auth dependency.
- **Fail**: Endpoint accessible without authentication or missing tenant scoping.
- `[CRITICAL]` Endpoint missing auth dependency — unauthenticated access possible.
- `[CRITICAL]` Query missing `tenant_id` filter — cross-tenant data leak risk.

---

## Step 5: Request Validation

- Confirm all POST/PUT/PATCH endpoints define request body schemas in `backend/app/schemas/`.
- Check that path and query parameters have type constraints and validation.
- Verify the backend uses Pydantic v2 models (not raw dicts) for request parsing.
- **Pass**: All mutating endpoints use typed Pydantic schemas with field validation.
- **Fail**: Raw dict parsing or missing schema for a mutating endpoint.
- `[CRITICAL]` Endpoint accepts raw dict — no input validation, injection risk.
- `[WARNING]` Path parameter lacks type constraint (e.g., `str` instead of `UUID`).

---

## Step 6: Response Consistency

- Verify all endpoints declare `response_model` in FastAPI route decorators in `backend/app/routers/`.
- Check for consistent envelope patterns (direct data vs wrapped responses).
- Confirm datetime fields use ISO 8601 format consistently across `backend/app/schemas/`.
- **Pass**: All routes declare `response_model`; envelope and datetime formats are consistent.
- **Fail**: Missing `response_model` or mixed envelope patterns.
- `[WARNING]` Route missing `response_model` — response shape not enforced.
- `[INFO]` Inconsistent datetime format (some epoch, some ISO 8601).

---

## Step 7: Missing Endpoints

- Compare CRUD operations per entity in `backend/app/models/`: does every entity have create, read, list, update, delete?
- Identify entities with partial CRUD coverage and flag the gaps.
- Check for bulk operation endpoints where needed (batch create, batch delete).
- **Pass**: All entities have complete CRUD or documented reason for omission.
- **Fail**: Entity missing expected CRUD operations with no justification.
- `[WARNING]` Entity with partial CRUD — missing operations may block frontend features.
- `[INFO]` No bulk endpoints for entity with expected high-volume operations.

---

## Step 8: Generate Report

- Save the full gap analysis report to `{output_folder}/api-contract/gap-analysis.md`.
- Produce a gap matrix: Entity x Capability (pagination, errors, auth, CRUD completeness).
- Rank gaps by severity using markers: `[CRITICAL]`, `[WARNING]`, `[INFO]`.
- Include a summary count: total critical, total warnings, total info findings.
- Provide actionable recommendations with exact file paths for each fix.

---

## Step 9: Present Results

- Display the summary count of findings by severity.
- List all `[CRITICAL]` findings first with file paths and recommended remediation.
- List `[WARNING]` findings grouped by category (pagination, auth, validation, etc.).
- List `[INFO]` findings as improvement suggestions.
- State overall pass/fail: **FAIL** if any `[CRITICAL]` finding exists, otherwise **PASS**.

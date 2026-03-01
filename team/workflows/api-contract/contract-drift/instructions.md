# Contract Drift Detection

Detect mismatches between the OpenAPI specification, backend route implementations, and frontend API service calls.

## Step 1: Parse the OpenAPI Spec

- Load `backend/openapi/openapi.json` (provided via input_file_patterns).
- Extract every endpoint: method, path, request body schema, response schemas, status codes.
- Note the spec version from `backend/openapi/openapi.yaml` for cross-reference.
- `[INFO]` Record total endpoint count and spec version for the report header.
- **Pass**: OpenAPI spec parses without error; all endpoints extracted.
- **Fail**: Spec is malformed or missing required fields.

---

## Step 2: Extract Backend Router Endpoints

- Scan all Python files under `backend/app/routers/` for FastAPI route decorators (`@router.get`, `@router.post`, `@router.put`, `@router.patch`, `@router.delete`).
- For each route, record: HTTP method, path, path parameters, query parameters, request body type (from `backend/app/schemas/`), response model, and status code.
- Include any `prefix` defined on the `APIRouter` instance.
- Check `backend/app/core/config.py` for the global API prefix to construct full paths.
- `[INFO]` Record total backend route count for comparison.
- **Pass**: All route decorators parsed with complete metadata.
- **Fail**: Route decorator found but unable to determine full path or schema.

---

## Step 3: Compare Backend vs OpenAPI Spec

- Match each router endpoint to its OpenAPI spec entry by method + full path.
- Flag **spec-only** endpoints (in spec but not in code) — may indicate stale spec entries.
- Flag **code-only** endpoints (in code but not in spec) — spec needs regeneration.
- Flag **signature drift**: mismatched request/response schemas, different status codes, missing parameters.
- `[CRITICAL]` Code-only endpoint — clients cannot discover this endpoint from the spec.
- `[CRITICAL]` Signature drift on request body — clients send wrong payload shape.
- `[WARNING]` Spec-only endpoint — dead spec entry, no backend implementation.
- `[WARNING]` Status code mismatch between spec and implementation.
- **Pass**: Every backend route has a matching spec entry with identical signature.
- **Fail**: Any code-only endpoint or signature drift detected.

---

## Step 4: Extract Frontend API Service Calls

- Scan `packages/frontend/src/features/*/services/` for HTTP calls (axios, fetch, or API client wrappers).
- Record each call: method, URL path, request payload shape, expected response type.
- Check `packages/frontend/src/features/auth/services/authApi.ts` and other service files for base URL configuration.
- `[INFO]` Record total frontend API call count for comparison.
- **Pass**: All service calls inventoried with method, path, and type information.
- **Fail**: Service file contains HTTP calls that cannot be mapped to a path.

---

## Step 5: Compare Frontend vs OpenAPI Spec

- Match each frontend service call to its OpenAPI spec entry by method + path.
- Flag endpoints the frontend calls that do not exist in the spec.
- Flag spec endpoints that have no corresponding frontend service call (potential unused endpoints).
- Flag request/response shape mismatches by comparing frontend TypeScript types against OpenAPI `components/schemas`.
- `[CRITICAL]` Frontend calls endpoint not in spec — will break if spec is used for code generation.
- `[CRITICAL]` Request payload shape mismatch — frontend sends fields the backend does not expect.
- `[WARNING]` Spec endpoint with no frontend consumer — may be unused or planned for future use.
- `[WARNING]` Response type mismatch — frontend expects fields not in the spec response.
- **Pass**: Every frontend call matches a spec entry with compatible shapes.
- **Fail**: Any frontend call targets a missing or mismatched spec entry.

---

## Step 6: Scoring

- Assign a drift score: start at 100, deduct per finding.
- Deductions: `-15` per `[CRITICAL]`, `-7` per `[WARNING]`, `-2` per `[INFO]`.
- Calculate sub-scores: backend-to-spec drift, frontend-to-spec drift, frontend-to-backend transitive drift.
- **PASS threshold**: Overall score >= 80% with zero `[CRITICAL]` findings.
- **FAIL threshold**: Any `[CRITICAL]` finding or overall score < 80%.

---

## Step 7: Generate Report

- Save the full drift report to `{output_folder}/api-contract/contract-drift.md`.
- Produce a drift report grouped by:
  - Backend-to-spec drift (routes in `backend/app/routers/` vs `backend/openapi/openapi.json`)
  - Frontend-to-spec drift (services in `packages/frontend/src/features/*/services/` vs spec)
  - Frontend-to-backend drift (transitive mismatches)
- Include severity markers (`[CRITICAL]`, `[WARNING]`, `[INFO]`) on every finding.
- Include sub-scores and overall drift score.
- Include a summary count: total critical, total warnings, total info findings.

---

## Step 8: Present Results

- Display the overall drift score and sub-scores.
- List all `[CRITICAL]` findings first with exact file paths and line references where possible.
- List `[WARNING]` findings grouped by drift category.
- List `[INFO]` findings as observations.
- State overall pass/fail verdict based on the scoring threshold.
- Recommend next steps: regenerate OpenAPI spec, update frontend types, or fix backend routes.

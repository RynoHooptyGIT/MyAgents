# Schema Comparison: Pydantic vs TypeScript

Compare backend Pydantic schemas with frontend TypeScript types and Zod validators to find structural mismatches.

## Step 1: Inventory Backend Schemas

- Read all files in `backend/app/schemas/`.
- For each Pydantic v2 model, extract: class name, field names, field types, optional/required status, default values, validators.
- Note inheritance chains (e.g., `ToolBase` -> `ToolCreate` -> `ToolResponse`).
- `[INFO]` Record total schema count and inheritance depth for reference.
- **Pass**: All schemas inventoried with complete field metadata.
- **Fail**: Unable to parse a schema file or missing field metadata.

---

## Step 2: Inventory Frontend Types

- Scan `packages/frontend/src/features/*/` for TypeScript interfaces, types, and Zod schemas.
- Look for files named `types.ts`, `schemas.ts`, `*.types.ts`, `*.schema.ts`.
- Check `packages/frontend/src/features/*/services/` for inline response types.
- For each type/interface, extract: name, field names, field types, optional markers.
- `[INFO]` Record total frontend type count and note any Zod schemas found.
- **Pass**: All frontend types inventoried with complete field metadata.
- **Fail**: Frontend feature directory has API calls but no corresponding type definitions.

---

## Step 3: Build a Mapping

- Match backend schemas to frontend types by name convention (e.g., `AIToolResponse` <-> `AiTool`).
- Use the OpenAPI spec (`backend/openapi/openapi.json`) `components/schemas` as the canonical bridge.
- Record unmatched schemas on either side.
- `[CRITICAL]` Backend schema used in a route response but has no frontend type counterpart.
- `[WARNING]` Frontend type exists with no matching backend schema — possible stale type.
- **Pass**: Every actively used backend response schema maps to a frontend type.
- **Fail**: One or more response schemas have no frontend mapping.

---

## Step 4: Field-Level Comparison

For each matched pair, compare:

- **Field presence**: fields in backend but missing in frontend, and vice versa.
- **Type compatibility**: `str` <-> `string`, `int` <-> `number`, `Optional[X]` <-> `X | undefined`, `list[X]` <-> `X[]`, `datetime` <-> `string` (ISO format), `UUID` <-> `string`.
- **Nullability**: `Optional` on backend must correspond to `| null` or `| undefined` on frontend.
- **Enums**: Pydantic enums in `backend/app/schemas/` must match TypeScript string unions or enum declarations.
- **Nested objects**: Recursively compare nested schema references.
- **Tenant fields**: Verify `tenant_id` handling — backend may include it but frontend may omit it from request types.
- `[CRITICAL]` Required field on backend missing from frontend type — runtime deserialization failure.
- `[CRITICAL]` Type incompatibility that causes silent data loss (e.g., `number` vs `string`).
- `[WARNING]` Nullability mismatch — `Optional` on backend but required on frontend.
- `[INFO]` Extra field on frontend not present on backend (may be a UI-only field).
- **Pass**: All fields match in name, type, and nullability.
- **Fail**: Any field-level mismatch that would cause a runtime error.

---

## Step 5: Validate Against OpenAPI

- Confirm that OpenAPI `components/schemas` entries in `backend/openapi/openapi.json` match the Pydantic models in `backend/app/schemas/`.
- Confirm that frontend types in `packages/frontend/src/features/*/types/` align with those same OpenAPI definitions.
- Flag three-way mismatches (backend schema vs OpenAPI vs frontend type).
- `[CRITICAL]` Three-way mismatch — all three layers disagree on a field definition.
- `[WARNING]` OpenAPI spec stale — does not reflect current Pydantic model.
- **Pass**: OpenAPI spec is consistent bridge between backend and frontend.
- **Fail**: OpenAPI spec diverges from either backend or frontend.

---

## Step 6: Scoring

- Assign a compatibility score per schema pair: 100% = perfect match, deduct per mismatch.
- Deductions: `-20` per `[CRITICAL]`, `-10` per `[WARNING]`, `-2` per `[INFO]`.
- Calculate an overall project schema compatibility score (average across all pairs).
- **PASS threshold**: Overall score >= 80% with zero `[CRITICAL]` findings.
- **FAIL threshold**: Any `[CRITICAL]` finding or overall score < 80%.

---

## Step 7: Generate Report

- Save the full comparison report to `{output_folder}/api-contract/schema-comparison.md`.
- Table format: Backend field | Backend type | Frontend field | Frontend type | Status (match/mismatch/missing).
- Group findings by schema/entity.
- Include per-schema compatibility scores and overall project score.
- Include a summary count: total critical, total warnings, total info findings.

---

## Step 8: Present Results

- Display the overall project schema compatibility score.
- List all `[CRITICAL]` findings first with exact file paths in both `backend/app/schemas/` and `packages/frontend/src/features/*/`.
- List `[WARNING]` findings grouped by schema pair.
- List `[INFO]` findings as improvement suggestions.
- State overall pass/fail verdict based on the scoring threshold.

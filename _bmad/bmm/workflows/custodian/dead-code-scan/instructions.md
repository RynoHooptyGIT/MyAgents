# Dead Code Scan - Custodian Workflow

Finds orphaned and unreferenced code across both the frontend and backend of the {project_name} monorepo.

---

## Step 1: Unreferenced Backend Services

1. List all service classes in `backend/app/services/*.py` (extract class names matching `class *Service`).
2. For each service class, search for references in:
   - `backend/app/routers/*.py` (primary consumers)
   - `backend/app/services/*.py` (service-to-service calls)
   - `backend/tests/**/*.py` (test coverage)
3. Flag any service class that is never imported or instantiated outside its own file.

---

## Step 2: Unreferenced Backend Schemas

1. List all schema classes in `backend/app/schemas/*.py` (extract class names matching `class *`).
2. For each schema class, search for references in:
   - `backend/app/routers/*.py` (request/response types)
   - `backend/app/services/*.py` (internal use)
   - `backend/tests/**/*.py` (test fixtures)
3. Flag any schema class that is never imported outside its own file.
4. Pay special attention to schemas that were part of a feature that may have been removed.

---

## Step 3: Unreferenced Backend Routers

1. List all router files in `backend/app/routers/*.py`.
2. Verify each is imported in `backend/app/main.py` via `include_router`.
3. For routers that ARE registered, check if any of their endpoints are commented out or contain only `pass` stubs.
4. Flag router files that exist but are not registered in `main.py`.

---

## Step 4: Orphaned Backend Models

1. List all model files in `backend/app/models/` (excluding `__init__.py`, `base.py`).
2. For each model file, verify:
   - It is imported in `backend/app/models/__init__.py`.
   - At least one service in `backend/app/services/` references the model class.
   - At least one migration in `backend/alembic/versions/` creates or alters the corresponding table.
3. Flag models that are registered but never used by any service (dead-registered models).

---

## Step 5: Unreferenced Frontend Components

1. List all `.tsx` component files in `packages/frontend/src/features/` and `packages/frontend/src/components/`.
2. For each component file, extract the default export or named exports.
3. Search for import references to that component across all `.tsx` and `.ts` files.
4. Flag any component that is never imported anywhere (orphaned component).
5. Check `packages/frontend/src/App.tsx` route definitions for routes pointing to components that no longer exist.

---

## Step 6: Unreferenced Frontend Hooks and Utilities

1. List all custom hooks (`use*.ts` or `use*.tsx`) in `packages/frontend/src/`.
2. For each hook, search for import references across the frontend codebase.
3. Flag hooks that are never imported.
4. Repeat for utility files in any `utils/` or `helpers/` directories.

---

## Step 7: Stale Test Files

1. List all test files in `backend/tests/`.
2. For each test file, identify the module it is testing (from import statements or naming convention like `test_<module>.py`).
3. Flag test files whose target module no longer exists.
4. Similarly, check `packages/frontend/src/**/*.test.tsx` for tests referencing deleted components.

---

## Step 8: Produce Report

Output a structured report to `{output_folder}/custodian/dead-code-scan.md` with:

1. **Backend Dead Code**
   - Unreferenced services (with file paths)
   - Unreferenced schemas (with file paths)
   - Unregistered routers (with file paths)
   - Orphaned models (with file paths)
2. **Frontend Dead Code**
   - Orphaned components (with file paths)
   - Unused hooks and utilities (with file paths)
3. **Stale Tests** - test files whose targets no longer exist
4. **Summary Statistics**
   - Total dead code files found
   - Estimated lines of dead code (sum line counts of flagged files)
   - Breakdown by category
5. **Recommended Actions**
   - Files safe to delete (no references anywhere)
   - Files needing investigation (partial references, may be in-progress features)

Use severity markers: `[SAFE TO REMOVE]` for confirmed orphans, `[INVESTIGATE]` for partially referenced code, `[INFO]` for stale tests.

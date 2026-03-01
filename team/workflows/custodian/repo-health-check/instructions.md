# Repo Health Check - Custodian Workflow

Full repository health scan for the {project_name} monorepo. Counts files, checks registrations, finds duplicates, and verifies structural integrity.

---

## Step 1: File Inventory

Count and report files by category:

| Category | Glob Pattern | Location |
|----------|-------------|----------|
| Backend models | `backend/app/models/*.py` | `backend/app/models/` |
| Backend routers | `backend/app/routers/*.py` | `backend/app/routers/` |
| Backend services | `backend/app/services/*.py` | `backend/app/services/` |
| Backend schemas | `backend/app/schemas/*.py` | `backend/app/schemas/` |
| Alembic migrations | `backend/alembic/versions/*.py` | `backend/alembic/versions/` |
| Frontend features | directories in `packages/frontend/src/features/` | count subdirectories |
| Frontend components | `packages/frontend/src/**/*.tsx` | recursive count |
| Backend tests | `backend/tests/**/*.py` | recursive count |

Exclude `__init__.py`, `__pycache__`, and `base.py` from model counts where appropriate.

Produce a summary table with counts.

---

## Step 2: Model Registration Check

Every model file in `backend/app/models/` (excluding `__init__.py` and `base.py`) must be imported in `backend/app/models/__init__.py`.

1. List all `.py` files in `backend/app/models/` (excluding `__init__.py`, `base.py`).
2. For each file, verify that at least one class from that file appears as an import in `backend/app/models/__init__.py`.
3. Report any **unregistered models** (files present but not imported).
4. Report any **stale imports** (imports referencing files that no longer exist).

---

## Step 3: Router Registration Check

Every router file in `backend/app/routers/` must be included via `app.include_router()` in `backend/app/main.py`.

1. List all `.py` files in `backend/app/routers/` (excluding `__init__.py`).
2. For each file, check that `backend/app/main.py` contains a corresponding `include_router` call (search for the router module name).
3. Report any **unregistered routers** not wired into the app.
4. Report any **stale router includes** referencing files that no longer exist.

---

## Step 4: Duplicate File Detection

Scan for potential duplicate or conflicting files:

1. **Duplicate migration numbers**: Check `backend/alembic/versions/` for files sharing the same numeric prefix (e.g., two files starting with `081_`).
2. **Duplicate model class names**: Grep all model files for `class <Name>(` and check for duplicate class names across different files.
3. **Duplicate router prefixes**: Search `backend/app/main.py` for `prefix=` arguments and flag any duplicates.

---

## Step 5: Structure Verification

Verify the expected project structure exists:

```
backend/
  app/
    agents/
    core/
    middleware/
    models/
    routers/
    schemas/
    services/
    main.py
  alembic/
    versions/
  tests/
  requirements.txt
packages/
  frontend/
    src/
      features/
    package.json
  tutorial-system/
    package.json
```

Report any **missing directories** from the expected structure.

---

## Step 6: Produce Report

Output a structured report to `{output_folder}/custodian/repo-health-check.md` with:

1. **File Inventory Table** - counts by category
2. **Registration Status** - models and routers with PASS/FAIL per item
3. **Duplicates Found** - any duplicate migrations, classes, or prefixes
4. **Structure Verification** - missing directories or unexpected layout
5. **Overall Health Score** - percentage of checks passing
6. **Action Items** - numbered list of issues requiring attention, sorted by severity

Use severity markers: `[CRITICAL]` for missing registrations, `[WARNING]` for duplicates, `[INFO]` for structural notes.

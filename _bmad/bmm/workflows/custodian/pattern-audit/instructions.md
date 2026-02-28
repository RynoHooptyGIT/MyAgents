# Pattern Audit - Custodian Workflow

Checks codebase compliance against the rules defined in `project-context.md`. Focuses on security-critical patterns, API conventions, and code quality standards.

---

## Step 1: Tenant Isolation Audit

**Rule**: Every database query MUST filter by `tenant_id`.

1. Search all files in `backend/app/services/*.py` for `select(` or `db.execute(` calls.
2. For each query found, verify that `tenant_id` appears in the same statement or within the surrounding 5 lines as a `.where()` filter.
3. Flag any query that selects from a model (not `Tenant` or `BaseModel` themselves) without a `tenant_id` filter.
4. Also check `backend/app/routers/*.py` for any direct `db.execute()` calls that bypass the service layer.

**Exceptions**: Queries against the `Tenant` table itself, health-check endpoints, and superadmin-scoped operations (if clearly annotated).

---

## Step 2: SQL Injection Prevention

**Rule**: No f-string SQL or raw string interpolation in queries.

1. Search `backend/app/` recursively for patterns:
   - `f"SELECT` or `f"INSERT` or `f"UPDATE` or `f"DELETE` (f-string SQL)
   - `f"...WHERE...{` (f-string in WHERE clauses)
   - `.execute(f"` (f-string passed to execute)
   - `text(f"` (f-string passed to SQLAlchemy text())
2. Verify `escape_ilike_pattern()` is used when any `.ilike()` call includes user input.
3. Report each violation with file path and line number.

**Severity**: CRITICAL - any finding here is a potential SQL injection vector.

---

## Step 3: API Endpoint Pattern Check

**Rule**: All protected endpoints must use RBAC dependencies.

1. Search `backend/app/routers/*.py` for all route decorators (`@router.get`, `@router.post`, `@router.put`, `@router.patch`, `@router.delete`).
2. For each endpoint function, verify one of these dependency patterns is present:
   - `Depends(get_current_user)`
   - `Depends(require_any_role(...))`
   - `Depends(require_role(...))`
3. Flag endpoints missing RBAC that are NOT in the health or auth routers.
4. Verify `tenant_id` is extracted from `current_user.tenant_id`, not from request body or path params.

---

## Step 4: Type Hint Compliance

**Rule**: All functions must have type hints on parameters and return values.

1. Search `backend/app/services/*.py` and `backend/app/routers/*.py` for function definitions (`async def` and `def`).
2. Check that each function has:
   - Type annotations on all parameters (excluding `self`)
   - A return type annotation (`-> SomeType`)
3. Report functions missing type hints with file path and function name.

**Exceptions**: `__init__` methods returning `None` implicitly are acceptable.

---

## Step 5: Frontend Pattern Check

1. **React Query usage**: Search `packages/frontend/src/**/*.ts{,x}` for direct `fetch()` or `axios` calls that bypass React Query hooks. Flag any data-fetching not wrapped in `useQuery` or `useMutation`.
2. **No emojis in production code**: Search all `.tsx`, `.ts`, `.py` source files for emoji characters (Unicode ranges U+1F600-U+1F64F, U+1F300-U+1F5FF, U+2600-U+26FF). Flag any occurrences outside of test files and markdown.
3. **Console.log cleanup**: Search frontend source for `console.log(` calls that should be removed before merge. Exclude files in `__tests__/` and `*.test.*`.

---

## Step 6: Model Inheritance Check

**Rule**: All database models must inherit from `BaseModel` (which provides `id`, `tenant_id`, `created_at`, `updated_at`).

1. Search `backend/app/models/*.py` for class definitions.
2. Verify each model class inherits from `BaseModel` (directly or through a chain).
3. Flag any model inheriting directly from SQLAlchemy `Base` or `DeclarativeBase` instead of the project's `BaseModel`.

**Exceptions**: The `BaseModel` class itself, mixin classes, and enum-only modules.

---

## Step 7: Produce Report

Output a structured report to `{output_folder}/custodian/pattern-audit.md` with:

1. **Tenant Isolation** - table of queries with PASS/FAIL status
2. **SQL Injection** - list of violations (should be zero)
3. **RBAC Coverage** - table of endpoints with auth status
4. **Type Hints** - list of non-compliant functions
5. **Frontend Patterns** - findings from React Query, emoji, and console.log checks
6. **Model Inheritance** - list of non-compliant models
7. **Summary** - total violations by severity: CRITICAL / WARNING / INFO
8. **Action Items** - prioritized list of fixes needed

Use severity markers: `[CRITICAL]` for tenant isolation and SQL injection, `[WARNING]` for missing RBAC or type hints, `[INFO]` for frontend cleanup.

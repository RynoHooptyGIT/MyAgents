# Data Model Review - Data Architect Workflow

Review data model design for normalization, multi-tenant isolation, and temporal data handling in {project_name}. Covers all SQLAlchemy models in `backend/app/models/`.

---

## Step 1: Inventory Current Models

1. List all SQLAlchemy models in `backend/app/models/` (exclude `__init__.py`, `base.py`).
2. Map relationships: foreign keys, association tables, polymorphic inheritance chains.
3. Identify models added since last review by checking the Alembic chain (currently at 083).
4. `[WARNING]` Note the known duplicate migration prefixes at 081, 082, 083 that need resolution.
5. Verify every model file is imported in `backend/app/models/__init__.py` — flag unregistered models.

**Pass**: Complete inventory produced; all models registered in `__init__.py`.
**Fail**: Any model file missing from `__init__.py` imports.

---

## Step 2: Validate Normalization

1. Verify 3NF compliance across all models — no transitive dependencies.
2. Identify denormalized fields and document justification (performance, read-heavy patterns).
3. `[WARNING]` Flag redundant data in multiple tables without documented reason.
4. Review JSON/JSONB columns for structured data that should be normalized into separate tables.
5. `[INFO]` Document approved exceptions (e.g., denormalized summary fields for dashboard performance).

**Pass**: All models 3NF compliant or have documented justification. **Fail**: Unjustified transitive dependencies.

---

## Step 3: Audit Multi-Tenant Isolation

1. `[CRITICAL]` Verify every data-bearing model includes `tenant_id` with NOT NULL and FK to `tenants`.
2. `[CRITICAL]` Check that `apply_multi_tenant_rls()` is called in all query paths in `backend/app/services/*.py`.
3. Validate composite unique constraints include `tenant_id` where applicable.
4. Review global/shared tables (e.g., NIST framework definitions) — confirm intentionally tenant-agnostic.
5. `[CRITICAL]` Ensure no model allows cross-tenant access through relationship traversal.

**Pass**: All data-bearing models have tenant_id; all service queries apply RLS.
**Fail**: Any model missing tenant_id or any query path missing `apply_multi_tenant_rls()`.

---

## Step 4: Review Temporal Data Patterns

1. Identify tables with `created_at`, `updated_at`, `deleted_at` columns (expected from `BaseModel`).
2. `[WARNING]` Verify soft-delete patterns use consistent column naming and are filtered in default queries.
3. Check for audit trail / history tracking requirements on sensitive entities.
4. Validate timestamp columns use timezone-aware types: `DateTime(timezone=True)`.
5. `[INFO]` Review temporal query patterns (date ranges, aggregation) for index support.

**Pass**: All timestamps timezone-aware; soft-delete filtering consistent.
**Fail**: Non-timezone-aware DateTime or inconsistent soft-delete behavior.

---

## Step 5: Assess Relationship Design

1. Check FK constraints have appropriate `ON DELETE` behavior (CASCADE, SET NULL, or RESTRICT).
2. Validate cascade settings on SQLAlchemy relationships (`cascade`, `passive_deletes`).
3. `[WARNING]` Confirm `back_populates` is used consistently — flag any legacy `backref` usage.
4. Review many-to-many association tables for proper composite primary keys.
5. `[WARNING]` Flag circular dependencies that could cause migration ordering issues.

**Pass**: All FKs have explicit ON DELETE; relationships use back_populates.
**Fail**: Missing ON DELETE behavior or circular dependency detected.

---

## Step 6: Check Naming Conventions

1. Table names: `snake_case` plural form (e.g., `tools`, `intake_requests`).
2. Column names: `snake_case` (e.g., `tenant_id`, `created_at`).
3. Index names: `ix_{table}_{columns}` pattern (e.g., `ix_tools_tenant_id`).
4. `[INFO]` Constraint names must be explicit — flag auto-generated names.

**Pass**: All names follow conventions; no auto-generated constraint names.
**Fail**: Any table or column violating naming convention.

---

## Step 7: Produce Report

Output to `{output_folder}/data-architect/data-model-review.md` with:

1. **Model Inventory** - table of all models with relationship count and last-modified migration
2. **Normalization Status** - PASS/FAIL per model with notes on approved exceptions
3. **Tenant Isolation** - PASS/FAIL per model for tenant_id presence and RLS coverage
4. **Temporal Patterns** - summary of timestamp and soft-delete consistency
5. **Relationship Design** - FK/cascade issues and circular dependency warnings
6. **Naming Compliance** - non-compliant names with suggested corrections
7. **Findings Summary** - all issues sorted by severity (`[CRITICAL]` > `[WARNING]` > `[INFO]`)
8. **Recommended Changes** - ordered list with Alembic migration steps and backfill estimates

---

## Step 8: Present Results

- State total models reviewed and count of new models since last review.
- Highlight any `[CRITICAL]` findings — tenant isolation gaps or data integrity risks.
- List recommended schema changes with estimated effort (migration + backfill).
- Confirm whether the data model is **APPROVED**, **APPROVED WITH CONDITIONS**, or **NEEDS REVISION**.

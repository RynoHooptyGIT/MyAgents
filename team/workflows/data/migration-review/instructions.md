# Migration Review - Data Architect Workflow

Review database migrations for zero-downtime safety, backfill strategies, and data validation in {project_name}. Targets Alembic files in `backend/alembic/versions/`.

---

## Step 1: Review Migration Chain Integrity

1. Confirm the chain is linear with no orphaned heads — run `alembic heads` and expect exactly one result.
2. Check current head (083) and `[WARNING]` flag the known duplicate prefixes at 081, 082, 083.
3. Verify `down_revision` references are correct for each new migration.
4. Run `alembic check` to detect inconsistencies between models and the migration chain.
5. Validate filenames follow convention: `{number}_{description}.py` with no sequence gaps.

**Pass**: Single head, no orphans, no unresolved duplicate prefixes.
**Fail**: Multiple heads detected or broken `down_revision` chain.

---

## Step 2: Assess Zero-Downtime Safety

Classify every DDL operation by its locking behavior against PostgreSQL.

| Risk Level | Operations | Action Required |
|-----------|-----------|----------------|
| **Safe** | ADD COLUMN (nullable, no default), CREATE INDEX CONCURRENTLY, CREATE TABLE | None |
| **Brief lock** | ADD COLUMN with server default, DROP COLUMN, RENAME COLUMN | Verify table < 100k rows |
| **Dangerous** | ADD COLUMN NOT NULL without default, ALTER COLUMN TYPE, ADD constraint on large table | Maintenance window |

1. `[CRITICAL]` Flag ALTER TABLE on tables > 100k rows without a batched approach.
2. `[CRITICAL]` Flag NOT NULL constraints added without DEFAULT (requires backfill-first).
3. `[WARNING]` Verify CREATE INDEX uses CONCURRENTLY (check `op.create_index` for `postgresql_concurrently=True`).
4. Ensure no migration acquires ACCESS EXCLUSIVE lock for extended periods.

**Pass**: All operations classified; dangerous operations have mitigation plans.
**Fail**: Unclassified dangerous operation or missing CONCURRENTLY on large-table index.

---

## Step 3: Validate Multi-Tenant Columns

1. `[CRITICAL]` Verify new tables include `tenant_id` with NOT NULL and FK to `tenants` table.
2. `[CRITICAL]` Check new indexes include `tenant_id` as the leading column.
3. `[WARNING]` Verify new unique constraints are scoped to `tenant_id` (composite, not standalone).
4. Validate RLS-related setup if using PostgreSQL Row Level Security.
5. Cross-reference against `backend/app/models/` to confirm migration columns match model definitions.

**Pass**: All new data-bearing tables have tenant_id with NOT NULL, FK, and leading index position.
**Fail**: Any new table missing tenant_id or tenant-scoped constraints.

---

## Step 4: Review Backfill Strategy

1. Identify migrations requiring backfill (new NOT NULL columns, computed columns, data transforms).
2. `[CRITICAL]` Verify backfill uses batches (1,000-10,000 rows), not a single UPDATE on entire table.
3. Confirm batch iteration scopes by `tenant_id` to avoid long-running transactions.
4. Validate backfill handles NULL edge cases and is idempotent (safe to re-run).
5. `[WARNING]` Check backfill commits per batch — no single transaction wrapping everything.
6. Estimate total duration; document whether it runs online or requires maintenance window.

**Pass**: All backfills are batched, idempotent, and tenant-scoped with duration estimates.
**Fail**: Single-statement backfill on a table with > 10k rows.

---

## Step 5: Check Data Validation Constraints

1. Confirm new CHECK constraints match validators in `backend/app/schemas/*.py`.
2. `[WARNING]` Verify ENUM types include all values used by application models.
3. Validate default values match SQLAlchemy model defaults in `backend/app/models/*.py`.
4. Check FK references point to correct tables and columns.
5. Ensure column types match SQLAlchemy 2.0 / AsyncSession model definitions (no type drift).

**Pass**: All constraints, defaults, and types consistent between migrations and models.
**Fail**: Type mismatch or missing constraint that exists in the application layer.

---

## Step 6: Test Rollback Safety

1. `[CRITICAL]` Confirm each migration has a working `downgrade()` — not `pass` or empty.
2. `[WARNING]` Flag empty `downgrade()` with no explanatory comment.
3. Check that downgrade does not irreversibly lose data (or explicitly documents when it does).
4. Verify downgrade handles partial backfill state (migration interrupted mid-batch).
5. Confirm upgrade -> downgrade -> upgrade cycle produces a clean state.

**Pass**: All migrations have functional downgrade; destructive downgrades documented.
**Fail**: Missing downgrade or undocumented data loss on rollback.

---

## Step 7: Produce Report

Output to `{output_folder}/data-architect/migration-review.md` with:

1. **Chain Integrity** - head count, orphan check, duplicate prefix status
2. **Zero-Downtime Assessment** - table of operations with risk classification and mitigation
3. **Tenant Isolation** - PASS/FAIL per new table for tenant_id, FK, and index
4. **Backfill Safety** - table of backfills with batch size, scope, and duration estimate
5. **Constraint Consistency** - mismatches between migrations and models/schemas
6. **Rollback Status** - PASS/FAIL per migration for downgrade completeness
7. **Findings Summary** - all issues sorted by severity (`[CRITICAL]` > `[WARNING]` > `[INFO]`)
8. **Migration Checklist** - final go/no-go checklist for deployment

---

## Step 8: Present Results

- State total migrations reviewed and current chain head.
- Highlight any `[CRITICAL]` findings — zero-downtime violations or missing tenant isolation.
- List migrations requiring maintenance window (if any) with estimated duration.
- Confirm whether the migration set is **APPROVED**, **APPROVED WITH CONDITIONS**, or **BLOCKED**.

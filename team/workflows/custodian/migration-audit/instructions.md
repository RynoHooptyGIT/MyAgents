# Migration Audit - Custodian Workflow

Verifies Alembic migration chain integrity, checks for numbering conflicts, validates tenant isolation in new tables, and confirms down_revision linkage.

---

## Step 1: Migration File Inventory

1. List all files in `backend/alembic/versions/`.
2. Extract from each filename: the numeric prefix (e.g., `081`), the descriptive slug, and the full filename.
3. Produce a sorted table: `| Number | Filename | revision | down_revision |`.
4. Read the `revision` and `down_revision` variables from the top of each migration file.

---

## Step 2: Duplicate Number Detection

1. Group migration files by their numeric prefix.
2. Flag any prefix that appears more than once (e.g., two files both starting with `081_`).
3. For each duplicate set, list the conflicting filenames.
4. Recommend resolution: one file must be renumbered to the next available number.

**Severity**: CRITICAL - duplicate numbers will cause Alembic to fail.

---

## Step 3: Revision Chain Validation

1. Build a directed graph: each migration's `down_revision` points to its parent.
2. Verify the chain forms a single linear sequence (no forks, no orphans).
3. Check for:
   - **Broken links**: A `down_revision` value that does not match any file's `revision`.
   - **Orphan migrations**: Files whose `revision` is never referenced as a `down_revision` by any subsequent file (except the head).
   - **Multiple heads**: More than one migration with no successor (Alembic allows this but it signals unmerged branches).
   - **Circular references**: Any cycle in the down_revision chain.
4. Report the current HEAD revision and total chain length.

---

## Step 4: Tenant Isolation in Migrations

For every migration that creates a new table (`op.create_table`):

1. Verify a `tenant_id` column is included (type `UUID`, `ForeignKey` to `tenants.id`).
2. Verify a `tenant_id` index exists (either standalone or as part of a composite index).
3. Check for RLS (Row-Level Security) policy creation:
   - Look for `op.execute(` calls containing `CREATE POLICY` or `ENABLE ROW LEVEL SECURITY`.
   - If RLS policies exist elsewhere in the project, flag tables missing them for consistency.

**Exceptions**: Junction tables, enum tables, or tenant-management tables themselves.

---

## Step 5: Migration Content Quality

For each migration file, check:

1. **Has docstring**: Top-level docstring or comment explaining the purpose.
2. **Has downgrade**: The `downgrade()` function is not empty (contains at least one operation).
3. **No hardcoded UUIDs**: Search for hardcoded UUID strings that should be parameterized.
4. **No data migrations mixed with schema**: Flag migrations that mix `op.execute(INSERT/UPDATE/DELETE)` with `op.create_table/add_column` -- these should be separate migrations.

---

## Step 6: Model-Migration Alignment

1. List all model classes from `backend/app/models/__init__.py` imports.
2. For each model's `__tablename__`, search migrations for a corresponding `op.create_table('tablename')`.
3. Flag any model whose table has no migration (may indicate manual table creation or missing migration).
4. Flag any migration creating a table that has no corresponding model (may indicate a removed feature with leftover migration).

---

## Step 7: Produce Report

Output a structured report to `{output_folder}/custodian/migration-audit.md` with:

1. **Migration Inventory** - numbered list with revision IDs
2. **Duplicate Numbers** - conflicts requiring immediate resolution
3. **Chain Integrity** - graph validation results, HEAD revision, chain length
4. **Tenant Isolation** - table-by-table tenant_id and RLS status
5. **Content Quality** - per-migration quality checklist results
6. **Model Alignment** - models without migrations and vice versa
7. **Summary Verdict** - PASS (no issues), CONCERNS (warnings only), or FAIL (critical issues)
8. **Action Items** - ordered list of required fixes

Use severity markers: `[CRITICAL]` for duplicate numbers and broken chains, `[WARNING]` for missing tenant_id or empty downgrades, `[INFO]` for quality suggestions.

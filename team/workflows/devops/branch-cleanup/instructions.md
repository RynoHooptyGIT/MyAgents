# Branch Cleanup Workflow

Clean up local git branches that have been deleted on the remote (marked as `[gone]`), including removing associated worktrees. Prevents stale branch accumulation in long-lived development environments.

---

## Step 1: Fetch Remote State

Sync remote tracking information:

```bash
git fetch --prune
```

This updates remote refs and removes any remote-tracking references that no longer exist on the remote.

- `[CRITICAL]` If not a git repository → inform user and STOP
- `[CRITICAL]` If no remote configured → inform user and STOP

---

## Step 2: Identify Gone Branches

List all local branches and identify those marked `[gone]`:

```bash
git branch -v
```

Parse the output to find branches where the upstream has been deleted (shown as `[gone]`).

- Record each gone branch name
- Note branches with `+` prefix (these have associated worktrees)
- Record the current branch name to ensure it is never deleted
- `[WARNING]` If the current branch is marked `[gone]`, warn user but do not delete it
- `[INFO]` If no branches are marked `[gone]`, report "No cleanup needed" and STOP

---

## Step 3: Inventory Worktrees

List all worktrees to identify those associated with gone branches:

```bash
git worktree list
```

For each gone branch, check if a worktree exists:
- Match worktree entries to branch names via the `[branch-name]` suffix
- Record worktree paths that need removal
- `[WARNING]` Never remove the main worktree (the primary repository directory)

---

## Step 4: Preview Cleanup

Present the cleanup plan to the user before executing:

```
BRANCH CLEANUP PLAN:

  Branches to delete:
    - [branch-name] (last commit: [short-sha] [date])
    - [branch-name] (last commit: [short-sha] [date])

  Worktrees to remove:
    - [path] → [branch-name]

  Protected (will NOT be deleted):
    - [current branch] (currently checked out)

  Total: [N] branches, [M] worktrees
```

Ask user to confirm before proceeding.

---

## Step 5: Execute Cleanup

For each gone branch:

1. **Remove worktree first** (if one exists and it is not the main worktree):
   ```bash
   git worktree remove --force "[worktree-path]"
   ```

2. **Delete the branch**:
   ```bash
   git branch -D "[branch-name]"
   ```

3. Record the result (success or failure) for each operation.

- `[CRITICAL]` If a worktree removal fails, skip branch deletion for that branch and report the error
- `[INFO]` Log each successful deletion

---

## Step 6: Present Results

Display cleanup summary directly to the user:

```
BRANCH CLEANUP COMPLETE

  Deleted:  [N] branches
  Worktrees removed: [M]
  Errors:   [E] (if any)
  Remaining local branches: [list]
```

If any errors occurred, list them with suggested manual resolution steps.

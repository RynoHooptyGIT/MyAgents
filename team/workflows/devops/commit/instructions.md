# Commit Workflow

Lightweight commit workflow — stage, generate a smart commit message, and commit. No push, no PR, no BMAD tracking updates. Use the Ship workflow for the full release pipeline.

---

## Step 1: Assess Current State

Gather git state:

- Current branch: `git branch --show-current`
- Git status: `git status --short`
- Staged changes: `git diff --cached --stat`
- Unstaged changes: `git diff --stat`
- Recent commits: `git log --oneline -5`

**Stop conditions**:
- `[CRITICAL]` No changes detected → report "Nothing to commit" and STOP
- `[CRITICAL]` Not a git repository → inform user and STOP

**Branch awareness**:
- `[WARNING]` If current branch is `main` → warn: "You are committing directly to `main`. This should only be done for hotfixes or release preparation. Consider creating a feature branch first."
- `[WARNING]` If current branch is `develop` → warn: "You are committing directly to `develop`. Feature work should be on a dedicated `feature/*` or `fix/*` branch. Consider running `dev-story` which auto-creates the correct branch. Continue? [y/N]"
- `[INFO]` If current branch matches `feature/*` or `fix/*` → no warning needed, this is the expected workflow

---

## Step 2: Security Check

Scan staged and modified files for sensitive content:

| Pattern | Reason |
|---------|--------|
| `.env`, `.env.local`, `.env.production` | Environment secrets |
| Files containing `API_KEY`, `SECRET`, `PASSWORD`, `TOKEN`, `PRIVATE_KEY` | Embedded credentials |
| `credentials.json`, `service-account.json` | Service account keys |
| `*.pem`, `*.key` files | Private key material |
| `node_modules/`, `__pycache__/`, `.venv/` | Build artifacts |

- `[CRITICAL]` If sensitive files detected → exclude from staging, warn user
- `[INFO]` Suggest adding to `.gitignore` if not already present

---

## Step 3: Stage Changes

1. If files are already staged, use those
2. If nothing staged but changes exist, stage all modified/new files (excluding sensitive files)
3. Present preview:

```
FILES TO COMMIT:
  Modified: [list]
  Added:    [list]
  Deleted:  [list]
  Total: [count] files
```

- `[WARNING]` If staging more than 50 files, confirm with user
- Ask user to confirm before proceeding

---

## Step 4: Generate Commit Message

Analyze the staged diff to generate a commit message:

1. Read the full diff: `git diff --cached`
2. Identify the primary change type: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`
3. Identify the scope from affected directories (e.g., `auth`, `frontend`, `models`)
4. Write a concise imperative description

Format:
```
[type]([scope]): [Brief imperative description]

[2-3 sentence summary of what changed and why]

Co-Authored-By: Claude <noreply@anthropic.com>
```

Show the proposed message and ask user to confirm or edit.

---

## Step 5: Create Commit

Create the commit using HEREDOC syntax:
```bash
git commit -m "$(cat <<'EOF'
[commit message]
EOF
)"
```

Verify the commit succeeded by checking `git log -1 --oneline`.

- `[CRITICAL]` If commit fails (pre-commit hook rejection, etc.) → show error, suggest fixes
- `[INFO]` If pre-commit hook modifies files, re-stage and create a NEW commit (never amend)

---

## Step 6: Present Results

Display commit summary directly to the user:

```
COMMITTED
  SHA:     [short sha]
  Branch:  [branch name]
  Message: [first line]
  Files:   [count] changed ([additions]+, [deletions]-)
```

Remind user they can run the Ship workflow to push and create a PR.

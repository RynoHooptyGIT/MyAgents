# Ship Workflow

Commit, push, and create a PR — with smart commit messages, story-aware context, and BMAD status updates. Packages completed work into clean commits and well-documented pull requests.

---

## Step 1: Assess Current State

Gather git and project state:

- Current branch: `git branch --show-current`
- Git status: `git status --short` (never use `-uall` flag)
- Staged changes: `git diff --cached --stat`
- Unstaged changes: `git diff --stat`
- Recent commits: `git log --oneline -5`
- Remote tracking: `git rev-parse --abbrev-ref @{upstream}` (check if upstream exists)

**Stop conditions**:
- `[CRITICAL]` No changes detected (nothing staged, nothing modified) → report "Nothing to ship" and STOP
- `[CRITICAL]` Not a git repository → inform user and STOP
- `[WARNING]` Detached HEAD state → warn user, suggest creating a branch first

**Branch validation**:
- `[WARNING]` If current branch is `main` → warn: "You are about to ship from `main`. Feature work should be on a `feature/*` or `fix/*` branch. Continue anyway? [y/N]"
- `[WARNING]` If current branch is `develop` → warn: "You are about to ship directly from `develop`. Feature work should be on a dedicated feature branch. Continue anyway? [y/N]"
- `[INFO]` Validate branch name matches convention: must match `feature/*` or `fix/*` for story work. If not, warn: "Branch does not follow naming convention (`feature/*` or `fix/*`). Proceeding anyway."

---

## Step 2: Identify Story/Task Context

Check for story context in priority order:

1. **Explicit input**: If a story/spec file path was provided as argument, read it and extract: story key, title, acceptance criteria summary
2. **BMAD detection**: If `team/config.yaml` exists:
   - Search for `output/sprint-status.yaml`
   - Find story with status `in-progress` or `review`
   - Load that story file for context
   - Extract: story key, title, AC summary
3. **Diff-based inference**: If no story context available, analyze `git diff` to infer what was done

Record the context source for use in commit message generation.

---

## Step 2b: Validate Story Lifecycle (BMAD Gate)

**Skip this step if:** No BMAD story was detected in Step 2.

When a BMAD story was found in Step 2, validate its lifecycle state before proceeding:

1. Read the story file's `Status` field
2. Cross-reference with `sprint-status.yaml` for the story's current status

**Gate logic:**

- **Status is `done`** → `[PASS]` Code review has been completed. Proceed to Step 3.
- **Status is `review`** → `[WARNING]` Story is awaiting code review. Display: "⚠️ Story is in 'review' status — code review (CR) has not been completed. Ship should only run AFTER code review passes."
  - Ask user: `[1] Run code-review first (recommended)` / `[2] Ship anyway (override)`
  - If user chooses [1] → STOP and inform user to run CR workflow
  - If user chooses [2] → Proceed with `[OVERRIDE]` noted in Step 8 report
- **Status is `in-progress`** → `[WARNING]` Story is still being implemented. Display: "⚠️ Story is still 'in-progress' — development and code review have not been completed."
  - Ask user: `[1] Go back to dev-story (recommended)` / `[2] Ship anyway (override)`
  - If user chooses [1] → STOP and inform user to run DS workflow
  - If user chooses [2] → Proceed with `[OVERRIDE]` noted in Step 8 report
- **Status is `backlog` or `ready-for-dev`** → `[CRITICAL]` Story has not been started. Display: "🛑 Story has not been implemented. Cannot ship work that hasn't been developed."
  - STOP — do not allow override for this case

**Secondary evidence check:** If story status is `done`, also verify the story file contains a review section (look for "CODE REVIEW FINDINGS" or "Senior Developer Review"). If missing, display `[INFO]` note but do not block.

---

## Step 3: Security Check

Scan staged and modified files for sensitive content before committing:

| Pattern | Reason |
|---------|--------|
| `.env`, `.env.local`, `.env.production` | Environment secrets |
| Files containing `API_KEY`, `SECRET`, `PASSWORD`, `TOKEN`, `PRIVATE_KEY` | Embedded credentials |
| `credentials.json`, `service-account.json` | Service account keys |
| `*.pem`, `*.key` files | Private key material |
| `node_modules/`, `__pycache__/`, `.venv/` | Build artifacts |

- `[CRITICAL]` If sensitive files detected → list them with reasons, exclude from staging, warn user
- `[INFO]` Suggest adding detected files to `.gitignore` if not already present

---

## Step 4: Stage and Preview

Stage the appropriate files:

1. If files are already staged, use those
2. If nothing staged but changes exist, stage all modified/new files (excluding sensitive files and generated artifacts)
3. Present a preview to the user:

```
FILES TO COMMIT:
  Modified: [list]
  Added:    [list]
  Deleted:  [list]
  Total: [count] files ([additions] additions, [deletions] deletions)
```

- `[WARNING]` If staging more than 50 files, confirm with user this is intentional
- Ask user to confirm before proceeding. If user wants to exclude files, unstage them.

---

## Step 5: Create Commit

Generate commit message based on available context:

**With story context:**
```
[type]([scope]): [Story Key] - [Brief description]

[2-3 sentence summary of what was implemented and why]

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Without story context (diff-based):**
```
[type]([scope]): [Brief imperative description]

[2-3 sentence summary derived from the diff]

Co-Authored-By: Claude <noreply@anthropic.com>
```

Use conventional commit types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`.

Create commit using HEREDOC syntax for proper formatting. Show the commit result.

---

## Step 6: Update BMAD Tracking

**If `output/sprint-status.yaml` exists AND story context was loaded:**
- Read the complete sprint-status.yaml
- Find the story key entry and update status to `done`
- Add comment with date and summary

**If BMAD story file exists:**
- Update story Status to `done`
- Add Change Log entry with commit summary and date

**GitHub Issue Sync (if story file contains `**GitHub Issue:** #NNN`):**
- Extract the issue number
- Update label: `gh issue edit #NNN --remove-label "status:review" --add-label "status:done"`
- Close with comment: `gh issue close #NNN --comment "Completed in commit [short-sha]."`
- Store issue number for PR linking in Step 7

- `[INFO]` If no BMAD tracking found, skip this step silently

## Step 6b: Regenerate Sprint Digest

After updating sprint-status.yaml, regenerate the sprint digest context file so it stays fresh:

- Run: `python scripts/context/generate_all.py --sprint`
- This regenerates `output/context/sprint-digest.md` from the updated sprint-status.yaml
- Stage the regenerated file for inclusion in the commit (or as a follow-up commit)
- `[INFO]` If the script is not found or fails, skip silently — this is non-blocking

---

## Step 7: Push and PR

Ask the user to choose:

1. **Push and create PR** — Push branch and open a pull request
2. **Push only** — Push to remote without creating a PR
3. **Done** — Keep changes local

### Push logic:
- If no upstream: `git push -u origin [branch]`
- If upstream exists: `git push`

### PR target branch:
- Determine the correct PR base branch:
  - If current branch starts with `feature/` or `fix/` → PR targets `develop` (`--base develop`)
  - If current branch is `develop` → PR targets `main` (`--base main`)
  - Otherwise → ask user for target branch (default: `develop`)
- `[CRITICAL]` Never auto-target `main` for feature/fix branches

### PR creation:
- Check if PR already exists: `gh pr view [branch] --json number`
- If no existing PR, create one with `gh pr create --base [target_branch]` including:
  - Summary bullets, acceptance criteria (if available), file change count
  - `Closes #NNN` if GitHub issue was linked
- If PR already exists, inform user changes were pushed to it

---

## Step 8: Produce Report

Output summary to `{output_folder}/devops/ship.md`:

```
============================================
  SHIP SUMMARY
============================================
  Branch:   [branch name]
  Date:     [current date]
  Commit:   [sha]
============================================

Commit:   [sha] on branch [branch]
Message:  [first line of commit message]
Files:    [count] changed
Push:     [pushed to origin / local only]
PR:       [URL / not created / already exists at URL]
BMAD:     [sprint-status updated / story updated / not applicable]
Issues:   [#NNN closed / not applicable]
```

---

## Step 9: Present Results

Display the ship summary directly to the user. Highlight:
- The commit SHA and message
- PR URL (if created)
- Any `[WARNING]` items that were encountered during the process

---

## Step 10: Await and Review PR Feedback

**Skip this step if:** no PR was created in Step 7 (user chose "Push only" or "Done").

After PR creation, automated reviewers (GitHub Copilot, bots) typically post review comments within 1-3 minutes. This step ensures all review feedback is addressed before the PR is considered merge-ready.

### 10a: Poll for reviews

- Wait 60 seconds after PR creation to allow automated reviewers to process
- Check for reviews: `gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --jq '.[] | {user: .user.login, state: .state, body: .body}'`
- Check for inline comments: `gh api repos/{owner}/{repo}/pulls/{pr_number}/comments --jq '.[] | {user: .user.login, path: .path, line: .line, body: .body, id: .id, in_reply_to_id: .in_reply_to_id}'`
- Check for issue-level comments: `gh api repos/{owner}/{repo}/issues/{pr_number}/comments --jq '.[] | {user: .user.login, body: .body, id: .id}'`
- If no reviews or comments found after first check, wait another 60 seconds and try once more
- If still no reviews after second check, inform user: "No automated reviews posted yet. You can re-run this step later or proceed to merge."

### 10b: Analyze each review comment

For each review comment or suggestion, categorize it:

| Category | Criteria | Action |
|----------|----------|--------|
| **Accept** | Suggestion improves code quality, fixes a real bug, or aligns with project conventions | Will implement the change |
| **Reject** | Suggestion is incorrect, doesn't apply to this context, or conflicts with project requirements | Will post explanation and resolve |
| **Discuss** | Suggestion is valid but has trade-offs, or requires user decision | Will present to user for decision |

### 10c: Present review plan to user

Display a summary of all review comments with proposed dispositions:

```
PR REVIEW FEEDBACK
==================
[N] comments from [reviewer(s)]

ACCEPT ([count]):
  - [file:line] [summary of suggestion] → will implement
  ...

REJECT ([count]):
  - [file:line] [summary of suggestion] → [brief reason]
  ...

DISCUSS ([count]):
  - [file:line] [summary of suggestion] → [trade-off description]
  ...
```

- Ask user to confirm the plan or adjust any dispositions before proceeding
- `[CRITICAL]` Do NOT auto-resolve any conversations without user confirmation of the plan

---

## Step 11: Resolve PR Conversations

**Skip this step if:** Step 10 was skipped or no review comments were found.

### 11a: Implement accepted changes

For each **accepted** suggestion:
1. Make the code change locally
2. Verify the change doesn't break tests (run relevant test suite)
3. Stage the changed files

### 11b: Commit and push fixes

- If any accepted changes were made:
  - Generate commit message: `fix(review): address PR feedback — [N] suggestions applied`
  - Include `Co-Authored-By: Claude <noreply@anthropic.com>`
  - Commit using HEREDOC syntax
  - `[CRITICAL]` If pre-commit hook fails, fix and create NEW commit (never amend)
  - Push to the PR branch: `git push`

### 11c: Resolve conversations

For each review comment:
- **Accepted**: Reply confirming the fix, then resolve the conversation thread
  - `gh api repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies -f body="Applied — fixed in [commit_sha]."`
- **Rejected**: Reply with clear explanation, then resolve
  - `gh api repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies -f body="[explanation]"`
- **Discussed**: Reply with the user's decision and rationale, then resolve

To resolve a review thread, use the GraphQL API:
```
gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "[thread_node_id]"}) { thread { isResolved } } }'
```

To get thread node IDs:
```
gh api graphql -f query='{ repository(owner: "{owner}", name: "{repo}") { pullRequest(number: {pr_number}) { reviewThreads(first: 50) { nodes { id isResolved comments(first: 1) { nodes { body } } } } } } }'
```

### 11d: Verify all conversations resolved

- Re-fetch PR review threads and confirm all are resolved
- Check CI status: `gh pr checks {pr_number}`
- Report final PR state to user:

```
PR REVIEW RESOLUTION COMPLETE
==============================
Comments resolved: [N] / [total]
Changes committed: [sha] (if any)
CI status:         [passing / failing / pending]
PR ready to merge: [Yes / No — reason]
```

- If all conversations are resolved and CI passes, inform user the PR is ready to merge
- If CI is failing, note whether failures are pre-existing or introduced by review changes

---

## Merge Strategy (CRITICAL)

When merging PRs — whether manually or via `gh pr merge`:

- **ALWAYS use full merge** (`gh pr merge --merge`). This preserves individual commit history on the target branch.
- **NEVER squash-and-merge** (`--squash`). Squash merging flattens commit history and causes problems with traceability.
- **NEVER rebase-and-merge** (`--rebase`) unless explicitly requested by the user.
- If branch protection blocks the merge, use the `--admin` flag to bypass: `gh pr merge --merge --admin`

# PR Review Workflow

Review a pull request for bugs, CLAUDE.md compliance, and code quality. Uses multi-pass analysis with confidence scoring to filter false positives. Distinct from the BMAD `/code-review` workflow (which reviews working copy against stories) — this reviews a PR branch diff specifically.

---

## Step 1: Validate PR Eligibility

Fetch PR details using `gh pr view`:

```bash
gh pr view [PR-number-or-branch] --json state,isDraft,author,title,body,number,headRefName,baseRefName,commits
```

**Stop conditions**:
- `[CRITICAL]` PR is closed or merged → report status and STOP
- `[WARNING]` PR is a draft → inform user, ask if they want to proceed anyway
- `[INFO]` PR is from an automated bot (e.g., dependabot) → note this for context

Record: PR number, title, head branch, base branch, author.

---

## Step 2: Gather Context Files

Identify relevant context for the review:

1. **CLAUDE.md files**: Find all `CLAUDE.md` files in the repo root and in directories touched by the PR
2. **project-context.md**: Load `**/project-context.md` if it exists — this contains the 102 project rules
3. **PR diff**: Fetch the full diff:
   ```bash
   gh pr diff [PR-number] --patch
   ```
4. **Changed files list**: Extract file paths from the diff for targeted analysis

- `[INFO]` Record total files changed, lines added, lines removed

---

## Step 3: Summarize the Change

Analyze the PR diff to produce a concise summary:

- What is the primary purpose of this PR? (feature, bugfix, refactor, docs, etc.)
- Which areas of the codebase are affected? (backend models, frontend components, migrations, etc.)
- What is the risk level? (low: docs/tests only, medium: business logic, high: auth/security/data model)

This summary provides context for the detailed review passes.

---

## Step 4: Multi-Pass Code Review

Execute 5 independent review passes, each focused on a different concern:

### Pass 1: CLAUDE.md and Project Rules Compliance
- Check changes against `CLAUDE.md` instructions and `project-context.md` rules
- Verify naming conventions, file organization, required patterns
- Note: CLAUDE.md is guidance for code generation — not all rules apply during review

### Pass 2: Bug Scan (Shallow)
- Read the changed lines in the PR diff
- Focus on the changes themselves, not surrounding code
- Look for: null pointer risks, off-by-one errors, logic inversions, missing error handling, race conditions
- Avoid nitpicks — focus on bugs a senior engineer would flag

### Pass 3: Historical Context
- Check `git log` for files modified in the PR to understand recent history
- Look for patterns: was code recently fixed that's being re-broken? Are there related open issues?
- Use `git blame` on critical sections if needed

### Pass 4: Previous PR Comments
- Check recent PRs that touched the same files:
  ```bash
  gh pr list --state merged --search "[filename]" --limit 5
  ```
- Look for recurring feedback that may apply to this PR

### Pass 5: Code Comment Compliance
- Read inline code comments (TODO, FIXME, HACK, NOTE) in modified files
- Verify changes don't violate guidance embedded in code comments
- Check for stale comments that should be updated given the changes

---

## Step 5: Confidence Scoring

For each issue found in Step 4, evaluate confidence on a 0–100 scale:

| Score | Meaning |
|-------|---------|
| 0 | `[FALSE_POSITIVE]` Does not hold up to scrutiny, or is a pre-existing issue |
| 25 | `[LOW]` Might be real but unverified; stylistic issues not in CLAUDE.md |
| 50 | `[MEDIUM]` Verified real but minor — nitpick or unlikely in practice |
| 75 | `[HIGH]` Verified, likely to be hit in practice, important to fix |
| 100 | `[CRITICAL]` Confirmed real, will happen frequently, directly impacts functionality |

**Filter**: Only retain issues scoring **80 or above**.

Known false positive patterns to discard:
- Pre-existing issues (not introduced by this PR)
- Issues a linter/typechecker/compiler would catch (CI handles these)
- General code quality concerns unless explicitly required in CLAUDE.md
- Changes in functionality that are likely intentional
- Issues on lines not modified in this PR

---

## Step 6: Produce Report

Output a structured report to `{output_folder}/custodian/pr-review.md`:

```
============================================
  PR REVIEW: #[number] — [title]
============================================
  Branch:     [head] → [base]
  Author:     [author]
  Date:       [current date]
  Files:      [count] changed
  Risk Level: [low/medium/high]
============================================

## Summary
[1-2 sentence summary of the PR]

## Issues Found: [count]

### Issue 1: [brief description] (confidence: [score])
- **Source**: [Pass name — e.g., "Bug Scan"]
- **Location**: [file:line range]
- **Evidence**: [code snippet or rule reference]
- **Recommendation**: [suggested fix]

[... repeat for each issue ...]

## No Issues / Clean Review
[If no issues scored >= 80]
No issues found. Checked for bugs, CLAUDE.md compliance, and historical context.

---
Generated by: Code Custodian (Sentinel) - PR Review Workflow
```

---

## Step 7: Post Comment (Optional)

Ask the user: "Post this review as a PR comment?"

If yes, format and post using:
```bash
gh pr comment [PR-number] --body "$(cat <<'EOF'
### Code Review

[formatted findings or "No issues found"]

Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

- `[WARNING]` Re-check PR eligibility before posting (in case it was closed/merged during review)
- Include file:line links using full git SHA for GitHub rendering

---

## Step 8: Present Results

Display the review summary directly to the user:
- Number of issues found (and how many were filtered as false positives)
- Top findings with locations
- Overall assessment: APPROVE / REQUEST_CHANGES / COMMENT_ONLY

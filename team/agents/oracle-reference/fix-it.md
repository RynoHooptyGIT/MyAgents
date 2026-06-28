# Oracle prompt: fix-it (lazy)

CONTEXT ANALYSIS — Run in order, stop when actionable problems are found:

STAGE 1 — CONVERSATION CONTEXT (always runs first):
1. Scan recent tool output for: non-zero exit codes, stack traces, error messages, build failures, test failures
2. Scan recent user messages for: complaints, bug descriptions, "not working" phrases, questions about problems
3. Identify files recently read/edited as the active working area
4. If actionable problems found → proceed to CLASSIFY

STAGE 2 — PROJECT STATE SCAN (only if Stage 1 finds nothing):
NOTE: This stage may take time. Only runs on explicit "fix it" trigger, never on ambient detection.
1. Run: git status / git diff — check for uncommitted changes, merge conflicts
2. Run test suite if project has one (check package.json scripts, Makefile, pytest, etc.)
3. Run lint/type-check if detectable
4. Read sprint-status.yaml — check for stuck stories, stale in-progress items
5. Check recent git log — identify what was last worked on
6. If actionable problems found → proceed to CLASSIFY

CLASSIFY each problem:
- Description: what is wrong
- Category: bug | test-failure | build-error | security | architecture | data | test-coverage | sprint-blocker | devops | frontend | api | code-quality
- Severity: CRITICAL | HIGH | MEDIUM | LOW
- Evidence: the specific error, file, line, or signal
- Independence: can this be fixed without affecting other problems? (yes/no)

DISPATCH using {dispatch_map}:
1. For each problem, find the matching category in the dispatch map
2. Check independence — group related problems, separate independent ones
3. Independent problems with no shared state → dispatching-parallel-agents skill
4. Problems spanning 3+ categories → run [LR] Let's Ride (scan-and-plan) instead of piecemeal fixes

OUTPUT depends on mode:
- If {oracle_mode} = "auto" OR user said "just fix it" / "fix it now":
  Execute immediately. Skills invoke directly. Agent routes present as recommendations.
  Increment {oracle_issues_detected}. Update {oracle_last_action}.
- Otherwise (plan mode):
  Present:
  "FIX-IT ANALYSIS
  Found [N] problems:

  1. [SEVERITY] Description → dispatch target
  2. [SEVERITY] Description → dispatch target
  ...

  Approve? (sh = execute all, or pick numbers to execute selectively)"

  Wait for user response. "sh" = execute all. Numbers = execute selected. Anything else = discuss.

# Oracle — Action Prompts (lazy-loaded)

Loaded on demand by the Oracle `action` handler when a menu item with
`action="#prompt-id"` is selected. NOT loaded at activation — keeps the
per-session footprint down. Find the matching `<prompt id="...">` and execute
its content as instructions.

```xml
<prompts>
    <prompt id="project-brief">
      Re-read {project-root}/output/implementation-artifacts/sprint-status.yaml and present a comprehensive project brief:

      1. OVERALL PROGRESS: Total epics done/total, total stories done/total
      2. CURRENT EPIC: Name, completion percentage, remaining stories with their statuses
      3. IN FLIGHT: Any stories currently in-progress or review status — with lifecycle phase
      4. NEXT UP: The next story that should be worked on
      5. RISKS: Any stale items, missing retrospectives, lifecycle violations, or known issues
      6. RECOMMENDATION: Single most impactful next action
      7. WORKFLOW: Which menu command I will execute to accomplish it

      Format as a clean, scannable brief. No walls of text.
    </prompt>

    <prompt id="next-action">
      Based on sprint-status.yaml, apply this decision tree to determine AND EXECUTE the single best next action:

      1. CRITICAL: Are any stories stuck in "in-progress" for a long time? -> Resume work with DS (dev-story)
      2. HIGH: Are any stories in "review" status? -> Execute CR (code-review) workflow
      3. MEDIUM: Does the next story in the current epic need a story file? -> Execute CS (create-story)
      4. NORMAL: Is there a "ready-for-dev" story? -> Execute DS (dev-story)
      5. LOW: Is the current epic complete but no retrospective done? -> Execute RT (retrospective)
      6. INFO: Everything clear -> Present brief and ask user for direction

      Present the recommended action, then ASK the user to confirm before executing the workflow.
      Include: which story, which workflow, and what the expected outcome is.
    </prompt>

    <prompt id="route-to-agent">
      Ask the user what task they need help with, then route to the correct specialist agent:

      ROUTING TABLE — Domain Expertise (I route, they execute):
      | Task | Agent | Invoke Command |
      |------|-------|---------------|
      | Backend API/data design | Winston (Architect) | /team:architect |
      | Frontend UI/UX design | Sally (UX Designer) | /team:ux-designer |
      | Test strategy/planning | Murat (Test Architect) | /team:tea |
      | Repo health/patterns | Sentinel (Custodian) | /team:custodian |
      | Security review | Shield (Security) | /team:security-auditor |
      | NIST RMF compliance | Atlas (NIST Expert) | /team:nist-rmf-expert |
      | Docker/CI/CD | Forge (DevOps) | /team:devops |
      | API contract drift | Pact (API Contract) | /team:api-contract |
      | AI/Agentic architecture | Nexus (Agentic Expert) | /team:agentic-expert |
      | ML/model evaluation | Neuron (ML Expert) | /team:ml-expert |
      | SQL/data/caching | Vault (Data Architect) | /team:data-architect |
      | Healthcare compliance | Dr. Vita (Healthcare) | /team:healthcare-expert |
      | Government regulations | Senator (Government) | /team:government-expert |
      | Financial regulations | Sterling (Financial) | /team:financial-expert |
      | Quick fix/prototype | Barry (Quick Flow) | /team:quick-flow-solo-dev |
      | PRD creation/editing | John (Product Manager) | /team:pm |
      | Brainstorming / Creative Thinking | Carson (Creative Thinking Coach) | /team:creative-thinking-coach |
      | Design Thinking / Innovation | Maya (Design & Strategy Coach) | /team:design-strategy-coach |
      | Storytelling / Presentations | Sophia (Storyteller & Presenter) | /team:storyteller-presenter |

      **⚠️ BRAINSTORMING LIFECYCLE:** After brainstorming, ideas must flow through the pipeline: Brainstorm → Update Epics/PRD → CS (create-story) → DS (dev-story). Do NOT proceed directly from brainstorming to implementation.

      IMPLEMENTATION WORKFLOWS — I execute these directly (do NOT route):
      | Task | My Command |
      |------|-----------|
      | Create story file | CS |
      | Implement story | DS |
      | Code review | CR |
      | Ship (commit/push/PR) | SH |
      | Sprint planning | SP |
      | Sprint status check | SS |
      | Epic consistency check | EC |
      | Course correction | CC |
      | Retrospective | RT |

      Present the matching agent with the exact slash command, or indicate which of MY commands I'll execute directly.
    </prompt>

    <prompt id="risk-scan">
      Scan for project risks by checking:

      1. LIFECYCLE VIOLATIONS: Stories marked "done" that never went through "review" status
      2. STALE STORIES: Any stories in "in-progress" that may have been forgotten
      3. MISSING REVIEWS: Completed stories that skipped code review
      4. MISSING RETROSPECTIVES: Completed epics without retrospectives
      5. MISSING STORY FILES: Stories in "in-progress" or later status but no file in stories/ directory
      6. MIGRATION CONFLICTS: Check project-context.md for migration directory path; verify no duplicate migration numbers exist
      7. TEST GAPS: Note any known coverage gaps
      8. BACKLOG HEALTH: Are upcoming stories well-defined or do they need creation?
      9. UNPROCESSED BRAINSTORMS: Check if brainstorming session files exist in {output_folder}/analysis/brainstorming-session-*.md that haven't been converted to stories or epic updates

      Present findings ranked by severity: CRITICAL, HIGH, MEDIUM, LOW.
      For each finding, specify which workflow command I should execute or which agent to route to.
    </prompt>

    <prompt id="fix-it">
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
      4. Problems spanning 3+ categories → recommend Maestro scan-and-plan instead

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
    </prompt>

    <prompt id="oracle-status">
      Present current Oracle ambient intelligence state:

      "ORACLE STATUS
      Mode: {oracle_mode} (suggest | auto | off)
      Issues detected this session: {oracle_issues_detected}
      Last action: {oracle_last_action}
      Dispatch map loaded: yes/no

      Toggle: 'oracle auto' | 'oracle suggest' | 'oracle off'"
    </prompt>

    <prompt id="session-handoff">
      Generate a session handoff summary for continuity:

      1. Read current sprint-status.yaml
      2. Note what the current state is
      3. Identify what was likely worked on (most recently changed stories)
      4. List what should be done next (apply the next-action decision tree)
      5. Note any open risks or blockers
      6. Specify which workflow command should be executed first in the next session

      Format as a brief markdown summary that the next session can quickly scan to get up to speed.
      Save to {output_folder}/session-handoff-{date}.md
    </prompt>
</prompts>
```

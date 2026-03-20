# Engineering Discipline Knowledge Base

Hard enforcement patterns that prevent AI agents from cutting corners during implementation. Each knowledge fragment defines an **Iron Law**, red flags, a rationalization table, and an enforcement protocol.

## Usage

Agents reference `discipline-index.csv` to load relevant fragments by tag. The engine-level enforcement protocol at `{project-root}/team/engine/discipline-gates.xml` provides reusable gate checks invocable from any workflow via `invoke-task`.

## Fragments

| ID | Purpose |
|----|---------|
| `verification` | No completion claims without fresh evidence |
| `tdd` | No production code without a failing test first |
| `debugging` | No fixes without root cause investigation |
| `receiving-review` | No performative agreement — verify then respond |
| `anti-rationalization` | Cross-cutting: even 1% chance = MUST follow discipline |

# Promptbranch Backlog

This directory is the tracked repository backlog for architectural and product work that has been accepted for future implementation but is not yet part of the accepted/current runtime.

Machine-readable authority: `docs/backlog/backlog.json`.

## Architectural invariant

> Promptbranch controls the release lifecycle. Each project defines what must be validated and how its artifact is built.

## Tracked tickets

| Priority | ID | Title | Status | Ticket |
|---:|---|---|---|---|
| 1 | ISSUE-001 | Add a global release lifecycle engine with repository-specific lifecycle contracts | implemented_candidate | `docs/backlog/ISSUE-001-global-release-lifecycle-engine.md` |
| 2 | PBAI-001 | Validate full AI application architecture in Promptbranch and PB modules | in_progress | `docs/backlog/PBAI-001-full-ai-application-architecture.md` |

## Classification rule

Only entries in `backlog.json` with `status: open` are open backlog tickets. `in_progress` means an explicitly bounded implementation phase is active but the ticket is not complete. Historical release rows, repair records, Definition-of-Done items, and rolling-horizon slices are not automatically backlog tickets.

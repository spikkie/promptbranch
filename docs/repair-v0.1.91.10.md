# Repair v0.1.91.10 — Run-all progress writer syntax and browser scheduler timeout diagnostics

## Base

`v0.1.91.10` is a repair-only candidate on top of `v0.1.91.9`.

It preserves the `v0.1.91.1` through `v0.1.91.9` repair stack and does not advance the normal `v0.1.91` slice.

## Reason

The `v0.1.91.9` operator run exposed two defects:

1. The new run-all progress writer emitted malformed embedded Python because a newline string was split across shell-script lines, producing `SyntaxError: unterminated string literal`.
2. The required `browser_scheduler_source_lifecycle` release-validation group could time out after 300 seconds with empty stdout/stderr tails, hiding the active pytest nodeid.

## Changes

- Replaced the fragile progress-writer newline string with `chr(10)` inside the embedded Python writer.
- Marked the `browser_scheduler_source_lifecycle` release-validation group with `nodeid_progress=true`.
- Added per-nodeid execution/progress for that group while retaining the same explicit pytest nodeid set and required-group semantics.
- Added timeout/failure diagnostics for the active nodeid, completed nodeids, failed nodeids, timed-out nodeids, and per-nodeid result summaries.
- Kept the group timeout as the total budget; the remaining budget is passed to each nodeid subprocess.

## Unchanged

- No live/browser behavior changed.
- No Project Source mutation semantics changed.
- No Project deletion behavior changed.
- No adoption/current semantics changed.
- No Docker bootstrap behavior changed.
- No localhost lifecycle-reuse policy changed.

## Validation performed

Focused validation performed before packaging:

- progress writer static regression for `chr(10)`
- per-nodeid progress success regression
- per-nodeid timeout active-nodeid regression
- version surface tests
- explicit browser scheduler nodeid group execution: 9 passed
- Python compile and shell syntax checks
- project-control validation
- Artifact Guardian and artifact verify

Full live `--run-all-tests --adopt-after-validation` was not run in the build environment.

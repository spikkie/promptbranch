# Promptbranch v0.1.111.2 repair candidate

Adds observable progress to long-running release validation without changing test assertions or adoption authority.

## Output

Each full-test progress line reports the current work unit, completed/total units, passed, failed, skipped, percentage complete, elapsed time, and an approximate ETA based on observed average duration per completed unit.

Release-control also reports the current outer release step and an overall approximate ETA across expected release steps.

## Fail-fast

- `pb test full --fail-fast` stops after the first failed browser phase or required release-validation group.
- Release control enables this by default and accepts `--fail-fast` / `--no-fail-fast`.
- Fail-fast never converts a failure into success and never bypasses required adoption gates.

## Authority

Accepted/current remains `v0.1.109.1.1` until full direct, localhost, external-live, publication, adoption, and accepted/current verification pass.

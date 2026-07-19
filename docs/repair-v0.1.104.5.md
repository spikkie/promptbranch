# Repair v0.1.104.5 — Hermetic release-validation profile isolation

## Type

Repair-only candidate for unadopted `v0.1.104.4`.

## Baseline

- accepted/current: `v0.1.103.10.116`
- repaired candidate: `v0.1.104.4`
- active candidate: `v0.1.104.5`

## Reason

The `v0.1.104.4` retry passed 9/10 release gates. Its functional direct browser flow passed, including source add/overwrite/remove, ask, and task-message operations. The required offline `browser_scheduler_source_lifecycle` group alone timed out at `test_project_remove_is_frozen_before_profile_scheduler`. The same node passed independently and under localhost, proving the remaining defect was release-validation environment isolation rather than scheduler behavior.

## Scope

- Preserve visual completion/envelope recovery, sandbox, current-turn readiness, one-reload recovery, Project Source behavior, and all ten release gates unchanged.
- Create a unique temporary isolation root for every release-validation subprocess.
- Explicitly set HOME, TMPDIR, XDG cache/config/data/state, Promptbranch profile, project state/config, and project cache paths inside that root.
- Run a child-Python preflight that resolves the actual Promptbranch paths before pytest starts.
- Fail closed before node execution when any resolved path leaves the isolation root or repository `.pb_profile` remains reachable.
- Record only ambient lock existence/path metadata; never read lock contents and never wait on it.
- Preserve per-node progress, the 300-second group timeout, and no automatic retry for timed-out nodes.

## Out of scope

No live/browser, visual, sandbox, source, adoption, timeout, retry, or conversation changes.

## Required proof

A regression creates a disposable repository containing a realistic `.pb_profile/.promptbranch-browser-profile.lock`, guards against reading that lock, and executes the exact previously timed-out scheduler node. The node must finish promptly with a resolved profile inside the temporary root. A second regression poisons the resolved profile to repository `.pb_profile` and proves the node is not launched.

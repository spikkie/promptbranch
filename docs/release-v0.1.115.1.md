# Promptbranch v0.1.115.1

## Slice

`v0.1.115.1 — Release-live profile ownership handoff repair`

## Failure repaired

The immutable `v0.1.115` candidate passed direct, localhost, rollback, import-smoke, and Artifact Guardian validation, then failed `live_project_ensure`. The release-live slot was still protected by an external `flock`, while the scheduler returned `browser_profile_busy` after approximately 0.001 seconds despite advertising a 600-second queue timeout.

## Repair

- Cross-process `flock` acquisition now polls within the same bounded queue deadline as the in-process lock.
- Timeout evidence includes the external owner PID, operation, operation ID, acquisition time, liveness, poll count, and observed ownership transitions.
- Live preflight and continuous live explicitly use the same service transport owner.
- Release control waits for service-level browser idle and then proves the host profile `flock` is released before starting `release-live-continuous`.
- The barrier applies after all preflight outcomes, including a successful rate-limit acknowledgement/cooldown path.
- Required release-validation groups include cross-process handoff regressions.

## Authority

This repair preserves all `v0.1.115` PBAI operational evidence and impact-testing behavior. It does not advance normal scope. Accepted/current remains `v0.1.114.2` until strict validation and evidence-bound adoption succeed.

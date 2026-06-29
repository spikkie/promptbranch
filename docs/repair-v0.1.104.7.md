# Repair v0.1.104.7 — rollback to v0.1.104.1 source line

## Base releases

- Accepted/current baseline before repair: `chatgpt_claudecode_workflow-2_v0.1.103.zip`
- Failed normal candidate: `chatgpt_claudecode_workflow-2_v0.1.104.zip`
- Operator-pinned rollback source line: `chatgpt_claudecode_workflow-2_v0.1.104.1.zip`
- Discarded repair candidates for this line: `v0.1.104.2`, `v0.1.104.3`, `v0.1.104.4`, `v0.1.104.5`, `v0.1.104.6`
- New repair candidate: `chatgpt_claudecode_workflow-2_v0.1.104.7.zip`

## Reason

The `v0.1.104.2` through `v0.1.104.6` repair chain introduced increasingly complex Project ensure, isolated-validation, Project Sources direct-route, route-hydration, and challenge/interstitial recovery behavior without resolving the live Project Source add blockage. Operator direction is to return to the `v0.1.104.1` source line and continue the original `v0.1.104` target from there.

## Repair

This candidate is built from the `v0.1.104.1` source line and updates only version/control-surface metadata for a canonical repair artifact. It preserves the `v0.1.104` sandbox mutation verification and rollback evidence gate and the `v0.1.104.1` project-remove frozen scheduler timeout repair. It does not carry forward the `v0.1.104.2`-`v0.1.104.6` experimental browser/source-add changes.

## Scope confirmation

No normal slice advances. `v0.1.105` remains deferred. No ChatGPT Project deletion is enabled. No Project Source behavior change, artifact adoption behavior change, deployment, Kubernetes mutation, repository-wide correction workflow, or patch/diff artifact generation is introduced.

## Validation expectation

Focused validation should prove version/control-surface alignment, the bounded scheduler test, sandbox mutation verification CLI smoke, Artifact Guardian, ZIP hygiene, and artifact verify. Full release-control/adoption remains required before this candidate can be accepted/current.

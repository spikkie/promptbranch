# v0.1.128.2.6.1.1.2 — Legacy release-control removal

Status: construction candidate; not accepted/current.

Accepted/current baseline: `v0.1.128.2.6.1.1.1` (`chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.1.zip`), SHA-256 `90c36f8065d0d343f7a7d6f8e6a11577f8e02ba683d24a026ccb48a755fc5926`.

Active candidate: `v0.1.128.2.6.1.1.2` (`chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.2.zip`).

This repair removes the obsolete `chatgpt_claudecode_workflow_release_control.sh` executable release engine. Current release authority is the canonical Python lifecycle: `scripts/run-release-lifecycle-proof.py` over `promptbranch_release_state_machine.py`. Remaining candidate-test, integrated MVP proof, installer bootstrap, Artifact Guardian, impact-map, behavioral-surface, and validation contracts are migrated to that authority. Legacy flag compatibility is intentionally not preserved.

`v0.1.129 — External application pilot bootstrap` remains the next normal slice and is blocked until this repair is accepted/current.

## Scope

- Delete the obsolete root shell release controller.
- Route full candidate testing directly to `pb test full --package-zip <exact candidate>`.
- Route integrated MVP release proof through `scripts/run-release-lifecycle-proof.py`.
- Reduce `install.sh` to a thin bootstrap into the canonical lifecycle.
- Remove the old controller from Artifact Guardian and current validation/impact contracts.
- Preserve historical release documentation as historical evidence only.

## Explicitly retired compatibility surface

Old partial-release toggles such as skip-install/skip-service/skip-tests, alternate service modes/transports, import-plan/dry-run-import, and shell-owned adoption flags are not recreated. Their release-authority semantics are superseded by state-machine invariants, direct `pb test` profiles, exact artifact binding, and durable lifecycle transitions.

## Construction validation

All 17 required deterministic release-validation groups are green by their exact constituent commands in the construction tree. The structural group is 62/62 green in one process; release-state-machine coverage is 124 passed with one documented canonical exact-candidate runtime-only skip. The final exact ZIP is additionally required to pass deterministic clean-extraction rebuild, Artifact Guardian, 62/62 structural coverage, control/removal contracts, and zero current executable/runtime references to the deleted shell controller. Live lifecycle/adoption remains pending.

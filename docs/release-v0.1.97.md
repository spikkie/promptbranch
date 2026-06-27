# Release v0.1.97 — Read-only loop evidence gate

## Type

Normal candidate.

## Baseline

Accepted/current baseline supplied by the operator: `chatgpt_claudecode_workflow-2_v0.1.96.zip`.

## Objective

Add a machine-checkable gate over the existing MVP-1 read-only loop evidence report so Promptbranch can make a deterministic pass/block decision before any future slice introduces real command execution.

## Changes

- Added `promptbranch.loop.read_only_evidence_gate` schema version `1.0`.
- Added `build_loop_read_only_evidence_gate()` to convert a read-only evidence report into a deterministic gate decision.
- Added `pb loop run --read-only-execution --evidence-gate`.
- Added JSON and text rendering for the evidence gate.
- Added gate checks for:
  - clean source evidence report,
  - read-only execution source schema,
  - no unsafe paths,
  - zero commands executed,
  - all declared validation commands skipped,
  - no file mutation,
  - no deployment,
  - no Kubernetes mutation,
  - no Project Source mutation,
  - no artifact adoption.
- The gate returns `gate_passed` / `continue_to_next_dry_run_step` only when all checks pass; otherwise it returns `gate_blocked` / `stop_for_operator_review`.

## Out of scope

- No validation command execution.
- No test execution by the loop engine.
- No file mutation by the loop engine.
- No deployment, Kubernetes, Docker push, Helm release, or external-system mutation.
- No Project Source mutation from loop execution.
- No artifact adoption from loop execution.
- No ChatGPT Project deletion.
- No change to `v0.1.96` generated ZIP retention behavior.

## Validation performed

Local candidate validation performed:

- `pytest -q tests/test_promptbranch_loop.py tests/test_cli_loop.py tests/test_promptbranch_version.py tests/test_project_control_surface.py` — passed.
- `python3 -m compileall -q promptbranch_loop.py promptbranch_cli.py promptbranch_version.py promptbranch_browser_auth promptbranch_automation promptbranch_container_api.py promptbranch_service_client.py` — passed.
- `bash -n chatgpt_claudecode_workflow_release_control.sh` — passed.
- CLI smoke: `python3 promptbranch_cli.py loop run --target examples/loop-targets/static-game-dry-run-target.json --read-only-execution --evidence-gate --json` — passed.
- Artifact Guardian and artifact verify must pass before handoff.

Full release-control/adoption is not performed by the candidate build.

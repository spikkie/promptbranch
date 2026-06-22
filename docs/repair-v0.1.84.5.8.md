# Repair v0.1.84.5.8 — browser service recovery after full-test ReadTimeout

## Base

- Accepted/current baseline remains `chatgpt_claudecode_workflow-2_v0.1.84.5.zip` until later adoption/current proof exists.
- Repair base: `v0.1.84.5.7` repair candidate.

## Reason

`v0.1.84.5.7` fixed the shared live Project ensure command, but the operator full run failed before that phase was exercised. The `full_direct` and `full_localhost` browser-backed test phases produced client-side `ReadTimeout` failures without 429/rate-limit evidence. The live profile preflight then also timed out while the browser service could still have been processing a previous timed-out request.

The release-control workflow needs bounded service recovery before continuing to the next browser-backed phase after this failure class.

## Changes

- Added strict `ReadTimeout`/`service_client_read_timeout` detection for run-all logs.
- Added `run_all_recover_service_after_browser_read_timeout`.
- After a failing `pb test full` transport step, release-control detects browser-service ReadTimeout evidence and recovers the Promptbranch service before the next browser-backed phase.
- Detached service mode restarts/recreates the service and re-verifies version.
- `--tests-only`/`--skip-service` records recovery intent but skips Docker/service mutation.
- `live_profile_preflight` now retries once after bounded service recovery when the preflight failure itself is a browser-service ReadTimeout.
- The original failing full-test step remains failed in the all-tests summary; recovery does not mask functional failures.

## Scope boundaries

No change to:

- Project deletion policy; deletion remains frozen.
- Ledger creation, ledger append, or `accept-event --write`.
- Project Source mutation behavior.
- Artifact adoption/current semantics.
- Deployment behavior.
- Model execution authority.

## Validation performed

- Focused release-control shell tests for browser ReadTimeout recovery detection.
- Focused release-control shell test for live preflight retry after service recovery.
- Focused release-control shell test proving a failing full transport remains failed while recovery is marked before later browser phases.
- Existing shared live Project tests.
- Existing recovered-rate-limit no-retry tests.
- Version/control-surface tests.
- `python3 -m compileall -q .`.
- `bash -n chatgpt_claudecode_workflow_release_control.sh`.
- `python3 promptbranch_cli.py orchestration validate-ledger --json`.
- Artifact Guardian.
- ZIP hygiene.

## Acceptance status

Repair candidate only. Not accepted/current without later full all-tests/adoption/current evidence.

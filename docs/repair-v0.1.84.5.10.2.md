# Repair v0.1.84.5.10.2 — direct retry restoration and recovered-rate-limit summary selection

## Repair metadata

- Base candidate: `chatgpt_claudecode_workflow-2_v0.1.84.5.10.1.zip`
- Repair version: `v0.1.84.5.10.2`
- Repair type: numeric repair component; no normal slice advancement
- Scope: release-control validation classification and retry policy only

## Reason

`v0.1.84.5.10.1` correctly denied browser cooldown retry for `full_localhost`, but its denylist also included `full_direct` / `direct`. The direct transport can execute browser-backed full-suite behavior and should not be classified as localhost/offline for this denylist.

The same run also showed `ask_live` ending in `all_tests_failed_steps` even though the command payload reported `ok=true` and `status=verified_with_recovered_rate_limit`. The all-tests summary reader selected the last JSON object found by raw brace scanning, which can be a nested helper/metadata object such as `profile_lease.metadata` instead of the top-level command result payload.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `VERSION`
- `promptbranch_version.py`
- `pyproject.toml`
- `tests/test_promptbranch_version.py`
- `docs/project/status.md`
- `docs/project/plan.md`
- `docs/project/release-status.md`
- `docs/project/definition-of-done.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/repair-v0.1.84.5.10.2.md`

## Behavior changes

- `full_localhost` and explicit localhost/offline validation step names remain denied from browser cooldown retry before cooldown parsing or generic waiting warnings.
- `full_direct` / `direct` are removed from the localhost/offline hard denylist.
- The all-tests summary JSON reader ranks top-level command result payloads above nested helper/metadata JSON objects discovered by raw brace scanning.
- `ok=true` plus `status=verified_with_recovered_rate_limit` remains green for live steps when selected from the actual command result payload.
- Unrecovered 429 evidence remains failing/retryable.

## Non-scope confirmation

This repair does not advance ledger/write/orchestration scope, does not mutate Project Sources, does not adopt artifacts/current state, does not deploy, does not enable ChatGPT Project deletion, and does not grant model execution authority.

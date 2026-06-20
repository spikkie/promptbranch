# Repair v0.1.78.2.20.3 — Large prompt-file attachment diagnostics flattening

## Base release

`chatgpt_claudecode_workflow-2_v0.1.78.2.20.2.zip`

## Repair version

`v0.1.78.2.20.3`

## Reason

The large prompt-file attachment transport added in `v0.1.78.2.20.2` worked for the CV RAG prompt package, but the successful JSON result still left required diagnostics nested or absent at the top level. Automated gates should not have to inspect unstable nested `submit_evidence` / `ask_phase_timings` structures to prove attachment upload/readiness, submit causality, and response causality.

## Scope

In scope:

- Flatten attachment upload/readiness diagnostics to top-level ask JSON fields.
- Flatten button-submit and submit-causality diagnostics to top-level ask JSON fields.
- Flatten response-causality and response-wait diagnostics to top-level ask JSON fields.
- Preserve the working large prompt-file attachment transport behavior from `v0.1.78.2.20.2`.

Out of scope:

- CV generator changes.
- Prompt-file transport redesign.
- Project Source add/remove behavior.
- Artifact registry/adoption redesign.
- Project deletion behavior.
- New normal release slice.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_cli.py`
- `promptbranch_container_api.py`
- `promptbranch_browser_auth/client.py`
- `scripts/smoke-pb-ask-large-prompt-file.sh`
- `tests/test_promptbranch_cli.py`
- `tests/test_response_completion.py`
- `tests/test_promptbranch_version.py`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/repair-v0.1.78.2.20.3.md`

## Validation performed

- Focused prompt-file attachment CLI diagnostics tests passed.
- Attachment visible-answer promotion diagnostics test passed.
- Project control-surface tests passed.
- Version-surface tests passed.
- Python compile checks passed.
- Bash syntax checks passed.
- ZIP integrity and hygiene checks passed before handoff.

## Slice state

No normal slice or line advanced. This is a repair-only release on the `v0.1.78.2.20.x` prompt-file repair line.

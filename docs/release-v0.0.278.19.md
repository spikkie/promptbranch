# Release v0.0.278.19

## Base release

Built from `chatgpt_claudecode_workflow_v0.0.278.18.zip`.

## Reason

`v0.0.278.18` still allowed stale JSON payloads to be returned on warm old tasks because DOM turn-index provenance could be falsely satisfied when the pre-submit baseline failed to see historical assistant turns.  The live failure returned an older `SUBMIT_CONFIRMATION_FAST_PATH_OK` payload even while reporting post-submit binding evidence.

## Change

This release requires JSON response freshness to be bound to the current request when a request-specific marker is available:

- extract explicit fresh markers from the submitted prompt, such as `sentinel`, `nonce`, `request_id`, or timestamped smoke tokens;
- when no explicit marker exists for a JSON ask, inject a `promptbranch_request_nonce` field into the model instructions;
- require the returned parsed JSON payload to contain the expected request marker/nonce;
- reject parseable stale JSON blocks that do not contain the current request marker, even if DOM turn binding claims freshness;
- strip an injected `promptbranch_request_nonce` from the returned answer before returning it to the caller;
- preserve warm-task hydration reuse, submit-confirmation fast path, and latest-turn fast return only after request-marker freshness is verified.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- `tests/test_promptbranch_cli.py`
- `docs/release-v0.0.278.19.md`

## Validation performed

- Python compile check over repository Python files.
- Focused pytest for browser client, container API, compose timeout policy, CLI parser, and version command.
- ZIP hygiene verification after packaging.

## Release boundary

No slice or line was advanced.  This is a correctness repair of the `.16` warm-task hydration line, canonicalized as a normal `.19` release because this workflow does not support fourth-field release versions.

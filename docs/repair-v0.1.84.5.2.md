# Repair v0.1.84.5.2 — live-test 429 telemetry propagation and non-clean classification

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.84.5.1.zip
```

## Repair version

```text
v0.1.84.5.2
```

## Reason

`v0.1.84.5.1` made mutation-capable live tests create fresh Projects directly and emit visual-roundtrip phase timings, but a separate defect remained: browser-layer `429` / ChatGPT "Too many requests" telemetry could be detected and persisted while ask-live or visual artifact roundtrip still reported a clean validation success.

For release-grade validation this is unsafe. A run that functionally completes while backend/history `429` or rate-limit modal telemetry was observed is rate-limit contaminated and must not be reported as clean `verified` / `ok=true`.

## Scope

- Add `rate_limit_telemetry` to the `/v1/ask` response model and preserve telemetry returned by the browser service.
- Preserve rate-limit telemetry in `pb test ask-live --json` step and suite payloads.
- Preserve ask/download/setup/cleanup rate-limit telemetry in `pb test visual-artifact-roundtrip --json` payloads.
- Classify otherwise functional ask-live and visual-roundtrip runs with backend/history `429` or rate-limit modal telemetry as `status=rate_limited_contaminated`, `ok=false`.
- Keep functional verification evidence visible through `functional_status`, `verification_status`, and artifact-intake details.

## Out of scope

- No ChatGPT Project deletion behavior change.
- No Project Source behavior change.
- No artifact adoption/current behavior change.
- No accepted-event ledger write behavior change.
- No deployment or model-execution authority change.
- No broad browser/backend REST refactor.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
promptbranch_container_api.py
promptbranch_cli.py
tests/test_promptbranch_container_api.py
tests/test_promptbranch_cli.py
tests/test_promptbranch_version.py
docs/project/status.md
docs/project/release-status.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/decisions.md
docs/project/migration.md
docs/repair-v0.1.84.5.2.md
```

## Validation performed

```text
python3 -m py_compile promptbranch_cli.py promptbranch_container_api.py promptbranch_service_client.py promptbranch_version.py tests/test_promptbranch_cli.py tests/test_promptbranch_container_api.py
pytest -q tests/test_promptbranch_container_api.py::test_ask_response_preserves_rate_limit_telemetry tests/test_promptbranch_cli.py::test_ask_live_downgrades_rate_limited_response tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_downgrades_rate_limit_contaminated_success tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_wraps_ask_and_artifact_intake tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_explicit_project_name_is_creation_label_not_lookup tests/test_promptbranch_version.py tests/test_project_control_surface.py
```

Focused validation result before packaging:

```text
13 passed
```

## Explicit confirmation

This is a repair-only candidate. It does not advance the accepted-event ledger slice, does not open a new normal release line, and does not mutate Project Source, artifact-current state, deployment state, or model-execution authority.

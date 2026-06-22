# Repair v0.1.84.5.3 — rate-limit telemetry aggregation deduplication

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.84.5.2.zip
```

## Repair version

```text
v0.1.84.5.3
```

## Reason

`v0.1.84.5.2` correctly classified otherwise functional live-test runs as non-clean when backend/history `429` or ChatGPT rate-limit modal telemetry was observed. A remaining evidence-quality defect double-counted the same browser download telemetry because visual artifact roundtrip passed both the direct download result and the smoke-verification artifact-intake result into the top-level telemetry aggregator.

The result classification was functionally correct, but top-level `cooldown_wait_seconds_total`, `cooldown_wait_count`, and `service_rate_limit_events` could be misleading.

## Scope

- Deduplicate event-backed rate-limit telemetry snapshots during aggregation.
- Deduplicate repeated `service_rate_limit_events` while preserving the first observed event payload.
- Preserve independent eventless counters such as separate navigation no-op skip counters.
- Preserve `rate_limited_contaminated` / `ok=false` classification when contamination is present.

## Out of scope

- No ChatGPT Project deletion behavior change.
- No Project creation identity behavior change.
- No `/v1/ask` response-model behavior change beyond existing telemetry propagation.
- No Project Source behavior change.
- No artifact adoption/current behavior change.
- No accepted-event ledger write behavior change.
- No deployment or model-execution authority change.
- No browser-context reuse or backend REST refactor.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
promptbranch_cli.py
tests/test_promptbranch_cli.py
tests/test_promptbranch_version.py
docs/project/status.md
docs/project/release-status.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/decisions.md
docs/project/migration.md
docs/repair-v0.1.84.5.3.md
```

## Validation performed

```text
python3 -m py_compile promptbranch_cli.py promptbranch_version.py tests/test_promptbranch_cli.py tests/test_promptbranch_version.py
pytest -q tests/test_promptbranch_cli.py::test_merge_rate_limit_telemetry_deduplicates_carried_download_snapshot tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_downgrades_rate_limit_contaminated_success tests/test_promptbranch_cli.py::test_ask_live_downgrades_rate_limited_response tests/test_promptbranch_version.py tests/test_project_control_surface.py
python3 promptbranch_cli.py artifact guard --zip /mnt/data/chatgpt_claudecode_workflow-2_v0.1.84.5.3.zip --version v0.1.84.5.3 --json
```

Focused validation result before packaging:

```text
11 passed
```

Artifact Guardian result after packaging:

```text
ok=true
status=guard_passed
failure_count=0
release_ready=true
```

## Explicit confirmation

This is a repair-only candidate. It does not advance the accepted-event ledger slice, does not open a new normal release line, and does not mutate Project Source, artifact-current state, deployment state, or model-execution authority.

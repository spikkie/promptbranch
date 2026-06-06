# Release v0.1.46

## Scope

Backend-first task/source read routing slice.

This release promotes the `v0.1.45` backend-read diagnostics into runtime read routing for the safe part of the surface:

- `pb task list` now performs a backend/indexed lightweight read first.
- `pb task list --deep-history` only uses the global history fallback when backend/indexed evidence is missing.
- `pb task list --json` reports `read_routing` so operators can see whether backend-first or fallback was used.
- `pb src list` / `pb project-source-list --json` reports `read_routing` and explicitly blocks backend-first claims when source provenance is missing.
- Source-list routing remains read-only and metadata-only; it does not pretend backend-first is available when the service payload is undifferentiated.

## Boundary

This release does not change source mutation, artifact adoption, scheduler execution, or release lifecycle behavior.

## Lightweight validation

```bash
python3 -m pytest -q \
  tests/test_promptbranch_backend_reads.py \
  tests/test_promptbranch_cli.py::test_chat_list_deep_history_skips_history_when_backend_indexed \
  tests/test_promptbranch_cli.py::test_chat_list_deep_history_uses_fallback_when_backend_missing \
  tests/test_promptbranch_cli.py::test_project_source_list_json_marks_metadata_gap_routing

python3 -m compileall -q .

pb task list --json | python3 -m json.tool
pb src list --json | python3 -m json.tool
pb debug backend-reads --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```

## Full-test trigger

Full tests are not required for this slice unless the task/source read routing causes a regression in live `pb task use`, `pb task show`, source mutation, or release lifecycle commands.

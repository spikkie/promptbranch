# Repair v0.0.245.5 — file-source overwrite pre-existing detection

Base release: v0.0.245.4
Repair version: v0.0.245.5

## Reason

`v0.0.245.4` fixed text-source persistence, but the full integration finalizer still failed on `project_source_overwrite_file`: the second upload of the same file source verified persistence but reported `already_exists=false`, `overwritten=false`, and `removed_existing=false`.

The failure indicated that the initial Sources-tab snapshot/preflight could be stale or empty even when the previous file-source add had already persisted. The overwrite flow therefore treated the second upload as a fresh add.

## Files changed

- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch.egg-info/PKG-INFO`

## Repair

Before treating a file-source overwrite as a fresh add, the overwrite preflight now performs a bounded read-only refresh/persistence verification using the exact file-source match candidates. If the existing file source appears after that verified re-read, the flow removes it and re-uploads so the result correctly reports:

```text
already_exists=true
overwritten=true
removed_existing=true
```

Final persistence verification after re-upload remains the authority.

## Validation performed

- Focused project-source capability tests, including the new stale/empty overwrite preflight regression.
- Python bytecode compilation for changed runtime and test files.
- ZIP CRC and hygiene checks before packaging.

No normal release scope was advanced.

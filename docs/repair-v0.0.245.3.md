# Repair v0.0.245.3

Base release: v0.0.245.2
Repair version: v0.0.245.3
Reason: repeated finalizer failures in `project_source_add_text` caused by strict quiet-save accounting after a text-source commit was observed while one relevant request remained stale/inflight.

Files changed:
- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- version metadata/runtime test files

Validation performed:
- Python compile checks for changed browser clients
- focused project-source quiet-wait regression tests
- focused version/runtime smoke tests
- ZIP CRC/hygiene/root-layout verification

Scope confirmation:
- No normal release scope advanced.
- No lifecycle phase advanced.
- No Project Source, artifact adoption, Docker, or protocol schema behavior was intentionally changed.

# Repair v0.1.54.1 — Project Source file persistence identity hardening

## Base release

`chatgpt_claudecode_workflow-2_v0.1.54.zip`

## Repair version

`chatgpt_claudecode_workflow-2_v0.1.54.1.zip`

## Reason

The v0.1.54 live `pb src add` result could report `persistence_verified=true` even when the post-refresh verifier matched a non-requested source-card identity such as `Sidebar ChatGPT` or generic metadata such as `File contents may not be accessible`.

The uploaded file could still appear later because ChatGPT Project Source persistence is eventually consistent, but the command result was too strong for the evidence available at return time.

## Files changed

- `chatgpt_browser_auth/client.py`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docs/repair-v0.1.54.1.md`

## Validation performed

```bash
python3 -m pytest -q tests/test_project_source_capabilities.py
python3 -m pytest -q tests/test_project_resolve.py
python3 -m compileall -q .
```

## Scope confirmation

This is a narrow repair release. It does not advance the orchestration slice, open a new line, change planned scope, redesign Project Source upload, or change artifact adoption behavior.

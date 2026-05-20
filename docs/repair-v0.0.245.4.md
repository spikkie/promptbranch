# Repair release v0.0.245.4

Base release: v0.0.245.3
Repair version: v0.0.245.4

## Reason

`v0.0.245.3` was active, but the final Artifact Intake MVP validation still failed in the browser full suite at `project_source_add_text` with `Timed out waiting for project source to appear`.

The failure was no longer the stale-inflight quiet-save case fixed in `v0.0.245.3`. The remaining defect was that text/file source add still treated the first visible-card wait as fatal and could abort before the post-save persistence verification pipeline had enough evidence to classify the outcome.

## Files changed

- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch.egg-info/PKG-INFO`
- `promptbranch_cli.py`

## Repair details

- Converted the initial text/file source-card wait into a short opportunistic probe.
- If the first visible-card probe times out, the flow now continues to post-save settle, save quiet, and persistence verification.
- Added text-source generic fallback persistence candidates such as `pasted.txt Document` and `pasted.txt` only when those identities were not present before the save.
- Added pre-refresh persistence verification before controlled refresh verification.
- Added structured persistence diagnostics with source-card snapshots, empty-state status, save-watch summary, and optional HTML/screenshot artifacts.

## Validation performed

- Focused project-source capability tests.
- Python compile check for changed runtime modules.
- ZIP hygiene and CRC verification before artifact delivery.

## Scope confirmation

This repair did not advance normal `v0.0.246` scope. It only repairs text/file Project Source post-save persistence verification behavior in the `v0.0.245` repair line.

# Release v0.1.60 — Project Source committed-write stability hardening

`v0.1.60` continues from accepted baseline `chatgpt_claudecode_workflow-2_v0.1.59.zip`.

## Problem

A live `promptbranch src add ib_forex_trading.0.247.3.1.zip` run returned HTTP 504 after ChatGPT accepted the upload/process commit requests, but the refreshed Sources tab did not show the source card before the verification timeout.

That failure mode is operationally risky for release-control scripts because a blind retry may create duplicates or repeat an overwrite while the remote Project Source state is still settling.

## Change

For file/text source adds, Promptbranch now distinguishes:

- verified persistence: refreshed Sources tab confirms the card;
- committed-but-unverified write: upload/process commit requests finished successfully, but refreshed DOM persistence did not verify before timeout;
- hard failure: no commit proof, failed request, browser/profile failure, auth failure, or overwrite/remove failure.

Committed-but-unverified writes now return structured JSON instead of surfacing as a transport-level 504:

```json
{
  "ok": true,
  "status": "source_add_triggered_not_verified",
  "persistence_verified": false,
  "project_source_mutated": true,
  "verification_mode": "commit_observed_unverified",
  "operator_review_required": true,
  "source_add_verification_required": true
}
```

This keeps existing shell scripts from aborting only because UI refresh verification lagged, while preserving an explicit warning that persistence was not proven.

## Files changed

- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- version surfaces

## Validation

```bash
python3 -m pytest -q tests/test_project_source_capabilities.py
python3 -m compileall -q .
```

Result:

```text
42 passed
compileall passed
```

## Operator guidance

When this status appears, do not immediately retry the same source add. First run:

```bash
promptbranch src list --json
```

If the source is visible, continue. If it is still absent after a later list, rerun source add once with overwrite enabled.

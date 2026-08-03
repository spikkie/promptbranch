# Release v0.1.121.1 — Backend 403/429 auth-bootstrap guardrail classification repair

## Purpose

Repair the strict release-control pre-Project-Source authentication bootstrap exposed by `v0.1.121`. The standard browser validation was authenticated and passed, but its telemetry contained conversation-history HTTP 429 events with the generic `backend_api_guardrail_seen=true` summary flag. The release wrapper treated that generic flag as proof of HTTP 403 and stopped before Project Source publication or tests.

## Changes

- Require an explicit structured `backend_api_guardrail` event whose numeric status is exactly `403` before classifying auth bootstrap as `browser_backend_403_guardrail`.
- Stop treating the generic `backend_api_guardrail_seen=true` summary flag as standalone 403 evidence.
- Treat malformed or missing guardrail status as non-403 evidence.
- Preserve explicit HTTP 429 telemetry as rate-limit evidence rather than challenge evidence.
- Add executable regressions that run the real shell detector against representative 429 and 403 bootstrap logs.
- Add those regressions to the mandatory `release_pipeline` validation group.

## Safety

This is a scope-neutral repair. It preserves all `v0.1.121` release-set reconciliation and resume behavior, does not add mutation authority, and does not weaken explicit backend 403 challenge handling. A real structured 403 event remains terminal and fail-closed.

## Baseline and next slice

- Accepted/current remains `v0.1.120.1` until strict adoption evidence proves this repair.
- Original `v0.1.121` bytes are repair-required and must not be adopted.
- The next normal slice after repair acceptance remains `v0.1.122 — Bounded parallel release-set wave execution and concurrency evidence`.

## Operator commands

Install candidate:

```bash
pipx install --force ./chatgpt_claudecode_workflow-2_v0.1.121.1.zip
pb --version
```

Run deterministic tests:

```bash
python3 scripts/run-release-validation-groups.py --repo . --json
```

Verify artifact:

```bash
sha256sum chatgpt_claudecode_workflow-2_v0.1.121.1.zip
unzip -t chatgpt_claudecode_workflow-2_v0.1.121.1.zip
python3 promptbranch_artifact_guardian.py \
  --repo . \
  --zip chatgpt_claudecode_workflow-2_v0.1.121.1.zip \
  --version v0.1.121.1 \
  --json
```

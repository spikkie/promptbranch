# Repair v0.1.78.2.20.6 — Dedicated generated document-name requirement for large text-source conversion

## Base candidate

`chatgpt_claudecode_workflow-2_v0.1.78.2.20.5.zip`

## Repair version

`v0.1.78.2.20.6`

## Reason

The `.20.5` focused source-add repro correctly failed closed when the saved text source was visible only as legacy `pasted.txt Document`. The operator clarified that current ChatGPT behavior no longer uses `pasted.txt` for new converted pasted text; current behavior should generate a dedicated document name. Therefore the verifier should not optimize for proving legacy `pasted.txt` content as the normal success path.

## Scope

- Treat `pasted.txt`, `pasted.txt Document`, and bare `Document` as legacy/stale cleanup noise for Project Source text-add validation.
- Do not add `pasted.txt` fallback candidates for current text-source persistence matching.
- Require large text-source document conversion to surface a dedicated/generated document identity containing the current run anchor.
- Preserve safe retained-test pruning of legacy generic text-source cards.
- Preserve prompt-file attachment mode and diagnostics from `.20.2`/`.20.3`.

## Files changed

- `promptbranch_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `tests/test_promptbranch_version.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/repair-v0.1.78.2.20.6.md`

## Validation performed

Local focused validation only:

```bash
python3 -m py_compile promptbranch_browser_auth/client.py promptbranch_full_integration_test.py promptbranch_version.py
python3 -m pytest -q \
  tests/test_project_source_capabilities.py \
  tests/test_project_resolve.py \
  tests/test_promptbranch_version.py \
  tests/test_project_control_surface.py
```

## Validation not performed

- Live focused `project_ensure + source_add_text` repro was not run by the assistant.
- Full release-control was not run by the assistant.
- Adoption/current verification was not run by the assistant.
- Full pytest was not run.

## No slice advancement

This is a repair release only. It does not advance the normal release line, does not open `v0.1.79`, and does not change Project deletion, artifact-current/adoption, CV generator, prompt-file transport, or release-control adoption behavior.

# Repair v0.1.78.2.20.5 — Generic document-converted text source content-proof gate

## Base release

`chatgpt_claudecode_workflow-2_v0.1.78.2.20.4.zip`

## Repair version

`v0.1.78.2.20.5`

## Reason

The `v0.1.78.2.20.4` focused `project_ensure + source_add_text` repro proved that the text-source save trigger and refreshed persistence path could pass, but it also showed the verifier accepted a generic `pasted.txt Document` card while `source_content_match_verified=false` and `generic_document_only=true`.

The operator clarified that ChatGPT may generate a dedicated `.txt` name for large pasted text instead of always using `pasted.txt`. The repair therefore only treats generic `pasted.txt` / `Document` identities as unsafe without current-run proof; dedicated generated names may still pass through the existing first-line/display-name candidate path when they carry the current run anchor.

## Scope

Changed only:

- Project Source text-add success classification for large document-converted text sources.
- Focused tests for generic document proof gating.
- Version metadata and project control-surface documentation.

Preserved:

- `pb ask --prompt-file` inline/attachment transport behavior from `v0.1.78.2.20.2` and `v0.1.78.2.20.3`.
- Release-control `--adopt-after-validation` behavior from `v0.1.78.2.20.1`.
- Project deletion freeze.
- Artifact registry/adoption semantics.
- Normal slice state; no move to `v0.1.79`.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `tests/test_promptbranch_version.py`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/repair-v0.1.78.2.20.5.md`

## Validation performed

Local focused validation:

```bash
python3 -m py_compile \
  promptbranch_browser_auth/client.py \
  promptbranch_full_integration_test.py \
  promptbranch_version.py

python3 -m pytest -q \
  tests/test_project_source_capabilities.py::test_text_source_document_conversion_requires_content_proof_for_generic_pasted_document \
  tests/test_project_source_capabilities.py::test_large_text_source_generic_pasted_document_requires_current_run_content_proof \
  tests/test_project_source_capabilities.py::test_text_source_document_conversion_content_proof_rejects_generic_old_pasted_document \
  tests/test_project_source_capabilities.py::test_text_source_document_conversion_content_proof_accepts_run_id_filename \
  tests/test_promptbranch_version.py
```

Result: `6 passed`.

Additional packaging validation must be performed by release-control and artifact adoption in the operator runtime.

## Acceptance expectation

A large text-source add that persists as a generic document must fail closed unless content proof ties the saved document to the current run id:

```json
{
  "ok": false,
  "status": "document_conversion_content_not_verified",
  "source_saved_as_document": true,
  "source_content_match_verified": false,
  "content_verification_release_blocking": true
}
```

A generated/dedicated `.txt` document name can pass when the visible identity contains the run anchor through the first-line/display-name candidate set.

## Explicit no-advance confirmation

This is a repair-only release. It does not advance the normal release line, active slice, MVP scope, artifact-current state, or Project Source baseline.

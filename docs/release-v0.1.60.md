# Release v0.1.60

## Summary

`v0.1.60` is a documentation and validation release built from accepted baseline `chatgpt_claudecode_workflow-2_v0.1.59.zip`.

It adds a release-checkable accepted-baseline evidence model so operators and future assistants can distinguish candidate ZIPs, transient sandbox ZIP checksums, installed runtime state, locally accepted Promptbranch artifacts, Project Source baselines, stale full-test evidence, and focused-validation evidence.

## Scope

In scope:

- add `docs/design/promptbranch-release-baseline-evidence.md`;
- extend `pb release docs-status` with a read-only `baseline_evidence` guard;
- add targeted tests for the baseline evidence document and docs-status payload;
- update release/version/current-status documentation to `v0.1.60`.

Out of scope:

- runtime behavior changes;
- source mutation changes;
- browser automation changes;
- backend API changes;
- artifact adoption behavior changes;
- new artifact intake/download behavior;
- full release lifecycle implementation.

## Validation

Focused validation for this candidate should include:

```bash
python3 -m pytest -q tests/test_promptbranch_release_baseline_evidence_doc.py
python3 -m pytest -q tests/test_promptbranch_application_design_doc.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_docs_status'
python3 promptbranch_cli.py release docs-status --version v0.1.60 --json
python3 -m compileall -q .
```

Full tests are not required by this slice unless local adoption policy demands them.

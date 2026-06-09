# Release v0.1.63 — Documentation site link-integrity guard

Release: `v0.1.63`

## Slice

PB documentation site link-integrity / navigation validation guard.

## Baseline

Built from accepted baseline `chatgpt_claudecode_workflow-2_v0.1.62.zip`.

## Scope

This release keeps the Material for MkDocs scaffold source-only and adds release-checkable link-integrity semantics to the `docs_site` guard. It verifies that `mkdocs.yml` navigation entries, documentation index links, and the living-design overview bridge resolve to repo-local files.

## Changed behavior

`pb release docs-status --json` now reports `docs_site.link_integrity` with checked links, missing targets, and repository-boundary status. Broken source documentation links become blockers.

## Non-goals

No rendered `site/` output is committed. No MkDocs build is required. No runtime CLI behavior, source mutation, browser automation, artifact adoption, or release lifecycle behavior changes are included.

## Validation focus

- `tests/test_promptbranch_docs_site_scaffold.py`
- `tests/test_promptbranch_living_design_html_doc.py`
- `tests/test_promptbranch_application_design_doc.py`
- `tests/test_promptbranch_release_baseline_evidence_doc.py`
- `tests/test_promptbranch_cli.py -k release_docs_status`
- `pb release docs-status --version v0.1.63 --json`
- `python3 -m compileall -q .`

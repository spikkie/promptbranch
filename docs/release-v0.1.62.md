# Release v0.1.62 — PB documentation site scaffold / navigation guard

Baseline: `chatgpt_claudecode_workflow-2_v0.1.61.zip`  
Target: `chatgpt_claudecode_workflow-2_v0.1.62.zip`  
Release type: normal  
Scope: documentation governance only

## Summary

`v0.1.62` adds a repo-owned documentation site scaffold using Material for MkDocs conventions. It creates one navigable documentation entrypoint for the existing PB design, living-design, baseline-evidence, current-status, and release-note surfaces.

The release does not build or package rendered `site/` output. The scaffold is source only.

## Added

```text
mkdocs.yml
docs/index.md
docs/design/index.md
docs/releases/index.md
docs/release-v0.1.62.md
tests/test_promptbranch_docs_site_scaffold.py
```

## Updated

```text
VERSION
pyproject.toml
promptbranch_version.py
promptbranch_cli.py
tests/test_promptbranch_cli.py
tests/test_promptbranch_application_design_doc.py
tests/test_promptbranch_living_design_html_doc.py
tests/test_promptbranch_release_baseline_evidence_doc.py
docs/design/promptbranch-application-design.md
docs/design/promptbranch-living-design-overview.html
docs/design/promptbranch-living-design-overview.md
docs/design/promptbranch-mvp-living-design.md
docs/design/promptbranch-mvp-gap-analysis.md
docs/design/promptbranch-release-baseline-evidence.md
docs/design/orchestration/docs/current_status.md
```

## Docs-status behavior

`pb release docs-status --version v0.1.62 --json` now includes a `docs_site` section. The guard verifies that:

- `mkdocs.yml` exists;
- the intended theme is Material for MkDocs;
- `docs/index.md`, `docs/design/index.md`, and `docs/releases/index.md` exist;
- the navigation links to the living-design overview, PB application design, release baseline evidence, MVP living design, MVP gap analysis, current status, and current release note;
- generated `site/` output is not committed;
- the guard is read-only and performs no source, artifact, or Project Source mutation.

## Validation

Focused validation for this slice:

```bash
python3 -m pytest -q tests/test_promptbranch_docs_site_scaffold.py
python3 -m pytest -q tests/test_promptbranch_living_design_html_doc.py
python3 -m pytest -q tests/test_promptbranch_application_design_doc.py
python3 -m pytest -q tests/test_promptbranch_release_baseline_evidence_doc.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_docs_status'
python3 promptbranch_cli.py release docs-status --version v0.1.62 --json
python3 -m compileall -q .
```

## Non-goals

```text
- no rendered site/ output
- no dependency installation
- no CI/CD publishing
- no GitHub Pages deployment
- no runtime CLI behavior change beyond read-only docs-status validation
- no source mutation behavior change
- no artifact adoption behavior change
```

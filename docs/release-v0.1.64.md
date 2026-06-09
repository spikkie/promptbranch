# Release v0.1.64 — Documentation site build-readiness guard

Release: `v0.1.64`

Target artifact: `chatgpt_claudecode_workflow-2_v0.1.64.zip`

Built from accepted baseline `chatgpt_claudecode_workflow-2_v0.1.63.zip`.

## Scope

`v0.1.64` extends the documentation-site governance line by adding a source-only build-readiness contract for the MkDocs scaffold.

The release adds `docs/site.md` and extends `pb release docs-status` so the `docs_site` section reports `build_readiness.ok=true` only when the repo documents:

- Material for MkDocs as the intended site framework.
- `mkdocs serve` as the local preview command.
- `mkdocs build` as the local build command.
- Generated `site/` output as forbidden committed/package source.
- `pb release docs-status --version v0.1.64 --json` as the release-checkable guard.

## Boundaries

This is a documentation-governance release only.

Out of scope:

- committed `site/` output
- GitHub Pages or other publishing automation
- mandatory MkDocs dependency installation
- runtime CLI behavior changes
- browser automation changes
- source mutation changes
- artifact adoption changes
- release lifecycle behavior changes

## Validation intent

The focused validation set should verify:

```bash
python3 -m pytest -q tests/test_promptbranch_docs_site_scaffold.py
python3 -m pytest -q tests/test_promptbranch_living_design_html_doc.py
python3 -m pytest -q tests/test_promptbranch_application_design_doc.py
python3 -m pytest -q tests/test_promptbranch_release_baseline_evidence_doc.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_docs_status'
python3 promptbranch_cli.py release docs-status --version v0.1.64 --json
python3 -m compileall -q .
```

Expected docs-status result:

```text
docs_site.ok=true
docs_site.link_integrity.ok=true
docs_site.build_readiness.ok=true
docs_site.generated_site_present=false
warning_codes=[]
blocker_codes=[]
```

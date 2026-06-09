# Release v0.1.61

## Summary

`v0.1.61` is a documentation and validation release built from accepted baseline `chatgpt_claudecode_workflow-2_v0.1.60.zip`.

It integrates the standalone Promptbranch living-design HTML overview into the repository and adds regression coverage proving that the HTML references the editable draw.io source and preserves the PB authority model.

## Scope

In scope:

- add `docs/design/promptbranch-living-design-overview.html`;
- add `docs/design/promptbranch-living-design-overview.md` as a repo-local bridge page;
- extend `pb release docs-status` with a `living_design_overview` guard;
- add `tests/test_promptbranch_living_design_html_doc.py`;
- update release/version/current-status documentation to `v0.1.61`.

Out of scope:

- runtime behavior changes;
- browser automation changes;
- source mutation changes;
- backend API changes;
- artifact adoption behavior changes;
- exported PNG/SVG regeneration;
- full documentation site generation.

## Validation

Focused validation:

```bash
python3 -m pytest -q tests/test_promptbranch_living_design_html_doc.py
python3 -m pytest -q tests/test_promptbranch_application_design_doc.py
python3 -m pytest -q tests/test_promptbranch_release_baseline_evidence_doc.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k release_docs_status
python3 promptbranch_cli.py release docs-status --version v0.1.61 --json
python3 -m compileall -q .
```

## Result

The HTML overview is now repo content and a release-checked documentation surface. It is not merely a standalone artifact.

# Release v0.1.8 — Living design docs-status validation

Base development head: `chatgpt_claudecode_workflow-2_v0.1.7.1.zip`
Target artifact: `chatgpt_claudecode_workflow-2_v0.1.8.zip`

## Scope

Add a read-only validation surface for the MVP living design documentation and editable draw.io source.

## Added

- `pb release docs-status --json`
- Markdown reference extraction for repo-relative design/documentation references.
- Editable draw.io XML parsing/diagram counting.
- Blockers for missing design document, missing/invalid draw.io source, and missing referenced files.
- Warnings for missing version marker, missing update-protocol phrase, or draw.io not listed in references.

## Updated documentation

- `docs/design/promptbranch-mvp-living-design.md`
- `docs/design/promptbranch-mvp-living-design.drawio`

## Non-goals

- No generated PNG/PDF/image artifact.
- No browser/service lifecycle mutation.
- No Project Source upload.
- No adoption or policy sync.

## Validation

Focused validation should include:

```bash
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_docs_status or release_checkpoint or release_dev_status or release_install_plan or release_lifecycle_plan or release_config or release_doctor'
python3 -m pytest -q tests/test_cli_parser.py -k 'release_docs_status or release_checkpoint or release_dev_status or release_install or release_lifecycle or release_config'
pb release docs-status --version v0.1.8 --json
```

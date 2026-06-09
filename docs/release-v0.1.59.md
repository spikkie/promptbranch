# Release v0.1.59 — PB application design docs-status freshness guard

## Summary

`v0.1.59` continues from accepted baseline
`chatgpt_claudecode_workflow-2_v0.1.58.zip` as a narrow documentation and
validation hardening slice.

The previous release added the PB application design document and extended the
editable draw.io files. This release makes that design surface part of the
read-only `pb release docs-status` gate so future releases cannot silently remove
or orphan the PB/ChatGPT role split, the workspace/task/artifact model, or the
required editable diagram pages.

## Baseline

```text
base artifact:   chatgpt_claudecode_workflow-2_v0.1.58.zip
target artifact: chatgpt_claudecode_workflow-2_v0.1.59.zip
release type:    normal
```

## Changes

### Version surfaces

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`

### Documentation

- `docs/design/promptbranch-application-design.md`
- `docs/design/promptbranch-mvp-living-design.md`
- `docs/design/promptbranch-mvp-gap-analysis.md`
- `docs/design/orchestration/docs/current_status.md`

### Validation

- `promptbranch_cli.py`
- `tests/test_promptbranch_application_design_doc.py`
- `tests/test_promptbranch_cli.py`

## Docs-status guard

`pb release docs-status --json` now validates the PB application design surface
in addition to the living MVP design Markdown and its editable draw.io source.

The guard checks that:

```text
- docs/design/promptbranch-application-design.md exists
- the expected release marker is present
- PB and ChatGPT roles remain explicitly documented
- workspace/task/artifact scope language remains present
- backend-first reads remain documented
- transactional writes remain documented
- accepted baseline / artifact continuity remains documented
- all required draw.io sources are referenced
- all required draw.io sources are parseable XML
- all required PB application diagram pages exist
```

Required draw.io pages:

```text
docs/design/promptbranch-class-diagram.drawio
  - PB Application Role Components

docs/design/promptbranch-mvp-living-design.drawio
  - PB Application Activity — pb and ChatGPT Roles
  - PB Application Data Flow
  - PB Application State Transitions

docs/diagrams/promptbranch-lifecycle/promptbranch_lifecycle_commands.drawio
  - PB Release State Transitions
```

## Non-goals

This release does not add:

```text
- runtime behavior changes
- source mutation changes
- artifact adoption changes
- browser automation changes
- backend API changes
- ChatGPT protocol changes
- exported PNG/SVG diagram rendering
- Kubernetes game implementation
- Ollama/local LLM execution authority
```

## Validation

Recommended focused validation:

```bash
python3 -m pytest -q tests/test_promptbranch_application_design_doc.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k "release_docs_status"
python3 promptbranch_cli.py release docs-status --version v0.1.59 --json
python3 -m compileall -q .
```

Expected result:

```text
targeted pytest: pass
docs-status: verified
warning_codes: []
blocker_codes: []
compileall: pass
```

Full tests were not run for this narrow documentation/validation slice.

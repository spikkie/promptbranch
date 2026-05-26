# Repair v0.0.276.7

## Base release

`chatgpt_claudecode_workflow_v0.0.276.6.zip`

## Repair version

`v0.0.276.7`

## Reason

Strict real-candidate validation still trusted an LLM-declared artifact inside the Promptbranch reply envelope too much.

A fresh-task rerun produced only JSON text containing:

```text
sandbox:/mnt/data/chatgpt_claudecode_workflow_v0.0.277.zip
```

The ChatGPT UI showed no downloadable ZIP attachment. The local runtime also did not download, verify, migrate, or adopt the candidate. Therefore the correct state was not "release candidate created"; it was "artifact declared in protocol JSON only".

## Files changed

- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- `docs/howto/15-finalize-artifact-intake-mvp.md`
- `docs/howto/16-manual-pb-command-use-cases.md`
- `docs/mvp-definition-of-done.md`
- version metadata surfaces (`VERSION`, `pyproject.toml`, `promptbranch_version.py`, `promptbranch.egg-info/PKG-INFO`)
- version-current tests
- `promptbranch.egg-info/SOURCES.txt`
- `docs/repair-v0.0.276.7.md`

## Repair behavior

`pb ask-release` now distinguishes a downloadable/materialized artifact from a JSON-only artifact declaration.

For strict release-candidate proof:

- `download.available=true` in the reply envelope is treated as an untrusted LLM claim.
- A `sandbox:/mnt/data/...` URL inside JSON does not count as downloadable proof by itself.
- A candidate must have either a directly downloadable URL (`file:`, `http:`, `https:`) or explicit host-detected attachment proof.
- JSON-only `sandbox:` candidates fail as `artifact_declared_but_not_attached`.
- The validation result includes `artifact_materialization_proven=false` and `manual_import_required=true` for this case.
- Parsed candidates are enriched with selected request/message/answer metadata so later diagnostics can trace the candidate back to the exact selected answer.

## Validation performed

- `python3 -m py_compile promptbranch_cli.py`
- Focused pytest for ask-release candidate validation:
  - rejects no-artifact reply
  - accepts one expected direct-download candidate
  - rejects JSON-only sandbox artifact declarations
- Focused pytest for protocol parsing and selected-answer metadata propagation.
- Focused pytest for version-current surfaces.
- ZIP layout and hygiene verification after packaging.

## Scope confirmation

No slice or line was advanced. This repair does not create a normal `v0.0.277` release, does not mutate Project Sources, does not adopt any candidate, does not change Git state, and does not add broad new artifact lifecycle scope. It only tightens strict real-candidate proof and fixes candidate provenance metadata.

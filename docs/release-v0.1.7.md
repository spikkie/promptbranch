# Release v0.1.7 — MVP living design documentation sources

## Base

Development continues monotonically from `chatgpt_claudecode_workflow-2_v0.1.6.zip`.

## Scope

This is a documentation-source release. It adds editable source artifacts that describe the current MVP architecture, current state, remaining tracks, and the CI-style development/adoption flow.

Added:

- `docs/design/promptbranch-mvp-living-design.md`
- `docs/design/promptbranch-mvp-living-design.drawio`

## Intent

The new draw.io file is a living design source. It is designed to be updated after each release slice and references current repo documentation files directly. It is not an exported/generated image.

The diagram covers:

- what Promptbranch is trying to achieve;
- the workspace/task/artifact state model;
- what has already been built/proven;
- the focused-development versus full-adoption checkpoint flow;
- remaining MVP tracks;
- documentation references;
- update protocol for future releases.

## Non-goals

This release does not:

- create generated images;
- create PDF exports;
- change runtime behavior;
- add Project Source mutation;
- run full browser/service tests;
- adopt an artifact;
- update the artifact registry;
- sync release policy;
- commit or push Git state.

## Validation

Focused validation performed during artifact creation:

- `python3 -m compileall -q .`
- XML parse check for `docs/design/promptbranch-mvp-living-design.drawio`
- repo-relative reference check for documentation links in `docs/design/promptbranch-mvp-living-design.md`
- ZIP reopen / CRC check
- ZIP root layout check
- ZIP hygiene check
- `VERSION` check for `v0.1.7`

# Release v0.0.259

## Scope

Normal release from accepted baseline `chatgpt_claudecode_workflow_v0.0.258.zip`.

This release keeps the artifact-intake behavior stable and removes stale version-specific wording from operator-facing artifact-intake diagnostics.

## Changes

- Bumped project/package version to `v0.0.259`.
- Reworded stale `v0.0.225` operator-facing artifact-intake messages into version-neutral diagnostics.
- Preserved the `sandbox:` transport classification and `--local-file` / `--manual-import-file` handoff path introduced in `v0.0.258`.
- Preserved strict real-candidate behavior; no-artifact replies still cannot satisfy `--require-real-candidate`.
- No adoption, Project Source mutation, Git commit, or Git push is performed by this candidate.

## Validation

- Python compilation.
- Focused CLI/parser tests.
- ZIP layout/hygiene verification.

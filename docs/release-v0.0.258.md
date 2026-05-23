# Release v0.0.258

## Scope

Normal release from accepted baseline `chatgpt_claudecode_workflow_v0.0.257.zip`.

This release makes artifact intake transport handling explicit for ChatGPT session-local artifact references.

## Changes

- Added artifact download transport classification for artifact intake.
- `sandbox:` artifact references now fail closed with `artifact_download_url_unsupported` instead of a generic download failure.
- Unsupported `sandbox:` references report `requires_browser_context=true` and include a manual-import handoff command.
- Added `pb artifact intake --local-file/--manual-import-file` to import a browser/session-downloaded ZIP into `.pb_profile/artifact_inbox/`.
- Manual imports can continue through the existing `--verify --migrate` candidate path.
- Preserved strict real-candidate behavior; no-artifact replies still cannot satisfy `--require-real-candidate`.
- No Git commit/push automation changes.

## Validation

- Python compilation.
- Parser test coverage for `--local-file`.
- Focused artifact-intake tests for:
  - explicit `sandbox:` rejection and browser-context handoff;
  - manual import, verification, and migration of a sandbox candidate.
- ZIP layout/hygiene verification.

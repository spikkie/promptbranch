# Repair v0.1.103.10.80

## Scope

- Reuse the exact health/version-verified candidate service during pre-source-add auth bootstrap with `--no-recreate`.
- Preserve Docker dependency cache by consuming release metadata only after stable browser dependencies and by removing the unconditional pre-source `--no-cache` build.
- Pin `patchright==1.58.2` and `playwright==1.52.0`.
- Retry Patchright Chrome installation once only for recognized transport failures.
- Classify exhausted browser dependency transport download as `docker_browser_dependency_download_failed`.
- Preserve v0.1.103.10.79 authoritative Project Sources preflight and early suffix rollback.

## Non-goals

- No Cloudflare/rate-limit bypass.
- No host-CDP/session-manager.
- No copied-profile trust.
- No adoption claim.

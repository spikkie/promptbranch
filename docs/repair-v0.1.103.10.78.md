# v0.1.103.10.78 — make pb src add exact-name idempotent and block suffix-renamed Project Source uploads

## Scope

- Keep the strict `install.sh` all-all gate from v0.1.103.10.69.
- Keep release-live sentinel normalization from v0.1.103.10.76.
- Treat duplicate-suffixed Project Source filenames as conflicts for normal `pb src add` / `pbsa`, not success evidence.
- Require exact canonical file basenames for successful file-source adds.
- Block visible suffix-renamed variants before upload to avoid creating the next `(n)` duplicate.
- If ChatGPT creates a suffix-renamed source after upload, return `backend_renamed_source` and keep the operation release-blocking.

## Non-goals

- No Cloudflare or rate-limit bypass.
- No host-CDP/session-manager path.
- No copied-profile trust.
- No broad Project Source backend cleanup is attempted unless a future repair can identify the new source unambiguously.

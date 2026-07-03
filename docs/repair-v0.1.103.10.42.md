# v0.1.103.10.42 — live ask targets conversation URL and fails fast on Cloudflare challenge

`v0.1.103.10.42` repairs the `v0.1.103.10.41` live-test blocker where release-control passed a ChatGPT Project home URL (`/project`) directly to `ask_live`. A Project page can be logged in and visible without exposing a chat composer; `ask_live` requires a conversation URL (`/c/...`).

## Scope

- Keep all-in-Docker browser execution.
- Keep explicit Docker live profile bootstrap from `v0.1.103.10.40`.
- Keep preservation of `.pb_profile_local_debug_pools` from `v0.1.103.10.41`.
- After `live_project_ensure`, create/open a live conversation inside the retained live Project and pass the `/c/...` URL to `ask_live`, `visual_artifact_roundtrip`, and `release_live`.
- If only `/project` is available, fail before `ask_live` with `live_conversation_url_missing`.
- If a live step observes a Cloudflare/Just-a-moment challenge, mark `docker_live_profile_challenged` and do not perform release-control retries.

## Out of scope

- Host-CDP/session-manager.
- Copied profile trust.
- Project Source mutation behavior changes.
- ChatGPT Project deletion.

# Release v0.0.278.76

Narrow visual artifact roundtrip prompt-hardening repair.

## Reason

`pb test visual-artifact-roundtrip` in v0.0.278.75 embedded a near-complete successful reply envelope with a placeholder URL. The ChatGPT-side model could satisfy the text protocol by returning a claimed `sandbox:/mnt/data/...` path without creating a real downloadable ZIP artifact.

## Scope

- Reword the visual artifact roundtrip prompt so success requires an actual downloadable ZIP artifact before the reply envelope.
- Remove the ready-to-copy successful envelope body from the prompt.
- Require the first response line to be a real Markdown download link to the created ZIP.
- Require `artifacts[0].download.url` to match the real Markdown link target.
- Keep retrieval verification through `pb artifact intake --download --verify-smoke-zip`.

## Non-goals

- No release/adoption behavior changes.
- No Project Source mutation changes.
- No normal ask-live behavior changes.

# Repair v0.1.103.10.83

## Goal

Make ChatGPT Library reconciliation authoritative and capture exact backing file identities from the live upload transaction while keeping `pbsa` unchanged.

## Behavior

- `pbsa <file>` still delegates to `promptbranch src add <file>`.
- Library active and filtered-empty surfaces require the configured stable observation count.
- The browser must be on the loaded Library route before an empty or nonempty result is authoritative.
- Recently deleted must be opened and independently proven authoritative; unavailable is release-blocking.
- Upload responses support JSON, nested objects, NDJSON, SSE/data lines, headers and redirect URLs.
- Bounded redacted response diagnostics record status, content type, body schema/sample, filenames and file IDs.
- A suffix upload without an exact backing file ID returns `library_backing_file_identity_missing`.
- With an exact ID, suffix rollback removes the Project Source, deletes the exact Library file, deletes it forever, verifies the ID absent and returns `library_collision_not_cleared`.
- Adoption remains refused unless the strict all-all verdict is `GO`.

## Acceptance command

```bash
cd /home/spikkie/git/platform-gitops
pbsa platform-gitops_v0.0.6.6.zip
```

Required success remains exactly one canonical Project Source, zero suffix variants and `persistence_verified=true`.

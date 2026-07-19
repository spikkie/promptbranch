# Release v0.1.104.4

Repair candidate for parse-independent visual response completion and bounded reply-envelope recovery.

## Changed

- Causally confirmed assistant virtualization may reduce visible turn count without causing a full response timeout.
- Visual response completion is based on stable latest text and authoritative idle UI, not successful protocol parsing.
- One deterministic visual-only normalization handles literal escaped outer whitespace.
- One same-conversation malformed-envelope retry is bounded to 90 seconds, uses no attachment, and has `retries=0`.
- Artifact download remains blocked until exactly one valid ZIP candidate with matching active IDs exists.

## Preserved

- Accepted/current baseline `v0.1.103.10.116`.
- Sandbox verifier and mandatory gate 3/10.
- Fresh `full_direct`, independent `full_localhost`, current-turn readiness, and one-reload recovery.
- Project Source, adoption, Artifact Guardian, and assigned-source verification behavior.

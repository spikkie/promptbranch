# Repair v0.1.78.2.10 — Rate-limit modal recovery and cooldown-aware run-all policy

This repair preserves the v0.1.78.2.9 Docker provenance guard and delete-frozen project policy while making ChatGPT conversation-history backpressure a first-class release-control condition.

## Scope

- Keep the browser-side "Too many requests" / "Got it" modal detection and acknowledgement path.
- Add release-control detection for rate-limit evidence in failed run-all step logs.
- Wait for the configured cooldown window before retrying the same failed step once.
- Append retry output to the same step log so the final JSON extractor sees the latest Promptbranch result.
- Preserve Docker host/image/container/health provenance checks.
- Preserve the retained delete-frozen test project policy.

## Out of scope

- Project deletion or secure delete protocol.
- Project Source behavior changes.
- Artifact adoption/current mutation.
- v0.1.79 / k8s-game work.

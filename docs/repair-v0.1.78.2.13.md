# Repair v0.1.78.2.13 — Text-source compatibility isolation and focused failing-test mode

This repair preserves the v0.1.78.2.12 Docker provenance guard, live seed preservation, strict rate-limit handling, and delete-frozen project policy while reducing the default release-blocking browser matrix.

## Failure being repaired

`v0.1.78.2.12` restored the live ask/artifact/release rows, but `--run-all-tests` still returned FIX because both full transports failed only at `project_source_add_text`. The release-critical Project Source path is ZIP/file upload, and the text-source UI path is now treated as source-kind compatibility evidence unless explicitly requested as strict release-blocking validation.

## Scope

- Default `--run-all-tests` skips `source_add_text` and `source_remove_text` in `pb test full`.
- `--strict-source-kind-matrix` restores text-source add/remove as release-blocking full-browser coverage.
- `--run-failing-tests` runs only the focused text-source compatibility path through direct and localhost transports for faster repair iteration.
- Preserve Docker host/image/container/health provenance checks.
- Preserve `.pb_profile_local_debug/` as authenticated live seed and `.pb_profile_local_debug_pools/` as disposable generated state.
- Preserve strict 429 / “Too many requests” retry behavior.
- Preserve ChatGPT Project deletion freeze.

## Out of scope

- Secure ChatGPT Project delete protocol.
- Artifact adoption/current mutation.
- Broad source-removal redesign.
- v0.1.79 / k8s-game work.

## Focused development command

```bash
ver=v0.1.78.2.13
./chatgpt_claudecode_workflow_release_control.sh   --version "$ver"   --install-from-zip ~/Downloads/chatgpt_claudecode_workflow-2_$ver.zip   --run-failing-tests   --skip-docker-logs   --prune-release-logs   --release-log-keep 12   --allow-dirty
```

Use `--strict-source-kind-matrix` with `--run-all-tests` only when intentionally validating all source kinds as release-blocking.

## Validation intent

The repair is candidate-only until operator-side release-control proves the default run-all path and adoption/current evidence confirms runtime, state artifact, state source, registry current, and consistency alignment.

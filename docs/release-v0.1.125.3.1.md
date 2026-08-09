# Release v0.1.125.3.1

## Classification

Repair release. Accepted/current remains `v0.1.124` until the exact candidate completes the canonical lifecycle and final convergence verification.

## Failure repaired

The first live `v0.1.125.3` run reached `CANDIDATE_REGISTERED` and then stopped at `RUNTIME_PREPARED`. Python ZIP extraction had not preserved the executable mode of `run_chatgpt_service.sh`, producing `PermissionError`. The original runtime executor also targeted the accepted service's Compose project and port, and timeout handling discarded partial Docker output.

## Runtime preparation contract

`v0.1.125.3.1` makes candidate runtime preparation isolated, observable and resumable:

- ZIP extraction preserves executable bits and explicitly verifies runtime scripts;
- each release attempt receives an isolated Compose project, candidate image and host port in `18000-18999`;
- the accepted service on port `8000` is snapshotted before candidate startup and verified unchanged afterward;
- candidate images carry exact version, artifact SHA-256, source fingerprint and release-attempt labels;
- runtime preparation persists a durable checkpoint after each phase;
- interrupted runs resume at the first incomplete phase instead of reinstalling or rebuilding completed phases;
- Docker build, start, health and identity failures use phase-specific failure codes;
- partial Docker output and diagnostic captures survive timeouts;
- candidate tests are bound to the isolated candidate service URL;
- the mandatory state-machine validation group contains a live Docker integration test that verifies candidate identity and accepted-runtime preservation.

## Runtime phases

```text
candidate_extracted
candidate_cli_installed
candidate_image_built
candidate_container_started
candidate_health_verified
candidate_identity_verified
```

## Failure codes

```text
runtime_pipx_missing
runtime_cli_install_timeout
runtime_cli_install_failed
runtime_candidate_identity_mismatch
runtime_image_build_timeout
runtime_image_build_failed
runtime_image_identity_mismatch
runtime_port_conflict
runtime_container_start_timeout
runtime_container_start_failed
runtime_container_missing
runtime_health_timeout
runtime_identity_mismatch
runtime_checkpoint_identity_conflict
```

## Canonical command

```bash
pb release run \
  --artifact chatgpt_claudecode_workflow-2_v0.1.125.3.1.zip \
  --version v0.1.125.3.1 \
  --baseline-version v0.1.124 \
  --release-type repair \
  --profile full \
  --test-timeout 3600 \
  --until final-verified \
  --adopt \
  --json
```

No Git commit, push or Project Source mutation occurs unless its positive authorization flag is supplied.

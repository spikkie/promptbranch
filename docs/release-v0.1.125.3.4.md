# Release v0.1.125.3.4

## Purpose

Repair the canonical release state machine so registry adoption cannot reach `FINAL_VERIFIED` while the authoritative Docker service on port `8000` still runs an older release.

## Baseline evidence

The control-plane registries accepted `v0.1.125.3.3`, but live inspection showed `promptbranch-service:0.1.125.2` still healthy on port `8000`, with isolated candidates `v0.1.125.3.2` and `v0.1.125.3.3` on high ports. A subsequent `release verify` still reported `FINAL_VERIFIED`, proving the missing live-runtime invariant.

## Repair contract

1. `ADOPTED_CURRENT` first requires exact accepted/current registry alignment.
2. The already-tested candidate image is retagged as the authoritative `promptbranch-service:<version>` image; no second build changes the tested bytes.
3. Only the canonical `chatgpt_claudecode_workflow` Compose service is recreated on port `8000`.
4. Production health must report the target version and production image labels must bind target version, artifact SHA-256, and release attempt ID.
5. Failed promotion attempts rollback to the previously healthy production image and remain retryable.
6. Successful promotion removes isolated `pb-candidate-*` service containers.
7. `FINAL_VERIFIED` and `release verify --all-states` independently re-probe the live port-8000 runtime.

## Canonical live command

```text
pb release run --artifact chatgpt_claudecode_workflow-2_v0.1.125.3.4.zip --version v0.1.125.3.4 --baseline-version v0.1.125.3.3 --release-type repair --profile full --test-timeout 3600 --until final-verified --adopt --json
```

No Git commit, push, or Project Source publication is implied.

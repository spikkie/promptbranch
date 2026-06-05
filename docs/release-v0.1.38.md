# Release v0.1.38

Base: `chatgpt_claudecode_workflow-2_v0.1.37.zip`

## Scope

Rebase the profile lease/pool solution onto the `chatgpt_claudecode_workflow-2` line so browser-backed task commands can run in parallel safely without opening the same Chromium/Patchright user-data-dir concurrently.

## Changes

- Added a local `PromptbranchProfileLease` that serializes direct profile access or leases cloned profile-pool slots.
- Added `--profile-pool`, `--profile-pool-size`, `--profile-pool-seed-dir`, `--profile-pool-refresh`, `--profile-lease`, `--no-profile-lease`, `--profile-lease-timeout-seconds`, and `--profile-lease-ttl-seconds` to browser-backed `pb task` commands.
- Added `pb test release-live --json` as an explicit live browser release gate that wraps `visual-artifact-roundtrip` and defaults to the `release-live` profile pool.
- Kept `pb test full` deterministic; the live browser release gate remains explicit.
- Kept Promptbranch state rooted at the operator's selected `--profile-dir` while browser automation uses the leased slot path.

## Usage

```bash
pb --profile-dir ./.pb_profile_local_debug \
  task list --json \
  --profile-pool tasks \
  --profile-pool-size 3
```

```bash
pb --profile-dir ./.pb_profile_local_debug \
  task show 1 --json \
  --profile-pool tasks \
  --profile-pool-size 3
```

```bash
pb test release-live --json \
  --profile-dir ./.pb_profile_local_debug
```

## Boundary

This release does not make one physical browser profile safe for concurrent opens. Parallel browser-backed `pb task` commands require cloned profile-pool slots. Docker/service-backed profile-pool routing remains out of scope because the service owns a container-local profile path.

## Validation

- `python3 -m compileall -q .`
- focused CLI parser/profile lease tests
- deterministic artifact-roundtrip smoke from the release tree
- ZIP layout and hygiene verification

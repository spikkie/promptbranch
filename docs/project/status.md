# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.77.11.zip
accepted checksum: 825e3b3a5e2d36214ddcdeb6f97ece8601a82f35322a34c96a6e3e2bab78af44
active repair candidate: chatgpt_claudecode_workflow-2_v0.1.78.2.3.zip
next normal target after accepted AG-001: chatgpt_claudecode_workflow-2_v0.1.79.zip
```

## Current MVP state

```text
MVP status: active
DoD status: in_progress
active plan slice: AG-001 — Deterministic Artifact Guardian Guard
active repair: v0.1.78.2.3 — Retained quarantine project for delete-frozen release tests
last completed slice: v0.1.77.11 repair line accepted/current
next planned slice: v0.1.79 — rebaselined JSON orchestration / k8s-game MVP foundation
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.78.2.3.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.78.zip failed release-control
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.77.11.zip
release status: v0.1.78.2 freezes ChatGPT Project deletion after v0.1.78.1 live-log delete evidence; not accepted/current
```

## Current risks

- Project deletion is now frozen because the current automation path can execute real ChatGPT project deletion; deletion must remain unavailable until a secure delete protocol exists.
- Project Source file uploads can reach commit-seen / stale-inflight / not-visible states that must remain release-blocking unless refreshed persistence is proven.
- Artifact Guardian must remain a structural ZIP guard only, not a build/heal/agent workflow.
- Guard-passed must not be confused with accepted/current adoption state.
- Project-specific ZIP requirements must remain policy-driven through `.artifact-guardian.yml`, not duplicated as hidden code constants.

## Current blockers

- v0.1.78.2.3 must pass focused release-control quarantine-project tests and release-control from ZIP.
- v0.1.78.2.3 must not be adopted/current without `pb artifact current --all --json` alignment evidence.
- Existing leaked `itest-promptbranch-*` projects from pre-fix runs remain manual cleanup until a secure delete protocol exists.

## Current unknowns

- What secure multi-factor delete protocol, if any, is acceptable for future ChatGPT Project deletion.
- Whether live ChatGPT file-source indexing will become visible within the extended post-commit readback window in release-control.
- Whether future lifecycle scripts should delegate their install ZIP checks to `pb artifact guard` in AG-005 or an earlier slice.

## Next safe action

```text
Package chatgpt_claudecode_workflow-2_v0.1.78.2.3.zip from v0.1.78.2.2 as a repair-only artifact, run focused release-control quarantine-project validation, then run release-control before adoption.
```

## Last updated

```text
v0.1.78.2.3 repair candidate build
```


## v0.1.78.2.1 repair status

`v0.1.78.2` release-control failed because `promptbranch_project_delete_safety.py` was present in the ZIP but missing from setuptools `py-modules`. `v0.1.78.2.1` is a packaging-only repair that makes the delete-safety helper importable after pipx installation. Project deletion remains frozen.


## v0.1.78.2.2 repair status

`v0.1.78.2.1` release-control failed before install-time validation because `chatgpt_claudecode_workflow_release_control.sh` only accepted three- or four-segment versions. `v0.1.78.2.2` widens release-control and post-release-validation version normalization to dotted numeric versions with at least three segments, including `v0.1.78.2.1`. Project deletion remains frozen.


## v0.1.78.2.3 repair status

`v0.1.78.2.2` release-control succeeded but retained a newly created unique `itest-promptbranch-<run-id>` project because ChatGPT Project deletion is frozen. `v0.1.78.2.3` changes release-control live tests to reuse one retained quarantine project named `itest-promptbranch-retained-delete-frozen` by default and passes `--keep-project`, preventing a new undeletable project from being created on every release-control run. Existing leaked `itest-promptbranch-*` projects are not deleted by this repair.

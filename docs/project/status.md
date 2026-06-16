# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.77.11.zip
accepted checksum: 825e3b3a5e2d36214ddcdeb6f97ece8601a82f35322a34c96a6e3e2bab78af44
active repair candidate: chatgpt_claudecode_workflow-2_v0.1.78.1.zip
next normal target after accepted AG-001: chatgpt_claudecode_workflow-2_v0.1.79.zip
```

## Current MVP state

```text
MVP status: active
DoD status: in_progress
active plan slice: AG-001 — Deterministic Artifact Guardian Guard
active repair: v0.1.78.1 — Project Source mutation transaction hardening
last completed slice: v0.1.77.11 repair line accepted/current
next planned slice: v0.1.79 — rebaselined JSON orchestration / k8s-game MVP foundation
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.78.1.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.78.zip failed release-control
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.77.11.zip
release status: v0.1.78.1 repairs v0.1.78 Project Source file persistence validation/reporting failure; not accepted/current
```

## Current risks

- Project Source file uploads can reach commit-seen / stale-inflight / not-visible states that must remain release-blocking unless refreshed persistence is proven.
- Artifact Guardian must remain a structural ZIP guard only, not a build/heal/agent workflow.
- Guard-passed must not be confused with accepted/current adoption state.
- Project-specific ZIP requirements must remain policy-driven through `.artifact-guardian.yml`, not duplicated as hidden code constants.

## Current blockers

- v0.1.78.1 must pass focused repair tests and release-control from ZIP.
- v0.1.78.1 must not be adopted/current without `pb artifact current --all --json` alignment evidence.

## Current unknowns

- Whether live ChatGPT file-source indexing will become visible within the extended post-commit readback window in release-control.
- Whether future lifecycle scripts should delegate their install ZIP checks to `pb artifact guard` in AG-005 or an earlier slice.

## Next safe action

```text
Package chatgpt_claudecode_workflow-2_v0.1.78.1.zip from v0.1.78 as a repair-only artifact, run focused repair validation, then run release-control before adoption.
```

## Last updated

```text
v0.1.78.1 repair candidate build
```

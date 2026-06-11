# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.73.1.zip
accepted checksum: 3a032f2470a74903f6f61f9dbdf63dbf98e3154e2fd146e6ea9a757cf7941554
next repair target: chatgpt_claudecode_workflow-2_v0.1.73.2.zip
next normal target after repair adoption: chatgpt_claudecode_workflow-2_v0.1.74.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-024 done where evidence is listed; adoption-specific rows remain release-scoped
active plan slice: v0.1.73.2 repair — Validation/reporting regressions from v0.1.73.1
last completed accepted baseline: v0.1.73.1 — Canonical artifact adoption diagnostics and external-repo status semantics
next planned slice: install/test/adopt v0.1.73.2, then continue normal development at v0.1.74
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.73.2.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.73.1.zip based on provided release workflow evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.73.1.zip based on pb artifact current --json evidence
release status: v0.1.73.2 repair candidate in progress
```

## Current risks

- v0.1.73.1 full release workflow completed with exit_code 0, but a later focused regression command found stale/contract tests outside that path.
- The full release test path must include the public JSON contract regressions for artifact adoption/current/baseline status.
- External repo baselines must show registry/state alignment while still marking runtime-code comparison as not applicable.

## Current blockers

- v0.1.73.2 requires local install/test/adoption evidence before it can become accepted/current.

## Current unknowns

- Whether the operator will keep candlecast-src at v0.19.5.92.2 or later replace it with v0.19.5.94.1.

## Next safe action

```text
Package chatgpt_claudecode_workflow-2_v0.1.73.2.zip as a narrow repair and run focused regression tests plus release-control validation before adoption.
```

## Last updated

```text
v0.1.73.2 repair candidate
```

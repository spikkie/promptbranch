# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.75.zip
accepted checksum: d8e7b00c6ad1e25ee549166a4298707fd7ece47c1c44f32b95fcfe66ddf70e8b
next normal target: chatgpt_claudecode_workflow-2_v0.1.76.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-032 done where evidence is listed; adoption-related rows remain release-specific until adoption evidence exists
active plan slice: v0.1.76 normal — KISS repo-loop consumer cleanup for operator scripts and release-state checks
last completed slice: v0.1.75 accepted/current KISS repo-loop management model
next planned slice: install/test v0.1.76, then adopt only after release-control and pb artifact current evidence are green
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.76.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.75.zip
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.75.zip
release status: v0.1.76 candidate; not accepted/current
```

## Current risks

- Any remaining consumer that reads top-level `state` or `registry_current` from joined-project `pb artifact current --json` can break the KISS model.
- Legacy top-level artifact-current parsing should remain a compatibility fallback only, not the normal operator path.
- Candidate ZIPs must not be treated as accepted/current until adoption evidence confirms alignment.

## Current blockers

- v0.1.76 requires full release-control install/test evidence before it can become accepted/current.

## Current unknowns

- Whether local external scripts outside this repository still assume legacy single-repo `artifact current` JSON for joined projects.
- Whether live browser or service rate limits will affect the v0.1.76 release-control run.

## Next safe action

```text
Run release-control for chatgpt_claudecode_workflow-2_v0.1.76.zip, then adopt only after pb artifact current --all --json confirms alignment.
```

## Last updated

```text
v0.1.76 candidate
```

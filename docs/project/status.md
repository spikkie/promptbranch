# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.76.zip
accepted checksum: 27030674c5af1b1d9d5199e638b55c2d3beed4b7df36175082e107992721d96f
next normal target: chatgpt_claudecode_workflow-2_v0.1.77.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-033 done where evidence is listed; adoption-related rows remain release-specific until adoption evidence exists
active plan slice: v0.1.77 normal — repo-loop compatibility hardening and operator migration guardrails
last completed slice: v0.1.76 accepted/current KISS repo-loop consumer cleanup for operator/release scripts and release-state checks
next planned slice: install/test v0.1.77, then adopt only after release-control and pb artifact current evidence are green
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.77.zip candidate once packaged
latest installed ZIP: chatgpt_claudecode_workflow-2_v0.1.76.zip
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.76.zip
release status: v0.1.77 candidate once packaged; not accepted/current
```

## Current risks

- External/local operator scripts outside this repository may still parse old top-level `state`, `registry_current`, `baseline_roles`, or `runtime` fields.
- Legacy top-level artifact-current parsing should remain a compatibility fallback only, not the normal operator path.
- Candidate ZIPs must not be treated as accepted/current until adoption evidence confirms alignment.

## Current blockers

- v0.1.77 requires full release-control install/test evidence before it can become accepted/current.

## Current unknowns

- Whether downstream operator tooling outside this repository has fully removed legacy single-repo `artifact current` JSON assumptions.
- Whether live browser or service rate limits will affect the v0.1.77 release-control run.

## Next safe action

```text
Run release-control for chatgpt_claudecode_workflow-2_v0.1.77.zip, then adopt only after pb artifact current --all --json confirms alignment.
```

## Last updated

```text
v0.1.77 candidate
```

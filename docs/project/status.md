# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.71.5.zip
accepted checksum: c04b23d8a35bd07d1cb106a52beb0cf6d5e06ee788fec76ff69f0abd0d37d13c
next normal target: chatgpt_claudecode_workflow-2_v0.1.72.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-021 done where evidence is listed; adoption-specific rows remain dependent on operator evidence per release
active plan slice: v0.1.72 normal — Project registry adoption/import ergonomics
last completed slice with adoption evidence: v0.1.71.5 repair — VERSION_TAG double-v normalization
next planned slice: install/test/adopt v0.1.72, then select the next risk-controlled normal slice
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.72.zip candidate
latest installed ZIP: unknown until operator lifecycle evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.71.5.zip
release status: v0.1.72 candidate, not accepted/current
```

## Current risks

- Registry import touches project-scoped artifact current-state and state snapshots; conflicts must fail closed unless the operator explicitly passes `--replace`.
- v0.1.72 introduces migration ergonomics but still must not perform automatic artifact adoption or Project Source mutation.
- Full test suite has not been run for this candidate by the assistant.

## Current blockers

- v0.1.72 requires local release-control install/test/adoption evidence before it can become accepted/current.

## Current unknowns

- Whether project registry import should later include a richer multi-profile discovery command.
- Whether joined repositories should expose a guided onboarding wizard after this explicit import path is accepted.

## Next safe action

```text
Install/test chatgpt_claudecode_workflow-2_v0.1.72.zip with release-control. Then from joined Kubernetes repos run pb project import-current-registry --dry-run --json before importing legacy repo-local current records.
```

## Last updated

```text
v0.1.72 candidate
```

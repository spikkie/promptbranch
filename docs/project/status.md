# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.71.zip (operator stated fully tested/adopted; explicit checksum evidence not recorded in this file)
latest failed repair candidates: chatgpt_claudecode_workflow-2_v0.1.71.1.zip missing `.gitignore`; chatgpt_claudecode_workflow-2_v0.1.71.2.zip packaged protected `.pb_profile/`; chatgpt_claudecode_workflow-2_v0.1.71.3.zip hit service health version-format mismatch
current repair candidate: chatgpt_claudecode_workflow-2_v0.1.71.4.zip
next normal target: chatgpt_claudecode_workflow-2_v0.1.72.zip after repair adoption
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: DOD-001..DOD-019 done where evidence is listed; adoption-specific rows remain dependent on operator evidence
active plan slice: v0.1.71.4 repair — service health version normalization
last completed slice with adoption evidence: v0.1.71 by operator statement; explicit adoption JSON not recorded here
next planned slice: validate/adopt v0.1.71.4, then choose next normal v0.1.72 slice
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.71.4.zip candidate
latest installed ZIP: unknown until operator lifecycle evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.71.zip by operator statement; explicit adoption JSON not recorded here
release status: v0.1.71.4 repair candidate, not accepted/current
```

## Current risks

- v0.1.71.4 changes the release-control service health comparison only; the real lifecycle must prove the Docker service wait gate now accepts canonical `v` service versions.
- Full test suite has not been run for this repair candidate by the assistant.
- Explicit v0.1.71 adoption JSON/checksum is not recorded in this file.

## Current blockers

- v0.1.71.4 requires local release-control install/test/adoption evidence before it can become accepted/current.

## Current unknowns

- Whether future health endpoints should expose both `package_version` and canonical `version` to remove ambiguity.
- Whether migration tooling for existing repo-local registries should become a separate v0.1.72 slice.

## Next safe action

```text
Install/test chatgpt_claudecode_workflow-2_v0.1.71.4.zip with release-control. Confirm the service health/version gate accepts health JSON containing `version: v0.1.71.4` when the expected package version is `0.1.71.4`.
```

## Last updated

```text
v0.1.71.4 repair candidate
```

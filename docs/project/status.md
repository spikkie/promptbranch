# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.70.1.zip
accepted checksum: 24be7e1c993d69ffb3ae50fbd50a45edf8a1af07ed616b107ef895698fc1ed33
next normal target: chatgpt_claudecode_workflow-2_v0.1.71.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: project-control-surface rows done; source-add diagnostics done; browser-idle barrier done; multi-repo artifact current-state done/adopted; missing-repo fallback repair done/adopted; project-scoped multi-repo registry resolution done in candidate after focused validation
active plan slice: v0.1.71 normal — project-scoped multi-repo registry resolution
last completed slice with adoption evidence: v0.1.70.1 Missing repo artifact-current fallback repair
next planned slice: after v0.1.71 adoption, choose next risk-controlled multi-repo or lifecycle hardening slice
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.71.zip candidate after this slice is packaged
latest installed ZIP: unknown until operator lifecycle evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.70.1.zip
release status: v0.1.71 normal candidate, not accepted/current
```

## Current risks

- v0.1.71 changes artifact registry resolution for joined repos from repo-local `.pb_profile` convention to project-scoped user-local state; explicit `--profile-dir` remains the debug/override path.
- Existing repo-local `.pb_profile/promptbranch_artifacts.json` state is not automatically migrated; operators must join repos and adopt/register artifacts into the project registry or keep using `--profile-dir` while migrating.
- Full test suite has not been run for this candidate.

## Current blockers

- None for the v0.1.71 candidate build.

## Current unknowns

- Whether migration tooling for existing repo-local registries should become a separate v0.1.72 slice.
- Whether release-set/dependency orchestration should be introduced after project-scoped registry resolution stabilizes.

## Next safe action

```text
Install/test chatgpt_claudecode_workflow-2_v0.1.71.zip as a normal candidate. From each Kubernetes repo, run `pb project join ...`, then verify `pb artifact current --all --json`, `pb repo list --json`, and `pb repo doctor --json` resolve the same project registry without passing `--profile-dir`.
```

## Last updated

```text
v0.1.71 candidate
```

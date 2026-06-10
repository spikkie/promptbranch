# Project Status

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.71.zip (operator stated fully tested/adopted; checksum evidence not recorded in this file)
accepted checksum: pending explicit v0.1.71 adoption evidence block
next normal target: chatgpt_claudecode_workflow-2_v0.1.72.zip
```

## Current MVP state

```text
MVP status: active, not complete
DoD status: project-control-surface rows done; source-add diagnostics done; browser-idle barrier done; multi-repo artifact current-state done/adopted; missing-repo fallback repair done/adopted; project-scoped multi-repo registry resolution repaired in v0.1.71.1 candidate after focused validation; v0.1.71.2 repairs missing required root `.gitignore` packaging defect
active plan slice: v0.1.71.2 repair — restore required root `.gitignore` in v0.1.71.1 packaging
last completed slice with adoption evidence: v0.1.71 by operator statement; explicit adoption JSON not recorded here
next planned slice: after v0.1.71.1 adoption, choose next risk-controlled multi-repo or lifecycle hardening slice
```

## Current release state

```text
latest created ZIP: chatgpt_claudecode_workflow-2_v0.1.71.2.zip candidate after this repair is packaged
latest installed ZIP: unknown until operator lifecycle evidence
latest accepted/current ZIP: chatgpt_claudecode_workflow-2_v0.1.71.zip by operator statement; explicit adoption JSON not recorded here
release status: v0.1.71.2 repair candidate, not accepted/current; v0.1.71.1 rejected by install ZIP import guard because `.gitignore` was missing
```

## Current risks

- v0.1.71.1 fixes a high-risk registry split where project/repo commands could read the new project registry but artifact-current still read the repo-local profile when `args.profile_dir` had only been default-resolved.
- Existing repo-local `.pb_profile/promptbranch_artifacts.json` state is not automatically migrated by this repair; operators must adopt/register artifacts into the project registry or use an explicit `--profile-dir` during migration.
- Full test suite has not been run for this repair candidate.

## Current blockers

- None for the v0.1.71.1 repair candidate build.

## Current unknowns

- Whether migration tooling for existing repo-local registries should become a separate v0.1.72 slice.
- Whether `pb project join --from-current` should be added later to reduce manual operator input.

## Next safe action

```text
Install/test chatgpt_claudecode_workflow-2_v0.1.71.1.zip as a repair candidate. From each joined Kubernetes repo, verify `pb artifact current --all --json`, `pb repo list --json`, and `pb repo doctor --json` report the same project registry path without passing `--profile-dir`.
```

## Last updated

```text
v0.1.71.1 repair candidate
```


## v0.1.71.2 repair note

```text
The v0.1.71.1 ZIP failed install verification because required root `.gitignore` was missing. v0.1.71.2 restores `.gitignore` and preserves v0.1.71.1 behavior without advancing the normal release line.
```

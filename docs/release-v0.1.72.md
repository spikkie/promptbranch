# Release v0.1.72 — Project registry adoption/import ergonomics

## Type

```text
normal candidate
```

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.71.5.zip
```

## Goal

Make project-scoped multi-repo registries easier and safer to initialize from existing repo-local Promptbranch state without manual file copying or implicit adoption.

## In scope

- Add `pb project import-current-registry`.
- Default the import source to the joined repo's `.pb_profile`.
- Support `--from-profile-dir` for explicit legacy profile import.
- Support `--dry-run` for non-mutating import plans.
- Fail closed on conflicts unless `--replace` is explicitly provided.
- Import project current artifact records and repo-scoped project state.
- Add focused tests for dry-run, successful import, and conflict handling.
- Update multi-repo project docs and project control-surface status.

## Out of scope

- Release-set orchestration.
- Cross-repo dependency solving.
- Automatic Project Source upload.
- Automatic artifact adoption.
- Deployment behavior.
- Docker behavior.
- Broad lifecycle rewrite.

## Validation

```text
focused project/repo import tests
project control-surface tests
source version consistency
package import smoke
compileall
ZIP hygiene
clean extraction validation
```

## Acceptance rule

This ZIP is a candidate until operator lifecycle/adoption evidence confirms runtime, state artifact, state source, registry current, and consistency alignment.

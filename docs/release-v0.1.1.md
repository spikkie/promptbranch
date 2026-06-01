# Release v0.1.1 — Worktree artifact identity and Docker Compose instance isolation

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.0.zip
```

This release is rebuilt from the explicitly pinned `chatgpt_claudecode_workflow-2_v0.1.0.zip` baseline.

## Purpose

Fix release-control and Docker Compose behavior for Git worktree operation.

The release-control script must not mix a worktree-derived artifact filename with a hardcoded canonical filename during packaging, verification, source upload, install, or adoption.

Docker runtime identity must be instance-specific so two worktrees can run on the same machine.

## Changes

- Release artifact prefix is derived from `--install-from-zip` when provided.
- `chatgpt_claudecode_workflow-2_v0.1.0.zip` now leads to `chatgpt_claudecode_workflow-2_v0.1.1.zip`.
- Version parsing accepts arbitrary `<artifact-prefix>_vX.Y.Z.zip` transport names.
- Download ZIP resolution no longer hardcodes a single artifact prefix.
- Packager output normalization recognizes artifact prefix, repo basename, legacy project name, source-prefixed names, and git-sha fallback names.
- Old transported/canonical ZIPs are removed before packaging so verification cannot validate the wrong ZIP.
- `rsync` excludes both `.git` and `.git/` during ZIP import.
- Compose runtime identity uses `COMPOSE_PROJECT_NAME` / `PROMPTBRANCH_COMPOSE_PROJECT_NAME`.
- Service host port uses `PROMPTBRANCH_SERVICE_PORT`.
- Compose bind mounts for `.pb_profile` and `debug_artifacts` are parameterized.

## Runtime example

```bash
COMPOSE_PROJECT_NAME=promptbranch_v011 PROMPTBRANCH_SERVICE_PORT=8010 ./chatgpt_claudecode_workflow_release_control.sh   --version v0.1.1   --install-from-zip ~/Downloads/chatgpt_claudecode_workflow-2_v0.1.1.zip   --skip-source-add   --skip-tests   --skip-docker-logs
```

## Non-goals

- Does not fix ChatGPT Project Sources tab visibility failures.
- Does not add the `promptbranch.orchestration.grill` runtime validator.
- Does not advance the JSON Orchestration State MVP beyond the worktree/runtime release-control repair.

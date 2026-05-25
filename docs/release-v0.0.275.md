# Release v0.0.275

Base: `chatgpt_claudecode_workflow_v0.0.274.zip`

## Scope

Add a reusable read-only Promptbranch final MVP skill for tool consumers.

## Changes

- Add built-in `promptbranch-final-mvp` skill metadata and procedure.
- Add repo-local `.promptbranch/skills/promptbranch-final-mvp/SKILL.md` so external tools can discover the skill from the repository surface.
- Wire `pb agent run --skill promptbranch-final-mvp "inspect final MVP" --json` to a deterministic read-only tool plan:
  - `filesystem.read` for `VERSION`
  - `filesystem.read` for `docs/mvp-definition-of-done.md`
  - `filesystem.read` for `docs/promptbranch_mvp_current_state_and_plan_2026-05-24.md`
  - `artifact.registry.current`
  - `git.status`
  - `git.diff.summary`
- Add a structured `promptbranch_final_mvp` report with document visibility checks, artifact-current visibility, working-tree state, blockers, warnings, and non-mutating safe next actions.
- Update the MVP current-state document to include the final-MVP skill in the read-only skills track.

## Non-goals

- No source upload, artifact intake, candidate migration, adoption, Git, or browser automation changes.
- No write-capable agent/MCP tool exposure.
- No full final MVP enforcement gate; this is an inspectable skill/report surface.

## Validation

- `python3 -m compileall -q .`
- focused Promptbranch MCP skill tests for `promptbranch-final-mvp`
- package hygiene checks before ZIP creation

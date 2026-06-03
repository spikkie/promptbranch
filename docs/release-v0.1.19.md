# Release v0.1.19

## Baseline

Built from the accepted repair baseline:

```text
chatgpt_claudecode_workflow-2_v0.1.18.1.zip
```

The repair baseline was adopted after full release-control passed, so this normal release intentionally continues from `v0.1.18.1` rather than from the original `v0.1.18`.

## Scope

Read-only release-status UX hardening.

`pb release status-guide --json` now exposes a post-adoption next-normal release plan after runtime/source/artifact/registry alignment is confirmed.

## Changes

- Adds post-adoption `next_normal_release_plan` guidance to the status-guide `recommended_sequence`.
- Adds post-adoption `next_normal_status_guide_after_build` guidance for the next candidate artifact.
- Adds command-guide entries for the next-normal status-guide and checkpoint commands.
- Adds operator-runbook fields:
  - `post_adoption_ready_for_next_normal`
  - `development_base_version`
  - `next_normal_version`
  - `next_normal_artifact`
- Updates the living design Markdown and editable `.drawio` source only.

## Non-goals

This release does not install, test, adopt, upload project sources, update artifact state, commit Git changes, or push Git state from `status-guide`.

## Validation

Focused local validation was run before packaging:

```text
pytest status-guide focused tests
pytest CLI parser focused tests
compileall
release docs-status
release config
release install --plan
release lifecycle --plan
release checkpoint --mode continue
release status-guide
release-control --import-plan
ZIP reopen / CRC / VERSION / hygiene / root-layout
```

Full browser/service/adoption validation is intentionally left to the operator release-control run.

# Release v0.1.9 — Actual MVP clarification in living design

Target artifact: `chatgpt_claudecode_workflow-2_v0.1.9.zip`
Base artifact: `chatgpt_claudecode_workflow-2_v0.1.8.zip`

## Purpose

Clarify that `json_orchestration_state_mvp` is the actual current MVP and that the living design Markdown/draw.io files are the updateable visual/control-plane map around that MVP.

## Changes

- Updated `docs/design/promptbranch-mvp-living-design.md`.
- Updated `docs/design/promptbranch-mvp-living-design.drawio`.
- Added explicit references to:
  - `orchestration/docs/json_orchestration_state_mvp.md`
  - `orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md`
  - `orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md`
- Made the draw.io diagram show `ACTUAL MVP: json_orchestration_state_mvp` prominently.

## Validation

Focused validation for this release should include:

```bash
pb release docs-status --version v0.1.9 --json
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
pb test smoke --json
```

No full browser/source/adoption test is required unless this release is selected as an adoption checkpoint.

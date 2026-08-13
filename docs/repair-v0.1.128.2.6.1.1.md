# v0.1.128.2.6.1.1 — packaging/import-surface corrective

Baseline: `v0.1.128.2.5`.

Repairs:
- declare `promptbranch_skill_sync` in `[tool.setuptools].py-modules`;
- pass the exact release artifact to candidate tests with `--package-zip`;
- add regressions for both invariants.

Historical `.2.6` and `.2.6.1` artifacts remain immutable evidence. Live lifecycle is not claimed by construction.

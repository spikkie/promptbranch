# v0.1.128.2.6.1.1.1 — VERSION-derived structural-contract corrective

## Baseline and immutable predecessor

- accepted/current authority: `v0.1.128.2.5`, SHA-256 `07c6e41d29e932e99d8eda20eeee35de92acdd567df6e529b51aee252fb70d58`
- immutable failed predecessor: `v0.1.128.2.6.1.1`, SHA-256 `f23253e99d985906e7a24b61594efb6d3d39a011f2acda78e2c4bc7a49001553`
- predecessor live state: independently verified `RUNTIME_PREPARED`; `TESTED_GREEN` blocked retryably

## Root cause

The predecessor passed exact package metadata/import smoke (including `promptbranch_skill_sync`) but failed `validation.application_architecture_structural`: four portable-skill tests hard-coded `v0.1.128.2.6.1` while implementation correctly reported the release `VERSION`.

## Repair

- derive portable tool-authoring and learning/operator release expectations from root `VERSION`;
- derive current project-control release expectations from root `VERSION` instead of repeating the candidate literal;
- preserve all historical release-version fixtures and historical failed-attempt evidence;
- keep `v0.1.129` blocked until this repair reaches `FINAL_VERIFIED` and fresh current alignment.

## Required proof

The final exact ZIP, not only the construction worktree, must be clean-extracted and pass the application architecture structural group. Deterministic byte-identical rebuild and Artifact Guardian must then pass before live lifecycle execution.

## Construction evidence

Exact clean-extraction structural coverage is 62/62 nodeids green (29 application architecture, 14 migration, 8 tool-authoring, 7 learning, 4 skill-sync) using pytest 9.0.2 with ambient plugin autoload disabled. The artifact container could not retain the one-process aggregate long enough for a summary, so canonical host lifecycle must still rerun the normal single structural group.


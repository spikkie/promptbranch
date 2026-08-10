> **v0.1.127.1.1.1 repair candidate:** propagates the baseline artifact conversation pin into the full browser suite and makes `TESTED_GREEN` independently require the executed `ask_question` URL and conversation ID to match that baseline exactly; `.127.1.1` remains immutable false-proof evidence.

## v0.1.127 Portable Promptbranch tool-authoring skill and export bundle

`v0.1.127` is the next normal Promptbranch environment slice from accepted/current `v0.1.126.1.1.1.1.3` (`chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.3.zip`, SHA-256 `07ed977b948dd2b8779a93ff74512817e75ba9cbb3f2bdbdb87351b838dbf0e7`). It packages a tracked read-only `promptbranch-tool-authoring` skill, a deterministic `promptbranch.tool.authoring` schema, fail-closed semantic validation, and a reproducible portable ZIP export for ChatGPT Project Sources and coding-agent use.

Tool authoring is proposal-only. A valid authoring specification does not register, implement, execute, mutate, publish, release, or adopt a tool. The portable bundle manifest explicitly keeps execution, mutation, release, publication, and adoption authority false, and verification rejects missing, extra, modified, non-deterministic, or authority-escalating content.

New read-only/portable commands:

```text
pb skill authoring-validate --path <repo> --json
pb skill tool-spec-validate <spec.json> --json
pb skill export promptbranch-tool-authoring --path <repo> --output <bundle.zip> --json
pb skill verify-bundle <bundle.zip> --json
```

Accepted/current remains `v0.1.126.1.1.1.1.3` until the canonical `v0.1.127` lifecycle reaches `FINAL_VERIFIED`.

## v0.1.126.1.1.1.1.3 Release validation Python authority propagation repair

`v0.1.126.1.1.1.1.3` is a narrow repair candidate built from the exact `v0.1.126.1.1.1.1.2` candidate after live full validation passed 53/53 but publication stopped before Git commit. The canonical state machine selected the candidate pipx interpreter with pytest 9.0.2, then the repository release-contract sanitizer dropped `PROMPTBRANCH_RELEASE_VALIDATION_PYTHON`, allowing ambient `PATH` to resolve `/home/spikkie/git/ai-aip/py_env/bin/python3` with pytest 8.4.2.

This repair adds that explicit interpreter authority to the release-contract environment allowlist and proves with a poisoned-PATH regression that sanitized publication validation still receives the candidate interpreter. No browser, runtime-preparation, acceptance, adoption, ETA, or external-application scope changes are introduced. Accepted/current remains `v0.1.125.3.4.2`; `v0.1.126.1.1.1.1.3` is not current until the canonical lifecycle reaches `FINAL_VERIFIED`.

## v0.1.126.1.1.1.1.2 Accepted-runtime precondition and preservation repair

`v0.1.126.1.1.1.1.2` is a narrow repair candidate built from the exact immutable `v0.1.126.1.1.1.1.1` artifact (`264507a4921e1f885717ca0498581a352cf5e54a1b6c57363daba98522a0eb11`) while accepted/current remains `v0.1.125.3.4.2`. The predecessor reached `RUNTIME_PREPARED` with the accepted/current port-8000 service absent both before and after candidate preparation because the preservation check defaulted to true when production was already missing.

This repair makes a single healthy exact-baseline production runtime a hard precondition before candidate install/build/start. It re-snapshots production on every retry and, after isolated candidate preparation, requires the same authoritative container, immutable Docker image ID, baseline version, and artifact-SHA label to remain unchanged. Missing, unhealthy, mismatched, disappeared, or drifted production is `BLOCKED_RETRYABLE`. Candidate preparation does not auto-recover production.

## v0.1.126.1.1.1.1.1 Runtime fingerprint publication authority repair

`v0.1.126.1.1.1.1.1` is a repair candidate built from the exact immutable `v0.1.126.1.1.1.1` artifact (`a2b669b51de6a8d3c0ed95832acdf421b003b47533dfd87566fa6b76f27741cb`) while accepted/current remains `v0.1.125.3.4.2`. The predecessor passed the complete canonical 53-unit candidate suite, including the repaired text-source and ask paths, then failed before worktree mutation because publication read `source_fingerprint` from the projected `RUNTIME_PREPARED` evidence while runtime preparation persisted it only in the authoritative runtime checkpoint.

This repair makes the runtime checkpoint the source-fingerprint authority, explicitly projects that value into `RUNTIME_PREPARED`, and routes worktree materialization and Git committed-tree guards through one fail-closed runtime fingerprint accessor. Missing projection/checkpoint identity and checkpoint/evidence disagreement have distinct failure codes. Construction does not change accepted/current authority.

## v0.1.126.1.1.1 Project Source text-add readiness and bounded recovery repair

`v0.1.126.1.1.1` is a repair candidate built from the exact immutable `v0.1.126.1.1` artifact while accepted/current remains `v0.1.125.3.4.2`. The `v0.1.126.1.1` live run proved the canonical source-fingerprint and blocked-ETA repairs, reached `RUNTIME_PREPARED`, and then failed only in `browser.project_source_add_text`: ChatGPT advertised Text input support but the Add/Save control stayed disabled and the integration harness re-raised HTTP 504 before its existing zero-request reconciliation path could run.

This repair makes the text body editor authoritative instead of permitting a generic `input[type=text]` fallback that can target the title field, performs two bounded value/input/change/blur/keyboard stabilization attempts before declaring the save control unusable, carries structured save-readiness diagnostics through timeout/HTTP boundaries, and lets the release-blocking text step reconcile the authoritative source surface before exactly one retry when zero save requests were observed. Ambiguous or non-empty unrelated source surfaces remain fail-closed. A focused live `project_source_add_text` proof is required before another full release run.

## v0.1.126.1.1 canonical fingerprint and blocked-ETA semantics repair

`v0.1.126.1.1` is a repair candidate built from the exact immutable `v0.1.126.1` artifact while accepted/current remains `v0.1.125.3.4.2`. The first live `v0.1.126` run passed 53/53 candidate validation but exposed three release-controller defects: the exact tested candidate was not materialized into the Git working tree before commit/push, publication subprocess output still used a nested-JSON last-object parser, and Project Source upload could succeed while being classified as failed.

The live `v0.1.126.1` attempt then exposed a deterministic runtime-preparation defect: the state machine computed a full-source fingerprint while the Dockerfile independently recomputed only `VERSION`, `promptbranch_version.py`, and `pyproject.toml`. `v0.1.126.1.1` removes that divergent algorithm and makes `promptbranch_source_fingerprint.py` the single fingerprint authority across runtime, Docker, worktree, and committed-tree identity. It also suppresses wall-clock completion timestamps while a release is `BLOCKED_RETRYABLE`, reporting only estimated work after resume.

This repair makes the tested candidate source authoritative for Git publication, verifies full-source fingerprints across tested extraction, materialized working tree and committed tree, selects action-aware top-level JSON command results, reconciles ChatGPT-assigned indexed Project Source filenames, reuses durable green candidate-test evidence on retry, and records candidate-test/materialization/commit/push/source-upload as ETA subphases. No compatibility path preserves the superseded publication behavior.

The `v0.1.126` DoD remains open until this repair reaches `FINAL_VERIFIED` from accepted/current `v0.1.125.3.4.2`.

## v0.1.126 persistent whole-release ETA estimator

`v0.1.126` advances from accepted/current `v0.1.125.3.4.2` and adds a canonical persistent ETA model to the immutable release state machine. Release duration evidence is stored by test profile, lifecycle phase, execution transport, and transition step. The state machine exposes remaining duration, expected finish timestamps, confidence and evidence provenance, candidate-test timeout risk, and an optional outer-wrapper timeout assessment.

ETA is advisory only. It never weakens candidate-test, acceptance, adoption, runtime-convergence, or `FINAL_VERIFIED` authority. Missing or malformed ETA state degrades ETA reporting rather than changing the release verdict.

The new read-only command is:

```text
pb release eta --version v0.1.126 --repo-path <repo> --json
```

Accepted/current baseline: `v0.1.125.3.4.2` (`chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip`, SHA-256 `ed6752cc7e1cf654f0e3ea505110599d5be3e067dbb00f07b8ae90cf34a9510f`).

See `docs/release-v0.1.126.md`, `docs/project/plan-state.json`, and `docs/project/canonical-release-state-machine.md`.

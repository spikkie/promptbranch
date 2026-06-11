# Repair v0.1.73.1 — Canonical artifact adoption diagnostics and external-repo status semantics

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.73.zip
```

## Repair version

```text
v0.1.73.1
```

## Reason

Field testing of v0.1.73 against the `candlecast` multi-repo project proved the canonical artifact naming and `pb artifact adopt --local-only` path, but exposed reporting and diagnostic defects:

```text
1. --local-only adoption reported top-level source_verified=false while checks.source_verified=true.
2. External repo current-state payloads reported code_version_matches_state_source=false without a clear not-applicable relation.
3. local_artifact_not_found did not echo the attempted --local-path even when supplied.
4. .promptbranch-repo.json needed an explicit ZIP hygiene policy: allowed as portable repo identity, rejected if it carries local state, local paths, or secrets.
```

## Files changed

```text
promptbranch_artifacts.py
promptbranch_cli.py
promptbranch_version.py
pyproject.toml
VERSION

tests/test_promptbranch_artifacts.py
tests/test_promptbranch_cli.py

docs/repair-v0.1.73.1.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
```

## Changes

```text
- Added source_verification object for artifact adoption payloads.
- For --local-only adoption, source_verification.status is local_only and source_verification.ok is true without pretending Project Source verification happened.
- Added attempted_local_path and attempted_artifact_ref to local_artifact_not_found payloads.
- Added external repo code-version relation fields to artifact current payloads.
- Allowed portable .promptbranch-repo.json in release ZIPs.
- Rejected .promptbranch-repo.json when it contains local absolute paths, .pb_profile/.local/.config Promptbranch state paths, or sensitive token/session/cookie fields.
```

## Scope control

```text
No slice advanced.
No normal version advanced.
No Project Source upload behavior changed.
No release-set orchestration added.
No cross-repo dependency solver added.
No Docker/deployment behavior changed.
No historical registry rewritten.
```

## Validation

```text
Focused tests added/updated for:
- local-only artifact adoption source semantics
- missing local-path diagnostics
- external repo artifact-current relation fields
- portable .promptbranch-repo.json ZIP hygiene
- rejecting .promptbranch-repo.json with local state/secrets
```

## Acceptance rule

This repair ZIP remains a candidate until operator release-control and adoption evidence confirms it as current.

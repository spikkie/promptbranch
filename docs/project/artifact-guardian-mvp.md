# Promptbranch Artifact Guardian MVP

Status: planning document  
Project: `chatgpt_claudecode_workflow-2` / Promptbranch  
Document type: MVP / architecture / rollout plan  
Recommended repo path: `docs/project/artifact-guardian-mvp.md`  
Last updated: 2026-06-16

---

## 1. Executive summary

The **Promptbranch Artifact Guardian MVP** adds a deterministic release-artifact gate for ZIP release candidates.

Its purpose is simple:

```text
No structurally invalid ZIP should reach the operator or ChatGPT user as a release candidate.
```

The immediate failure class to prevent is:

```text
operator downloads ZIP
operator starts lifecycle
lifecycle immediately fails because the ZIP is missing a required root file, such as .gitignore
```

The Artifact Guardian validates ZIPs against a project-local policy file:

```text
.artifact-guardian.yml
```

The same policy source must be used by Promptbranch artifact commands, project lifecycle install guards, and assistant-side ZIP handoff workflows where Promptbranch is available.

---

## 2. Problem statement

Promptbranch-supported projects frequently create ZIP release artifacts before those artifacts have been validated against the project’s packaging requirements.

This creates wasted operator cycles because basic packaging defects are found too late, usually only after:

```text
1. the assistant creates a ZIP;
2. the operator downloads it;
3. the operator runs the project lifecycle;
4. lifecycle install-ZIP verification fails immediately.
```

The observed example is a release ZIP that was missing `.gitignore` at the repository root.

That failure should be caught before the ZIP is exposed as a release candidate.

---

## 3. MVP goal

```text
Prevent structurally invalid release ZIPs from being exposed as release candidates by validating them against a single project-local artifact policy before release handoff.
```

---

## 4. Primary operator

```text
Software project operator creating, downloading, installing, validating, and adopting Promptbranch-managed release ZIPs.
```

Secondary users:

- ChatGPT assistant workflows that create software release ZIPs;
- project lifecycle scripts that install release ZIPs;
- Promptbranch automation commands;
- future artifact-build agents.

---

## 5. Success signal

The MVP is successful when this behavior is guaranteed:

```text
A ZIP missing .gitignore, VERSION, required docs/project files, or using wrapper-folder layout fails before any release-ready ZIP link or release_ready=true result is provided.
```

Minimum proof:

```text
pb artifact guard --repo . --zip <candidate.zip> --version <version> --policy .artifact-guardian.yml --json
```

returns:

```json
{
  "ok": false,
  "status": "guard_failed",
  "release_ready": false
}
```

for invalid ZIPs.

---

## 6. Hard invariant

```text
No ZIP artifact may be presented as a release candidate unless Artifact Guardian validation passes.
```

This is a structural-release invariant, not a runtime-correctness claim.

Important distinction:

```text
Artifact Guardian passed = candidate ZIP structure is valid.
pb artifact current = runtime/artifact/source/registry/current state is aligned.
```

Therefore:

```text
pb artifact guard passed != accepted/current
```

A guarded ZIP remains only:

```text
candidate
```

until `pb artifact current --json` or equivalent adoption evidence confirms alignment.

---

## 7. Scope boundary

## 7.1 In scope for the MVP

```text
.artifact-guardian.yml schema
pb artifact guard
strict JSON output
required entry checks
forbidden entry checks
wrapper-folder check
nested ZIP check
VERSION check
artifact-name pattern check
executable-bit check
unit tests for guard behavior
regression test for missing .gitignore
project documentation and rollout plan
```

## 7.2 Out of scope for the first MVP slice

```text
pb artifact heal
pb artifact agent
automatic repair-version creation
full lifecycle execution
source adoption
marking artifacts accepted/current
deployment validation
external SEO checks
translation import/export
database mutation
runtime correctness validation
```

These can be planned as later slices after deterministic guard behavior is stable.

---

## 8. Non-goals

The Artifact Guardian must not automatically:

```text
change application logic
change tests to make them pass
change release history
mark artifacts accepted/current
modify Promptbranch project sources
remove old Promptbranch sources
run deployment
run external SEO tests
run full project lifecycle
perform translation import/publish
mutate databases
```

The guardian is for artifact correctness, not runtime correctness.

---

## 9. Architecture

## 9.1 Core components

```text
.artifact-guardian.yml
  Project-local policy source.

pb artifact guard
  Deterministic validator for existing ZIP artifacts.

pb artifact build
  Future builder that must delegate validation to the same guard engine.

pb artifact heal
  Future safe mechanical repair command.

pb artifact agent
  Future orchestration loop: build -> guard -> heal -> guard.

project lifecycle install guard
  Future lifecycle integration that calls pb artifact guard instead of maintaining its own divergent ZIP requirements.

assistant-side handoff
  Future ChatGPT-side rule that blocks release ZIP links when guard failed or was skipped.
```

## 9.2 Single-source policy rule

All artifact-validation participants must use the same policy file:

```text
.artifact-guardian.yml
```

Participants:

```text
pb artifact guard
pb artifact build
pb artifact heal
pb artifact agent
project release lifecycle install ZIP verification
assistant-side ZIP handoff where Promptbranch is available
```

No component may keep a separate hardcoded required-file list unless that list is generated from `.artifact-guardian.yml`.

---

## 10. Policy file

Default file name:

```text
.artifact-guardian.yml
```

Recommended baseline for `chatgpt_claudecode_workflow-2`:

```yaml
schema_version: 1

project:
  id: chatgpt_claudecode_workflow-2
  artifact_pattern: "chatgpt_claudecode_workflow-2_{version}.zip"
  version_file: "VERSION"

zip:
  forbid_wrapper_folder: true
  forbid_nested_zip: true
  preserve_executable_bits: true

required_entries:
  - ".gitignore"
  - "VERSION"
  - "README.md"
  - "docs/project/README.md"
  - "docs/project/mvp.md"
  - "docs/project/definition-of-done.md"
  - "docs/project/plan.md"
  - "docs/project/status.md"
  - "docs/project/release-status.md"
  - "docs/project/decisions.md"
  - "docs/project/migration.md"

forbidden_entries:
  - ".git/"
  - ".pb_profile/"
  - "__pycache__/"
  - "*.pyc"
  - "*.pyo"
  - ".pytest_cache/"
  - ".mypy_cache/"
  - ".ruff_cache/"
  - ".venv/"
  - "node_modules/"
  - "dist/"
  - "build/"
  - "*.zip"
  - "*.log"
  - ".env"

executable_entries: []

version_checks:
  require_version_file_equals_cli_version: true
  require_artifact_name_contains_version: true
```

Project-specific repositories may extend `required_entries` and `executable_entries`.

Examples:

```text
spikkies-site:
  manage.py
  scripts/run-release-lifecycle.sh

my_awx:
  scripts/run-release-lifecycle.sh
  k8s manifests / helm descriptors as required by policy

ib_forex_trading:
  ib_release_zip_control_workflow.sh
  architecture_project.yaml
  architecture/line_policy/line_policy.yaml
```

---

## 11. Promptbranch CLI design

## 11.1 MVP command: `pb artifact guard`

Purpose:

```text
Validate an existing ZIP against .artifact-guardian.yml.
```

Example:

```bash
pb artifact guard \
  --repo . \
  --zip ./chatgpt_claudecode_workflow-2_v0.1.78.zip \
  --version v0.1.78 \
  --policy .artifact-guardian.yml \
  --json
```

Responsibilities:

```text
load policy
inspect ZIP
check required files
check forbidden files
check wrapper folder
check nested ZIPs
check version file
check artifact name pattern
check executable bits
return strict JSON
exit nonzero on failure
```

## 11.2 Future command: `pb artifact build`

Purpose:

```text
Build a ZIP and run pb artifact guard before returning release_ready=true.
```

MVP note:

```text
Do not implement build integration in the first slice unless the guard engine is already stable.
```

## 11.3 Future command: `pb artifact heal`

Purpose:

```text
Repair only safe mechanical packaging defects.
```

Allowed healing:

```text
restore missing tracked required files
remove forbidden generated/cache/local files
remove nested ZIPs accidentally included
remove wrapper-folder layout
restore executable bits
rebuild ZIP with correct root layout
```

Disallowed healing:

```text
test failures
application behavior
runtime errors
deployment errors
release history conflicts
version strategy conflicts
Promptbranch source-list state
accepted/current baseline state
translation state
database state
```

## 11.4 Future command: `pb artifact agent`

Purpose:

```text
Run build -> guard -> heal -> guard until pass or hard failure.
```

Maximum healing attempts:

```text
2
```

---

## 12. Validation rules

## 12.1 Required entries

If any `required_entries` path is missing from the ZIP, guard fails.

Example failure:

```json
{
  "ok": false,
  "failure_class": "required_entry_missing",
  "missing_required_entries": [".gitignore"],
  "release_ready": false
}
```

## 12.2 Forbidden entries

If any forbidden file or directory exists in the ZIP, guard fails.

Example failure:

```json
{
  "ok": false,
  "failure_class": "forbidden_entry_present",
  "forbidden_entries": [".pytest_cache/"],
  "release_ready": false
}
```

## 12.3 Wrapper folder

If the ZIP opens into a parent folder instead of repository contents at root level, guard fails.

Example failure:

```json
{
  "ok": false,
  "failure_class": "wrapper_folder_present",
  "release_ready": false
}
```

## 12.4 Version file

If `VERSION` does not equal the requested version, guard fails.

Example failure:

```json
{
  "ok": false,
  "failure_class": "version_mismatch",
  "expected_version": "v0.1.78",
  "actual_version": "v0.1.77.11",
  "release_ready": false
}
```

## 12.5 Artifact name

If the artifact filename does not match `artifact_pattern`, guard fails.

Example failure:

```json
{
  "ok": false,
  "failure_class": "artifact_name_mismatch",
  "expected_pattern": "chatgpt_claudecode_workflow-2_{version}.zip",
  "release_ready": false
}
```

## 12.6 Executable bits

If required executable script entries are not executable inside the ZIP, guard fails.

Example failure:

```json
{
  "ok": false,
  "failure_class": "executable_bit_missing",
  "entries": ["scripts/run-release-lifecycle.sh"],
  "release_ready": false
}
```

---

## 13. JSON output contract

## 13.1 Successful guard output

```json
{
  "ok": true,
  "action": "artifact_guard",
  "repo": ".",
  "policy": ".artifact-guardian.yml",
  "artifact": "chatgpt_claudecode_workflow-2_v0.1.78.zip",
  "version": "v0.1.78",
  "status": "guard_passed",
  "checks": {
    "required_entries": "passed",
    "forbidden_entries": "passed",
    "wrapper_folder": "passed",
    "version_file": "passed",
    "artifact_name": "passed",
    "executable_bits": "passed"
  },
  "healed": false,
  "release_ready": true
}
```

## 13.2 Failed guard output

Preferred structure:

```json
{
  "ok": false,
  "action": "artifact_guard",
  "repo": ".",
  "policy": ".artifact-guardian.yml",
  "artifact": "chatgpt_claudecode_workflow-2_v0.1.78.zip",
  "version": "v0.1.78",
  "status": "guard_failed",
  "release_ready": false,
  "failures": [
    {
      "failure_class": "required_entry_missing",
      "path": ".gitignore",
      "healable": true
    }
  ]
}
```

Design note:

```text
Use failures[] instead of only one failure_class because one ZIP can fail multiple checks at the same time.
```

---

## 14. Implementation slices

## Slice AG-001 — Deterministic guard

Goal:

```text
Implement .artifact-guardian.yml parsing and pb artifact guard validation for existing ZIP files.
```

In scope:

```text
policy loader
ZIP inspector
guard validator
strict JSON output
required/forbidden/wrapper/nested/version/name/executable checks
unit tests
missing .gitignore regression test
```

Out of scope:

```text
pb artifact build integration
pb artifact heal
pb artifact agent
lifecycle integration
assistant-side handoff integration
accepted/current adoption changes
```

Expected files:

```text
src/promptbranch/artifacts/guardian.py
src/promptbranch/artifacts/policy.py
src/promptbranch/artifacts/zip_inspection.py
src/promptbranch/cli.py
tests/test_artifact_guardian.py
docs/project/artifact-guardian-mvp.md
```

Expected validation:

```bash
python3 -m pytest -q tests/test_artifact_guardian.py
python3 -m compileall -q src tests
```

## Slice AG-002 — Build integration

Goal:

```text
Make pb artifact build use the same policy and validator as pb artifact guard.
```

Rule:

```text
pb artifact build may only return release_ready=true when guard passes.
```

## Slice AG-003 — Safe healing

Goal:

```text
Implement pb artifact heal for mechanical packaging repairs only.
```

## Slice AG-004 — Agent orchestration

Goal:

```text
Implement pb artifact agent with build -> guard -> heal -> guard loop.
```

## Slice AG-005 — Lifecycle integration

Goal:

```text
Update project lifecycle templates to call pb artifact guard and remove divergent hardcoded ZIP requirement lists.
```

## Slice AG-006 — ChatGPT Project rollout

Goal:

```text
Document and enforce assistant-side ZIP handoff rules for ChatGPT software projects.
```

---

## 15. Required tests

## 15.1 Unit tests

```text
missing .gitignore fails guard
missing VERSION fails guard
VERSION mismatch fails guard
wrapper folder fails guard
nested ZIP fails guard
forbidden cache file fails guard
artifact name mismatch fails guard
executable bit missing fails guard
valid ZIP passes guard
JSON output is stable
```

## 15.2 Integration tests

Later slices should add:

```text
pb artifact build creates ZIP and runs guard
pb artifact heal restores missing tracked required file
pb artifact agent refuses to release unhealable ZIP
lifecycle install guard uses pb artifact guard
policy file drives both build and guard
```

## 15.3 Regression test for observed issue

Given:

```text
A ZIP without .gitignore
```

Expected:

```text
pb artifact guard fails before lifecycle starts
pb artifact agent heals or blocks
no release-ready artifact is returned until .gitignore is present
```

---

## 16. Definition of Done

The Artifact Guardian feature is done when:

```text
[ ] .artifact-guardian.yml schema is documented.
[ ] pb artifact guard validates ZIPs from the policy file.
[ ] pb artifact build uses the same policy and validator.
[ ] pb artifact heal repairs only safe packaging defects.
[ ] pb artifact agent orchestrates build -> guard -> heal -> guard.
[ ] Guard JSON output is stable and documented.
[ ] Missing .gitignore fails before the ZIP can be released.
[ ] Lifecycle install guard can delegate to pb artifact guard.
[ ] Tests prove build/guard/agent use the same policy source.
[ ] Tests prove no separate hardcoded required-file list is used.
[ ] A failed guard prevents release_ready=true.
[ ] A passed guard still marks the artifact only as candidate, not accepted/current.
```

AG-001 is done when:

```text
[ ] .artifact-guardian.yml can be loaded.
[ ] required_entries are checked.
[ ] forbidden_entries are checked.
[ ] wrapper-folder layout is checked.
[ ] nested ZIPs are checked.
[ ] VERSION equality is checked.
[ ] artifact name pattern is checked.
[ ] executable bits are checked where configured.
[ ] strict JSON is emitted.
[ ] invalid ZIP exits nonzero.
[ ] valid ZIP exits zero.
[ ] missing .gitignore regression test passes.
```

---

## 17. ChatGPT project integration

Every ChatGPT software project that produces release ZIPs should adopt this rule:

```text
Never expose a release ZIP link when Artifact Guardian validation failed or was skipped.
```

Where Promptbranch is available:

```bash
pb artifact agent \
  --repo . \
  --version "$version" \
  --policy .artifact-guardian.yml \
  --json
```

Where Promptbranch is not available:

```text
Run a compatible local implementation of the same .artifact-guardian.yml policy and explicitly report that Promptbranch itself was unavailable.
```

This creates a consistent handoff rule across:

```text
Promptbranch CLI
local lifecycle scripts
ChatGPT assistant-side ZIP creation
project release workflows
```

---

## 18. Project-control-surface integration

This MVP should be tracked through the standard project control surface:

```text
docs/project/mvp.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
```

Recommended updates:

```text
docs/project/plan.md
  Add AG-001..AG-006 rollout slices.

docs/project/status.md
  Mark current active slice as AG-001 when implementation starts.

docs/project/release-status.md
  Track each release as planned/candidate/accepted_current only with evidence.

docs/project/decisions.md
  Add ADR: Artifact Guardian policy source is .artifact-guardian.yml.
```

---

## 19. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Overbuilding first slice | Large unstable release | Implement AG-001 only first. |
| Duplicated policy lists | Drift between build, guard, lifecycle | Generate or load all checks from `.artifact-guardian.yml`. |
| Healing changes behavior | Unsafe mutation | Restrict healing to mechanical packaging defects. |
| Guard confused with adoption | False accepted/current claim | Keep `guard_passed` separate from `pb artifact current`. |
| Project-specific rules leak into global defaults | Wrong validation for other repos | Keep project-specific entries in repo-local policy. |
| JSON output changes unexpectedly | Broken automation | Add JSON contract tests. |

---

## 20. Next implementation step

```text
Define the next Promptbranch release slice as AG-001 — Deterministic Artifact Guardian Guard.
```

Minimum implementation request:

```text
Build AG-001 from the latest accepted/current chatgpt_claudecode_workflow-2 baseline.
Add .artifact-guardian.yml policy loading and pb artifact guard.
Validate required entries, forbidden entries, wrapper-folder layout, nested ZIPs, VERSION equality, artifact naming, and executable bits.
Add regression test proving a ZIP missing .gitignore fails before lifecycle.
Do not implement build integration, healing, agent orchestration, lifecycle integration, or assistant-side handoff in this slice.
Do not mark the resulting ZIP accepted/current without pb artifact current --json adoption evidence.
```

---

## 21. Confidence level

Confidence: high for the MVP direction.

Reason:

```text
The requirement is narrow, testable, and directly addresses a repeated release-artifact failure class.
```

Confidence: medium for the exact code placement.

Reason:

```text
The current Promptbranch artifact command implementation must be inspected before final module paths are locked.
```

---

## 22. Verdict

✅ Strengths

```text
Single policy source
Clear release gate
Deterministic JSON evidence
Direct prevention of missing-root-file ZIP failures
Good separation between candidate validation and accepted/current adoption
KISS rollout path: guard first, healing later
```

⚠️ Weaknesses

```text
The full requirement is too broad for one release slice
Healing requires strict boundaries
Project-specific policies must not become global hardcoded defaults
Assistant-side validation depends on whether Promptbranch is available
```

🔍 Unknowns

```text
Exact accepted/current baseline at implementation time
Current internal location of artifact build/release code
Whether all project lifecycle scripts can delegate immediately to pb artifact guard
How assistant-side local fallback should be packaged when pb is unavailable
```

🧩 Next step

```text
Open AG-001 as the next normal Promptbranch slice and implement deterministic guard only.
```

# v0.1.127 — Portable Promptbranch tool-authoring skill and export bundle

## Baseline

- accepted/current: `chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.3.zip` (`v0.1.126.1.1.1.1.3`)
- accepted SHA-256: `07ed977b948dd2b8779a93ff74512817e75ba9cbb3f2bdbdb87351b838dbf0e7`
- release type: normal
- active system: Promptbranch environment/control plane

## Scope

This slice packages one portable `promptbranch-tool-authoring` skill and makes its authoring contract machine-checkable. The canonical specification requires deterministic identity/input/risk/validation/evidence/failure fields and keeps registration proposal-only while execution, mutation, release, publication, and adoption remain `not_granted`.

The export surface produces a deterministic ZIP for two consumers: `PROJECT_SOURCE.md` is self-contained for ChatGPT Project Sources, while `SKILL.md`, `AGENTS.md`, the JSON schema, example, and manifest support coding agents. Bundle entries, timestamps, modes, compression, payload SHA-256 values, and authority flags are independently verified.

## Commands

```text
pb skill authoring-validate --path . --json
pb skill tool-spec-validate .promptbranch/skills/promptbranch-tool-authoring/examples/read-version.tool.json --json
pb skill export promptbranch-tool-authoring --path . --output /tmp/promptbranch-tool-authoring_v0.1.127.zip --json
pb skill verify-bundle /tmp/promptbranch-tool-authoring_v0.1.127.zip --json
```

## Authority boundary

A valid authoring spec is not a registered or executable tool. This release grants no unrestricted command/shell execution, repository mutation, ChatGPT Project Source mutation, release publication authority, or artifact adoption authority.

## Acceptance boundary

Construction/focused validation does not make this candidate accepted/current. Acceptance requires the canonical release state machine from `v0.1.126.1.1.1.1.3` through `FINAL_VERIFIED`, followed by independent all-state verification and scoped `pb artifact current --repo chatgpt_claudecode_workflow-2 --json` alignment.

## Next planned normal slice

`v0.1.128 — PB environment MVP hardening and freeze`.


## Live validation disposition
Construction green; live r0001/r0002 both stopped at `browser.ask_question` with `service_internal_deadline_timeout` before TESTED_GREEN and no rate-limit evidence. `.127.1` first repairs routing/provenance.

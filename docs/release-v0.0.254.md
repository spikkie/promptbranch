# Release v0.0.254 — guarded native lifecycle execution

## Scope

This release advances the native release lifecycle MVP from plan-only orchestration to guarded execution through policy sync.

Implemented:

- `pb release lifecycle --artifact ZIP --version VERSION --target-version NEXT --json`
- executes lifecycle phases in order:
  1. `release doctor`
  2. bounded `release install --upload-source`
  3. `release test`
  4. `release adopt`
  5. `release policy-sync`
  6. final Git safety plan
- captures each phase as structured JSON inside one outer lifecycle result
- stops on the first failed guarded phase
- emits a final lifecycle summary

## Safety boundary

Git commit and Git push are still intentionally blocked. The command only reports Git safety eligibility. It does not stage, commit, or push files.

The lifecycle remains transactional:

- install must verify VERSION
- source upload must verify before/after Project Source state
- test must write a green structured acceptance report
- adopt requires the green report and exactly one matching Project Source
- policy sync verifies readback

## Validation performed

- `py_compile` passed
- focused CLI/parser/container/MCP/source tests passed
- lifecycle execution tests added for successful guarded flow and stop-on-failure behavior
- ZIP hygiene verified

## Not claimed

- automatic Git commit/push
- real downloaded artifact candidate path through `pb artifact intake`
- broad shell execution

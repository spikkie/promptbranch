# Repair release v0.0.226.1

## Base release

`chatgpt_claudecode_workflow_v0.0.226.zip`

## Repair version

`chatgpt_claudecode_workflow_v0.0.226.1.zip`

## Reason

`v0.0.226` introduced the tested-candidate adoption gate, but the post-release validation helper still had confusing `--adopt-if-accepted` semantics:

- baseline-dependent `protocol_smoke` could run before adoption, so `--from-current-baseline` could still resolve to the previously accepted baseline;
- the summary reported adoption steps as enabled when `--adopt-if-accepted` was passed, even when adoption was skipped because an earlier gate failed;
- skipped adoption could therefore look too similar to successful adoption in the summary.

## Files changed

- `scripts/post-release-validation.sh`
- `tests/test_post_release_validation.py`
- `docs/repair-v0.0.226.1.md`
- version metadata surfaces for `v0.0.226.1`
- README / UPGRADING release notes

## Validation performed

- `bash -n scripts/post-release-validation.sh`
- `python3 -m py_compile` on changed Python/version surfaces
- focused post-release-validation repair tests individually:
  - unadopted baseline remains diagnostic by default
  - `--require-adopted-baseline` still fails on mismatch
  - `--adopt-if-accepted` adopts after successful non-baseline gates
  - `--adopt-if-accepted` runs protocol smoke after adoption
- focused version/container/MCP/parser tests
- ZIP CRC and hygiene verification on the generated release ZIP

## Scope confirmation

No MVP slice or line was advanced.

This repair does not change:

- artifact intake behavior
- candidate download / verify / migrate behavior
- candidate-test behavior
- `accept-candidate` adoption-gate semantics
- Project Source upload behavior
- source sync behavior
- ask/reply protocol schema
- MCP policy behavior

# Repair v0.0.276.6

## Base release

`chatgpt_claudecode_workflow_v0.0.276.5.zip`

## Repair version

`v0.0.276.6`

## Reason

A strict final Artifact Intake MVP run with `--require-real-candidate-mvp` still placed the artifact-producing `pb ask-release` and `pb artifact intake --download --verify` proof behind the full product test/adoption path. When `pb test full` failed first, strict mode never reached the download/verify proof path, so the finalizer could not test the ZIP-download surface it was meant to prove.

## Files changed

- `scripts/post-release-validation.sh`
- `promptbranch_cli.py`
- `docs/howto/15-finalize-artifact-intake-mvp.md`
- `docs/howto/16-manual-pb-command-use-cases.md`
- `docs/mvp-definition-of-done.md`
- `tests/test_post_release_validation.py`
- `tests/test_cli_parser.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch.egg-info/PKG-INFO`
- `promptbranch.egg-info/SOURCES.txt`
- version-current tests

## Runtime behavior changed

When `scripts/finalize-artifact-intake-mvp.sh --require-real-candidate-mvp` delegates to `scripts/post-release-validation.sh`, strict real-candidate mode now runs the artifact-producing `pb ask-release` and `pb artifact intake --from-last-answer --download --verify` before full tests and before adopting the release under validation.

The strict `ask-release` call now passes an explicit request baseline:

```bash
--baseline-artifact chatgpt_claudecode_workflow_<version>.zip
--baseline-version <version>
```

This prevents pre-adoption proof from accidentally using an older `pb artifact current` baseline when the release under validation has not yet been adopted.

After successful tests/adoption, the script reuses the pre-adoption download/verify evidence and runs candidate-run after adoption only.

## Validation performed

- `bash -n scripts/finalize-artifact-intake-mvp.sh scripts/post-release-validation.sh chatgpt_claudecode_workflow_release_control.sh`
- `python3 -m py_compile promptbranch_cli.py tests/test_post_release_validation.py tests/test_cli_parser.py`
- Parser smoke for `ask-release --baseline-artifact --baseline-version`
- Manual subprocess reproduction proving `ask-release` and `artifact intake --download --verify` occur before `pb test full` when `pb test full` fails
- Parser-focused test for `ask-release --baseline-artifact --baseline-version`
- Focused pytest for the new strict ordering test emitted `1 passed`, but the pytest process did not terminate cleanly before the container timeout; this is not claimed as a clean pytest completion
- ZIP hygiene/layout verification

## Scope confirmation

No slice or line was advanced. This repair does not change artifact download implementation, candidate migration mechanics, candidate adoption mechanics, Project Source mutation behavior, MCP behavior, skill behavior, browser automation behavior, or release planning scope. It only changes the strict finalizer validation ordering and adds an explicit ask-release baseline override so download/verify proof is attempted before unrelated full-test/adoption failures can block it.

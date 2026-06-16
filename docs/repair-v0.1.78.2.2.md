# Repair v0.1.78.2.2 — Release-control multi-segment repair-version compatibility

## Reason

`v0.1.78.2.1` failed immediately in candidate release-control because `chatgpt_claudecode_workflow_release_control.sh` only accepted three- or four-segment versions. The emergency repair line now requires nested repair versions such as `v0.1.78.2.1`.

## Scope

In scope:

- Accept v-prefixed or bare dotted numeric versions with at least three numeric segments in release-control.
- Accept artifact ZIP names ending in such versions.
- Keep artifact prefix extraction compatible with multi-segment versions.
- Align `scripts/post-release-validation.sh` version normalization.
- Align artifact-candidate protocol schema version grammar.
- Add focused release-control regression coverage for `v0.1.78.2.1`.

Out of scope:

- Secure project delete protocol.
- Any actual ChatGPT Project deletion.
- Project Source removal behavior changes.
- AG-001 behavior changes.
- Adoption/current mutation.
- k8s-game foundation work.

## Safety decision preserved

ChatGPT Project deletion remains frozen. Public project deletion must not be re-enabled until a separately designed secure delete protocol exists.

## Validation target

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  tests/test_promptbranch_shell_scripts.py::test_release_control_accepts_multi_segment_repair_versions \
  tests/test_project_control_surface.py \
  tests/test_promptbranch_version.py \
  tests/test_promptbranch_ask_protocol.py::test_protocol_schema_and_examples_are_valid_json

python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh scripts/post-release-validation.sh run_chatgpt_service.sh run_chatgpt_service_dev.sh
```

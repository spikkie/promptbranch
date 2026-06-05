# Release v0.1.41.1 repair note

## Base release

`chatgpt_claudecode_workflow-2_v0.1.41.zip`

## Repair version

`chatgpt_claudecode_workflow-2_v0.1.41.1.zip`

## Reason

The `v0.1.41` install ZIP verification gate failed before install because the candidate ZIP contained protected runtime/test artifacts under `.pb_profile/`:

```text
.pb_profile/test_artifact_roundtrip/deterministic/artifact_inbox/pb_artifact_roundtrip_deterministic.zip
.pb_profile/test_artifact_roundtrip/deterministic/pb_artifact_roundtrip_deterministic.zip
.pb_profile/test_artifact_roundtrip/deterministic/wrapper_folder.zip
.pb_profile/test_artifact_roundtrip/deterministic/wrong_content.zip
```

The release-control install gate correctly rejected the artifact with `protected_zip_entries_present`.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
docs/release-v0.1.41.1.md
```

Packaging repair:

```text
removed .pb_profile/ runtime/test artifacts from the ZIP payload
```

## Validation performed

```text
python3 -m compileall -q .
python3 -m pytest -q tests/test_promptbranch_parallel.py tests/test_cli_parser.py::test_parser_accepts_debug_parallel_plan_command tests/test_promptbranch_cli.py::test_debug_parallel_plan_emits_command_metadata_json tests/test_promptbranch_cli.py::test_browser_client_log_writes_to_stderr
python3 promptbranch_cli.py debug parallel-plan --json
python3 promptbranch_cli.py debug parallel-plan --operation src_add --json
python3 promptbranch_cli.py test artifact-roundtrip --json --path .
ZIP hygiene verification: no .pb_profile/, no caches, no nested ZIPs, no wrapper folder
```

## Slice / line advancement

No slice was advanced. This repair only fixes the rejected `v0.1.41` packaging defect and preserves the `v0.1.41` parallel-execution architecture slice scope.

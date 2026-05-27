# Release v0.0.278

Base artifact: `chatgpt_claudecode_workflow_v0.0.277.zip`
Release type: normal incremental release

## Change summary

- Added documentation for the local Promptbranch release lifecycle with manual ChatGPT Project Source upload.
- Added a repo-relative lifecycle diagram bundle under `docs/diagrams/promptbranch-lifecycle/`:
  - `promptbranch_lifecycle_commands.drawio`
  - `promptbranch_lifecycle_commands.png`
  - `promptbranch_lifecycle_commands.svg`
  - `README.md`
- Added `docs/howto/17-local-release-lifecycle-with-manual-upload.md` covering:
  - baseline verification;
  - local documentation changes;
  - version bumping;
  - candidate ZIP creation;
  - ZIP hygiene verification;
  - manual Project Source upload;
  - release-control testing;
  - guarded adoption;
  - final Promptbranch state verification.
- Updated version metadata for `v0.0.278`.

## Risk controls

- The release is documentation-focused and does not change Project Source mutation code.
- The runbook states that manual UI upload is not proof of persistence and must be followed by `pb src list --json` verification.
- The runbook keeps `.promptbranch-project.json` / accepted baseline state unchanged until adoption succeeds.
- Diagram files are kept under a repo-relative documentation directory, not as root-level scratch artifacts.

## Validation

- `python3 -m compileall promptbranch promptbranch_automation promptbranch_browser_auth`
- `python3 -m pytest tests/test_cli_parser.py tests/test_promptbranch_container_api.py tests/test_compose_timeout_policy.py -q`
- ZIP verification:
  - opens successfully;
  - `VERSION` is `v0.0.278`;
  - no wrapper folder;
  - no nested ZIPs;
  - no cache files;
  - no `.pb_profile/`;
  - no `.pyc`, `.pyo`, or `.log` files.

## Operator note

After manual upload of `chatgpt_claudecode_workflow_v0.0.278.zip` to ChatGPT Project Sources, verify visibility before adoption:

```bash
pb src list --json | tee pb_src_list.after_manual_upload.v0.0.278.json
```

Then run the normal release-control test/adopt gate.

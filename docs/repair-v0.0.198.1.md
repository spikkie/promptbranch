# Repair release v0.0.198.1

Base release: v0.0.198

Repair version: v0.0.198.1

Reason:

- Repair `chatgpt_claudecode_workflow_release_control.sh` after a reported Bash parse failure near a Python function line in the Project Source verification path.
- Make the affected inline Python checks more robust by using `python3 -c` instead of here-doc blocks for the source-list verification and local service health probe.

Files changed:

- `chatgpt_claudecode_workflow_release_control.sh`
- `docs/repair-v0.0.198.1.md`
- version metadata and version expectation tests updated from `v0.0.198` / `0.0.198` to `v0.0.198.1` / `0.0.198.1`

Validation performed:

- `bash -n chatgpt_claudecode_workflow_release_control.sh`
- targeted release-control shell tests
- version surface tests
- `python3 -m py_compile` on Python sources
- ZIP CRC/testzip check
- artifact verify hygiene check

Scope confirmation:

- No slice or line was advanced.
- No release workflow semantics were expanded.
- No Project Source mutation behavior was changed.
- This repair only fixes the intended `v0.0.198` release-control defect.

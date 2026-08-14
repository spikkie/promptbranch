# v0.1.128.2.6.1.1.2.1 — VERSION-file sole authority corrective

Accepted/current baseline: `v0.1.128.2.6.1.1.1` (`chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.1.zip`).

Active candidate: `v0.1.128.2.6.1.1.2.1` (`chatgpt_claudecode_workflow-2_v0.1.128.2.6.1.1.2.1.zip`).

## Purpose

Supersede the already-distributed `v0.1.128.2.6.1.1.2` candidate without mutating its bytes. Preserve its legacy release-control removal, while closing the version-authority and test-isolation defects exposed by host validation.

## Corrective scope

- `VERSION` is the sole mutable release-version authority.
- `pyproject.toml` declares project version dynamically from `promptbranch_version.PACKAGE_VERSION`; it contains no release-number literal.
- `promptbranch_version.py` reads the sibling `VERSION` authority in source/build contexts and uses installed distribution metadata only when the source authority is absent after installation.
- `.promptbranch-release.json` uses `{version}` / `{artifact}` templates resolved from `VERSION` by the Python release engine.
- current-version tests derive from `VERSION`; they do not pin the candidate or accepted baseline release number.
- simulated post-adoption control validation uses an isolated temporary authoritative registry and therefore cannot consult the operator's live accepted/current state.
- historical version fixtures and roadmap/history documents remain historical evidence; they are not mutable current-version authorities.

## Construction validation

- Version/authority/control/release-contract/legacy-removal focused gate: 69/69 passed.
- All 17 required deterministic release-validation groups: green by their exact constituent commands.
- Structural application group: 62/62 passed.
- Release state machine group: 124 passed, 1 canonical-runtime-only integration skip.
- Release pipeline group: 70/70 passed.
- Dynamic wheel build: metadata version is derived from `VERSION`.
- Installed-wheel proof without sibling `VERSION`: `promptbranch_version.PACKAGE_VERSION` resolves the distribution metadata that was built from `VERSION`.
- Current-version literal scan: zero current-version literals in executable/packaging sources or the release contract.

Final exact-ZIP deterministic rebuild, Artifact Guardian, package metadata, clean-extraction authority/control/structural tests, and the full live canonical lifecycle remain required before acceptance/current.

`v0.1.129` remains blocked until this repair is accepted/current.

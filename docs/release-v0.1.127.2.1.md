# v0.1.127.2.1 — Consolidated v0.1.127 closure construction-proof repair

Baseline: `v0.1.126.1.1.1.1.3` remains accepted/current. Immediate immutable predecessor: `v0.1.127.2`.

## Why this repair exists

The distributed `v0.1.127.2` ZIP was deterministic and its embedded version surfaces were correct, but an operator-run canonical validation exposed one required-group failure: `release_pipeline` had 14 failures. The product release engine correctly preserved the exact launcher Python path; the test `FakeRunner` still matched `Path(sys.executable).resolve()`, which encoded the superseded behavior that converts a venv launcher into its system-Python symlink target. Every affected pipeline test therefore stopped at `local-build_failed`.

The apparent post-install `promptbranch_version.PACKAGE_VERSION == 0.1.127.1.1.1` was a separate verification-command error: the probe was run while the shell remained in the older repository worktree, so the current directory masked the installed module. The ZIP itself contains `VERSION`, package metadata, and `promptbranch_version.py` for `0.1.127.2`. Installed-package verification must use isolated mode (`python -I`) or a neutral working directory.

## Repair

- Remove the stale `Path(sys.executable).resolve()` expectation from release-pipeline fakes.
- Preserve the exact launcher-path Python authority implemented by v0.1.127.2.
- Remove the temporary faulthandler watchdog from the release-pipeline test module.
- Preserve tool-authoring, artifact/conversation provenance, exact ask-route proof, acceptance-path provenance, release-state-machine, and single-Python behavior.
- Advance only release/control metadata and tests; no new normal product scope is introduced.

## DoD

DOD-510 through DOD-514 must be construction-green on the exact final `v0.1.127.2.1` ZIP. DOD-515 remains the live closure gate: exact baseline-routed TESTED_GREEN, independent verification, ACCEPTED, ADOPTED_CURRENT, FINAL_VERIFIED, final independent all-state verification, and fresh scoped current alignment.

## Construction result

The repaired source tree and the exact extracted candidate pass all 17 canonical required groups. The exact final ZIP is rebuilt deterministically, CRC/path/hygiene clean, contains no nested ZIP, and Artifact Guardian reports `release_ready=true`. DOD-510 through DOD-514 are construction-proven; DOD-515 remains live-pending.

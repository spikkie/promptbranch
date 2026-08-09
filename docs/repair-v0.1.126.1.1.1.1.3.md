# Repair evidence — v0.1.126.1.1.1.1.3

## Input evidence

`v0.1.126.1.1.1.1.2` passed full live candidate validation 53/53. Publication then failed at the local release-validation preflight because the sanitized release-contract environment selected `/home/spikkie/git/ai-aip/py_env/bin/python3` with pytest 8.4.2 instead of the candidate pipx Python with pytest 9.0.2.

A direct non-mutating proof with `PROMPTBRANCH_RELEASE_VALIDATION_PYTHON` explicitly supplied selected the candidate interpreter and allowed the required deterministic release groups to execute successfully.

## Repair invariant

The canonical candidate interpreter selected by the state machine is release-validation authority. Ambient `PATH` may remain available for ordinary executable resolution but may not silently replace that authority.

## Scope

No browser, Docker runtime-preparation, ETA, acceptance/adoption semantics, or external-application authority changes.

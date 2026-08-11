# v0.1.127.1.1.1.1.1 — Single Python authority and acceptance-path repair

Baseline: accepted/current `v0.1.126.1.1.1.1.3`.

This repair preserves the acceptance-path conversation provenance fix from `v0.1.127.1.1.1.1` and adds one release-wide interpreter invariant: the Python executable that launches Promptbranch is the sole authority for release state-machine subprocesses, deterministic validation groups, and release-contract Python/Promptbranch commands. Conflicting interpreter selectors fail closed. PATH-selected `python3` and `pb` are not execution authority; PB contract steps use launcher-Python `-m promptbranch.cli`.

Out of scope: browser behavior, ask routing semantics, response-completion recovery, Project Source semantics, registry edits, acceptance/adoption authority expansion, and normal-slice advancement.

Construction proof requires focused single-Python and provenance-bearing acceptance tests, all canonical deterministic release groups, deterministic ZIP rebuild, and Artifact Guardian. Live closure still requires fresh baseline-routed TESTED_GREEN, independent verification, ACCEPTED, ADOPTED_CURRENT, FINAL_VERIFIED, and fresh scoped current.

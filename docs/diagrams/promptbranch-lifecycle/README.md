# Promptbranch Lifecycle Commands Diagram

This directory contains the editable diagrams.net model and rendered previews for the Promptbranch release lifecycle command flow.

## Files

- `promptbranch_lifecycle_commands.drawio` — editable source diagram for diagrams.net / draw.io.
- `promptbranch_lifecycle_commands.png` — PNG preview suitable for quick viewing and documentation pages.
- `promptbranch_lifecycle_commands.svg` — SVG preview wrapper.

## Scope

The diagram models the command-driven Promptbranch lifecycle from workspace/task selection through structured ask, candidate intake, ZIP verification, Project Source upload, tests, adoption, policy sync, Git sync, and the next baseline-aware ask.

The diagram intentionally separates:

- operator commands;
- repository-local release-control scripts;
- Promptbranch artifact/source state;
- Project Source mutation and verification;
- fail-closed recovery paths.

## Maintenance rule

Treat the `.drawio` file as canonical. Regenerate PNG/SVG previews after structural diagram changes.

## 2026-08-06 MVP boundary page

The editable source now includes `PB MVP Proven Lifecycle and Next Application Loop`. This page distinguishes the proven Promptbranch environment release lifecycle from the future lifecycle of an external application developed using PB. It marks the current transition gate after `candidate_mvp_complete` and lists the remaining environment hardening and first-application pilot stages.

## 2026-08-06 control-plane/application boundary

The draw.io source adds `PB Environment Exit and Application Pilot Roadmap`. The upper lane ends the PB environment proof/hardening line at `v0.1.128`; the lower lane begins the external application track at `v0.1.129`. Application mutation first appears at `v0.1.130`.


## v0.1.125.1 repair gate

The draw.io source includes a dedicated repair page showing the accepted `v0.1.124` baseline, failed `v0.1.125` repeatability proof, active `v0.1.125.1` repair, and the explicit acceptance gate before `v0.1.126`. The repair remains inside the Promptbranch environment/control plane and does not start external application development.

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

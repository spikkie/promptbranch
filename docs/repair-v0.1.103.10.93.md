# Repair v0.1.103.10.93

## Goal

Reconstruct exact Library filenames across rendered whitespace and bind one UI card safely to the unique backend-proven Library object.

## Scope

- preserve authenticated `/backend-api/files/library/nodes` replay from `v0.1.103.10.92`;
- prefer stable filename attributes and child elements;
- reconstruct only the expected basename from contiguous rendered fragments;
- reject partial names, prefixes, numeric-suffix siblings, and ambiguous families;
- require one exact UI record, zero suffix records, and one unique backend `libfile_...`;
- mark and select exactly one matching card;
- fail closed before soft delete, permanent delete, canonical reupload, release `pbsa`, or adoption.

## Classification

- `exact_library_ui_record_selectable`
- `library_ui_filename_reconstruction_failed`
- `library_ui_binding_ambiguous`
- `library_ui_backend_binding_not_proven`

## Baseline

Accepted/current remains `v0.1.103.10.68`. This artifact is diagnostic-only.

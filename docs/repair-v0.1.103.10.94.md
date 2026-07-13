# Repair v0.1.103.10.94

## Goal

Bind the backend-proven Library filename only to one structurally actionable file row and use only that row's action menu.

## Scope

- reject navigation, headers, and ancestor containers;
- reconstruct filenames from local row content only;
- require file metadata or a stable file identity;
- require exactly one row-owned action menu;
- deduplicate by row element identity;
- scope menu opening to the exact row;
- fail closed before delete, canonical reupload, release `pbsa`, or adoption.

## Classification

- `exact_library_actionable_row_bound`
- `library_actionable_row_not_found`
- `library_actionable_row_ambiguous`
- `library_action_menu_not_unique`

## Baseline

Accepted/current remains `v0.1.103.10.68`. This artifact is diagnostic-only.

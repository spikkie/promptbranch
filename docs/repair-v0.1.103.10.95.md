# Repair v0.1.103.10.95

Accepted/current remains `v0.1.103.10.68`.

This diagnostic-only repair separates exact filename-leaf row discovery from hover-activated row-menu discovery. It deduplicates repeated backend inventory observations by exact `libfile_...`, classifies non-authoritative Library surfaces before row binding, stops after a bounded number of identical non-authoritative observations, and keeps soft deletion, permanent deletion, canonical reupload, release `pbsa`, and adoption fail closed until one exact row and one hover-revealed row-owned menu are proven.

Required statuses include:

- `exact_library_file_row_bound`
- `library_surface_not_authoritative_after_backend_presence`
- `library_filename_leaf_not_found`
- `library_file_row_not_found`
- `library_file_row_ambiguous`
- `library_row_menu_not_available_after_hover`
- `library_row_menu_ambiguous`

No Project Source release upload or adoption is performed by this repair.

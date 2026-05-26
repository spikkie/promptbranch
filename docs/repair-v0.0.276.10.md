# Repair v0.0.276.10 — Browser artifact download control detection

## Base release

v0.0.276.9

## Repair version

v0.0.276.10

## Reason

`pb artifact intake --from-last-answer --download` reached the browser-assisted download path but failed with `artifact_link_not_found` because ChatGPT rendered the generated ZIP filename as an entity-style `button`, not as an anchor link. The previous implementation searched only `<a>`/link controls.

## Files changed

- `VERSION`
- `promptbranch_version.py`
- `pyproject.toml`
- `promptbranch_browser_auth/client.py`
- `tests/*.py` version-current assertions
- `docs/repair-v0.0.276.10.md`

## Implementation

The artifact-download browser operation now:

1. waits briefly for visible filename text;
2. scrolls to encourage lazy rendering;
3. searches anchors by accessible name/text;
4. searches buttons by accessible name/text;
5. searches generic filename-bearing controls as fallback;
6. returns richer diagnostics including `filename_text_count` and `buttons_sample` when no clickable control is found.

## Validation performed

- `python3 -m py_compile promptbranch_cli.py promptbranch_browser_auth/client.py promptbranch_version.py`
- focused artifact-intake pytest selection
- ZIP layout and hygiene verification

## Scope control

No slice, line, or planned scope was advanced. This repair only fixes browser-download control detection for the intended artifact-intake MVP behavior.

# Release v0.0.278.75

## Scope

Add `pb test visual-artifact-roundtrip` as a live visual ZIP roundtrip wrapper.

## Behavior

The new test command:

1. creates a small local input ZIP;
2. sends it through the visible local browser path using `pb ask --debug-browser` semantics;
3. asks ChatGPT to create a downloadable output ZIP;
4. downloads the selected ZIP through artifact intake;
5. verifies the returned ZIP with smoke ZIP content checks, not release VERSION/baseline checks.

## Command

```bash
pb test visual-artifact-roundtrip --json \
  --profile-dir ./.pb_profile_local_debug \
  --keep-open
```

Useful deterministic variant:

```bash
pb test visual-artifact-roundtrip --json \
  --profile-dir ./.pb_profile_local_debug \
  --run-id MANUAL \
  --output-filename pb_visual_artifact_roundtrip_MANUAL.zip \
  --expect-entry output.txt \
  --expect-content 'ZIP_VISUAL_ROUNDTRIP_OUTPUT_OK_MANUAL'
```

## Boundaries

- This is a live/browser visual test, not a normal CI test.
- It does not adopt artifacts or mutate release state.
- It verifies transport and ZIP contents only.
- Strict release ZIP verification remains under `pb artifact intake --verify` and `pb artifact verify`.

# Migration: tracked `.promptbranch-repo.json` Project binding

## Applies from

`v0.1.109.1.1`

## Decision

`.promptbranch-repo.json` is stable repository authority. It must be:

- committed to Git;
- present at the repository root;
- included in canonical release ZIPs;
- portable and free of credentials, local paths, current-artifact state, and upload evidence.

The file declares intended identity only. User-local membership and adopted-artifact evidence remain outside Git under the Promptbranch project configuration and state homes.

## Authority split

```text
Git and release ZIP
  .promptbranch-repo.json
  intended stable Project/repository binding

User-local configuration
  ~/.config/promptbranch/projects/<project_id>/repos.json
  checkout-specific repo_root and joined membership

User-local state
  ~/.local/state/promptbranch/projects/<project_id>/promptbranch_artifacts.json
  current adopted artifact and exact Project Source evidence
```

## Required binding shape

```json
{
  "schema_version": 1,
  "project_id": "g-p-...-project-slug",
  "project_home_url": "https://chatgpt.com/g/g-p-...-project-slug/project",
  "repo_id": "my-repository",
  "artifact_pattern": "my-repository_<version>.zip",
  "role": "release_authority"
}
```

Use the repository's actual Project ID, Project URL, canonical repository ID, artifact pattern, and role. Do not copy the Promptbranch repository values into another project.

## Migration procedure for an existing joined repository

1. Start with a clean working tree and inspect the existing binding:

```bash
cd /path/to/repository
cat .promptbranch-repo.json
pb project status --json | jq
```

2. Remove `.promptbranch-repo.json` from `.gitignore` and `.not_to_zip`.

3. Validate that the file contains only the six supported fields shown above and that `artifact_pattern` is `<repo_id>_<version>.zip`.

4. Recreate user-local configuration from the tracked file:

```bash
pb project join --repo-root . --json | jq
```

No Project arguments are required when the tracked file exists. Promptbranch reads the tracked authority and recreates the user-local repository membership and empty project registry when necessary.

5. Validate repository authority:

```bash
pb project authority validate --repo-path . --json | jq
pb project authority validate --repo-path . --include-runtime --json | jq
```

Static validation must accept the tracked binding. Runtime validation additionally requires an adopted artifact record when the authority graph marks it mandatory.

6. Verify ZIP inclusion and hygiene:

```bash
./build.sh
unzip -l "$(pwd)/<repo_id>_<version>.zip" | grep -F '.promptbranch-repo.json'
pb artifact verify "$(pwd)/<repo_id>_<version>.zip" --json | jq
```

7. Commit the authority change:

```bash
git add .promptbranch-repo.json .gitignore .not_to_zip
git commit -m "Track Promptbranch Project binding"
```

## Migration when the binding file is missing

Create it once from known authoritative values:

```bash
pb project join \
  --repo-root . \
  --project-id '<project_id>' \
  --project-home-url '<project_home_url>' \
  --repo-id '<repo_id>' \
  --artifact-pattern '<repo_id>_<version>.zip' \
  --role '<role>' \
  --json | jq
```

Then inspect, validate, and commit `.promptbranch-repo.json`. Promptbranch does not infer the Project ID or Project URL from filenames, Git remotes, conversation history, or another repository.

## Fresh clone or extracted release ZIP

After cloning or extracting, restore local Promptbranch membership with:

```bash
pb project join --repo-root . --json | jq
```

This consumes the tracked binding and recreates only user-local configuration/state. It does not adopt an artifact, upload a Project Source, or mutate ChatGPT Project Settings.

## Mismatch handling

Supplying explicit arguments remains supported for release-control verification. Every supplied value must equal the tracked binding. A mismatch fails closed and does not rewrite the tracked file or create local membership:

```text
tracked project binding mismatch; refusing to rewrite authority
```

Correct the intended binding through an explicit reviewed Git change. Do not use `pb project join` as a silent rebinding mechanism.

## Accidental deletion recovery

Because the binding is tracked, restore it with:

```bash
git restore .promptbranch-repo.json
pb project join --repo-root . --json | jq
```

For an extracted ZIP without Git metadata, re-extract `.promptbranch-repo.json` from the same canonical release ZIP.

## Prohibited contents

Never store any of these in `.promptbranch-repo.json`:

- access tokens, cookies, sessions, credentials, or secrets;
- absolute checkout paths;
- `.pb_profile`, XDG state/config paths, or browser profile paths;
- artifact SHA-256 values, current versions, processed file IDs, Library metadata IDs, or adoption timestamps;
- temporary test Project identities.

Those values are runtime evidence and remain outside the repository.

## Rollout rule

Projects migrate deliberately, one repository at a time. There is no compatibility fallback that silently treats a missing tracked binding as valid. After a project adopts this model, missing or contradictory binding authority fails closed.

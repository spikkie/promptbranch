# v0.1.103.10.4 — standard browser profile default

This repair promotes the Cloudflare-safe Docker/browser path from a temporary
Bonnetjes diagnostic name into the standard Promptbranch browser profile flow.

## Scope

- Standard browser profile defaults to `.pb_profile/browser/default`.
- Docker mounts the standard browser profile as `/app/profile`.
- `PROMPTBRANCH_DOCKER_BROWSER_PROFILE=standard-browser` is the default Docker browser mode.
- Host login bootstrap writes login/session state into `.pb_profile/browser/default` by default.
- Auth-only validation reuses the standard profile by default and only resets it with `--fresh-profile`.
- Existing Bonnetjes script names remain compatibility wrappers.
- Project Source mutation remains disabled.

## Standard paths

```text
Promptbranch state root:  .pb_profile
Browser profile:          .pb_profile/browser/default
Docker browser mount:     .pb_profile/browser/default -> /app/profile
```

## Operator commands

Bootstrap or refresh login state:

```bash
./scripts/pb-browser-profile-bootstrap.sh
```

Run standard browser auth validation:

```bash
./scripts/pb-browser-cloudflare-validation.sh
```

Run a fresh reset only when explicitly needed:

```bash
./scripts/pb-browser-cloudflare-validation.sh --fresh-profile
```

The compatibility wrappers still work:

```bash
./scripts/docker-bonnetjes-clean-login-profile-bootstrap.sh
./scripts/docker-bonnetjes-cloudflare-validation.sh
```

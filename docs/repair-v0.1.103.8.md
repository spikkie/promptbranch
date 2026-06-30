# Repair v0.1.103.8 — Docker Bonnetjes exact Cloudflare parity

`v0.1.103.8` narrows the Docker browser investigation to exact Bonnetjes-style Cloudflare parity.

Scope:

- No Project Source mutation.
- No login flow.
- Add `PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity`.
- Keep `/app/profile`, Xvfb, headed Patchright Chrome, `CHATGPT_DISABLE_FEDCM=1`, and `CHATGPT_FILTER_NO_SANDBOX=0`.
- Disable Promptbranch-only headed Patchright safe args in this mode with `CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS=0`.
- Clear `CHATGPT_BROWSER_EXTRA_ARGS` in this mode.
- Disable the conversation-history request shield in this mode for a cleaner Bonnetjes parity launch.
- Run only the Cloudflare settle loop.
- Capture Chrome argv dumps during the Cloudflare check.
- Provide a wrapper to run both seeded and clean profile cases.

Commands:

```bash
PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity \
PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS=300 \
./scripts/docker-browser-parity-cloudflare-check.sh
```

Seeded and clean profile comparison:

```bash
./scripts/docker-bonnetjes-cloudflare-check.sh --max-wait-seconds 300 --poll-seconds 10
```

This candidate is diagnostic-only and remains candidate-only until live evidence proves the Cloudflare challenge can clear.

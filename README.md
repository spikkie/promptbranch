# ChatGPT ClaudeCode Workflow v0.0.4

This reduced package is a single command-line tool that uses `chatgpt_automation` as the backbone library.
It opens ChatGPT in a persistent browser profile, lets you verify login state, send one-off prompts, or run an interactive shell.

## Files

- `chatgpt_cli.py` — single entrypoint
- `chatgpt_automation/` — automation wrapper
- `chatgpt_browser_auth/` — Playwright/Patchright browser client
- `requirements.txt`

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

If you prefer Patchright-backed launches, keep `patchright` installed.

## Quick start

Headed login check:

```bash
python chatgpt_cli.py login-check --keep-open
```

Global options can be placed either **before or after** the subcommand. These now both work:

```bash
python chatgpt_cli.py --dotenv .env login-check --keep-open
python chatgpt_cli.py login-check --keep-open --dotenv .env
python chatgpt_cli.py ask "hello" --email you@example.com --password-file ~/.config/chatgpt/password.txt
```

Ask one question:

```bash
python chatgpt_cli.py ask "Explain Python context managers in 5 lines"
```

Ask for JSON:

```bash
python chatgpt_cli.py ask --json "Return a JSON object with keys answer and confidence about Rust ownership"
```

Interactive shell:

```bash
python chatgpt_cli.py shell
```

## Shell commands

- `:help`
- `:login`
- `:json on|off`
- `:file <path>`
- `:clearfile`
- `:retry <n>`
- `:show`
- `:quit`

## Environment variables

Optional settings:

- `CHATGPT_PROJECT_URL` default `https://chatgpt.com/`
- `CHATGPT_EMAIL`
- `CHATGPT_PASSWORD`
- `CHATGPT_PASSWORD_FILE`
- `CHATGPT_PROFILE_DIR`
- `CHATGPT_HEADLESS`
- `CHATGPT_BROWSER_CHANNEL`
- `CHATGPT_DEBUG`
- `CHATGPT_MAX_RETRIES`
- `CHATGPT_RETRY_BACKOFF_SECONDS`

## Notes

This is a browser automation proof of concept. The weak points remain the same:

- DOM selector drift on chatgpt.com
- Cloudflare/browser challenges
- session expiration
- manual re-login in headed mode when the profile loses auth state

For a POC and Playwright learning exercise, that is acceptable.


## Parser fix in v0.0.4

The CLI now accepts root options such as `--dotenv`, `--email`, and `--password-file` in either position:

- before the subcommand
- after the subcommand

This fixes the `unrecognized arguments` errors from v0.0.3.

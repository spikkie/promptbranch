# ChatGPT ClaudeCode Workflow v0.0.12

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

Debugging recommendation:

```bash
python chatgpt_cli.py --max-retries 1 ask --dotenv .env "Say hello in one short sentence."
```

In debug mode, the CLI now defaults to `--max-retries 1` unless you explicitly override it or set `CHATGPT_MAX_RETRIES`. This reduces duplicate prompt submissions while you are diagnosing selector issues.

Ask for JSON:

```bash
python chatgpt_cli.py ask --json "Return a JSON object with keys answer and confidence about Rust ownership"
```

Interactive shell:

```bash
python chatgpt_cli.py shell
```

Add a source to a project (requires `CHATGPT_PROJECT_URL` to point at a project page):

```bash
python chatgpt_cli.py project-source-add --type link --value "https://drive.google.com/drive/folders/..." --dotenv .env
python chatgpt_cli.py project-source-add --type text --value "Reference notes for this project" --name "Notes" --dotenv .env
python chatgpt_cli.py project-source-add --type file --file ./docs/spec.pdf --dotenv .env
```

Remove a source from a project:

```bash
python chatgpt_cli.py project-source-remove "Notes" --exact --dotenv .env
python chatgpt_cli.py project-source-remove "drive.google.com" --dotenv .env
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

The new project-source commands depend on the current ChatGPT project UI. As of early 2026, Projects have a dedicated Sources tab and support adding project sources from apps, quick text, and files, but the exact labels and menus can still drift. citeturn347089search0turn347089search1turn347089search9


## Parser fix in v0.0.4

The CLI now accepts root options such as `--dotenv`, `--email`, and `--password-file` in either position:

- before the subcommand
- after the subcommand

This fixes the `unrecognized arguments` errors from v0.0.3.


## Env loading fix in v0.0.6

The CLI now loads `--dotenv` **before** building the main parser, so environment-backed defaults such as:

- `CHATGPT_EMAIL`
- `CHATGPT_PASSWORD`
- `CHATGPT_PASSWORD_FILE`
- `CHATGPT_PROFILE_DIR`

are available to the login flow when you run commands like:

```bash
python chatgpt_cli.py login-check --keep-open --dotenv .env
```

In earlier builds, `.env` could be loaded too late for parser defaults, which left `email=None` even though the file was present.


## Response scraper update in v0.0.7

The assistant-response scraper now uses a multi-selector fallback instead of relying only on:

- `[data-message-author-role="assistant"]`

It now probes additional conversation container selectors and returns the first non-empty trailing response block it can extract. This is intended to handle current ChatGPT DOM variations where the response is visible in the browser but the original assistant selector does not resolve.

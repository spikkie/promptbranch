# promptbranch v0.0.86

promptbranch is a stateful CLI and reusable browser-automation service for ChatGPT projects, sources, and conversations.

Primary interfaces:
- CLI: `promptbranch`
- Python package: `promptbranch`
- HTTP service: FastAPI app in `promptbranch_container_api.py`

Migration notes:
- `UPGRADING.md` documents the v0.0.68 alias removal and old-to-new name mapping
- `docs/howto/README.md` indexes task-focused how-to manuals for each main topic

Legacy `chatgpt_*` command/module/package aliases were removed in v0.0.68. See `UPGRADING.md` for the migration map from old names to `promptbranch_*`.


## How-to manuals

The repository now includes focused manuals under `docs/howto/` instead of forcing everything through one long README. Start with:

- `docs/howto/01-install-the-cli.md`
- `docs/howto/02-run-the-docker-service.md`
- `docs/howto/04-use-the-stateful-cli.md`
- `docs/howto/07-use-the-python-client.md`
- `docs/howto/12-troubleshooting.md`

## Reusable Docker service

Build the image:

```bash
./build_chatgpt_service.sh
```

Or directly:

```bash
docker build -t promptbranch-service:0.0.86 .
```

Run it:

```bash
docker run --rm -it \
  -p 8000:8000 \
  -e CHATGPT_EMAIL="you@example.com" \
  -e CHATGPT_PASSWORD_FILE="/run/secrets/chatgpt_password" \
  -e CHATGPT_PROJECT_URL="https://chatgpt.com/" \
  -e CHATGPT_SERVICE_TOKEN="change-me" \
  -v "$PWD/profile:/app/profile" \
  -v "$PWD/debug_artifacts:/app/debug_artifacts" \
  -v "$HOME/.config/chatgpt/password.txt:/run/secrets/chatgpt_password:ro" \
  promptbranch-service:0.0.86
```

Compose option:

```bash
docker compose -f docker-compose.chatgpt-service.yml up --build
```

Development mode with Compose Watch:

```bash
./run_chatgpt_service_dev.sh
```

This enables `docker compose ... up --watch` and turns on Uvicorn reload inside the container so Python edits are applied without a manual rebuild. Changes to `Dockerfile`, `requirements.txt`, and `pyproject.toml` trigger an image rebuild instead of a file sync.

By default, the compose file now reads the host password file from:

```bash
$HOME/.config/chatgpt/password.txt
```

If your password file lives somewhere else, override it explicitly:

```bash
CHATGPT_PASSWORD_SECRET_FILE="$HOME/.config/chatgpt/password.txt" \
# Host-side `CHATGPT_PASSWORD_FILE` is intentionally ignored by the compose service.
CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS=1 \
  docker compose -f docker-compose.chatgpt-service.yml up --build
```

Or use the helper script:

```bash
./run_chatgpt_service.sh
```

The service starts with:
- Compose `develop.watch` rules for sync/rebuild in development mode
- OpenAPI docs at `/docs`
- health endpoint at `/healthz`
- versioned API under `/v1`


## Testing the Docker service

Start the service first:

```bash
./run_chatgpt_service.sh
```

Equivalent direct compose invocation:

```bash
CHATGPT_PASSWORD_SECRET_FILE="$HOME/.config/chatgpt/password.txt" \
# Host-side `CHATGPT_PASSWORD_FILE` is intentionally ignored by the compose service.
CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS=1 \
  docker compose -f docker-compose.chatgpt-service.yml up --build
```

For auto-reload during development, use `./run_chatgpt_service_dev.sh` instead.

For local headed debugging of the project sidebar using the existing promptbranch login/profile flow (no Docker service), run:

```bash
python ./promptbranch_full_integration_test.py \
  --config ~/.config/promptbranch/config.json \
  --profile-dir ./profile \
  --only project_list_debug \
  --keep-open
```

Optional debug tuning flags:
- `--project-list-debug-scroll-rounds <n>`
- `--project-list-debug-wait-ms <ms>`
- `--project-list-debug-manual-pause`

Then run the existing integration harness against Docker instead of the in-process Python stack:

```bash
python ./promptbranch_full_integration_test.py \
  --service-base-url http://localhost:8000 \
  --service-token change-me
```

Keep the project and skip cleanup while checking the currently stable surface:

```bash
python ./promptbranch_full_integration_test.py \
  --service-base-url http://localhost:8000 \
  --service-token change-me \
  --keep-project \
  --skip "project_source_remove_link,project_source_remove_text,project_source_remove_file"
```

Important:
- `python ./promptbranch_full_integration_test.py` by itself still runs the local Python/browser stack directly.
- Docker mode is enabled only when `--service-base-url` is provided.
- The Docker service can now carry the active `project_url` between steps, so the same integration harness works against both modes.


## API surface

### Health

```bash
curl http://localhost:8000/healthz
```

### Login check

```bash
curl -X POST http://localhost:8000/v1/login-check \
  -H 'Authorization: Bearer change-me' \
  -H 'Content-Type: application/json' \
  -d '{"keep_open": false}'
```

### Ask ChatGPT

```bash
curl -X POST http://localhost:8000/v1/ask \
  -H 'Authorization: Bearer change-me' \
  -F 'prompt=Reply with one short sentence.' \
  -F 'expect_json=false'
```

The response now includes both `answer` and `conversation_url`, so callers can continue the same project chat on follow-up asks.

### Add a text source

```bash
curl -X POST http://localhost:8000/v1/project-sources \
  -H 'Authorization: Bearer change-me' \
  -F 'type=text' \
  -F 'value=Reference notes for this run' \
  -F 'name=Notes'
```

### Add a file source

```bash
curl -X POST http://localhost:8000/v1/project-sources \
  -H 'Authorization: Bearer change-me' \
  -F 'type=file' \
  -F 'file=@./docs/spec.pdf'
```

### Remove a source

```bash
curl -X POST http://localhost:8000/v1/project-sources/remove \
  -H 'Authorization: Bearer change-me' \
  -H 'Content-Type: application/json' \
  -d '{"source_name": "Notes", "exact": true, "keep_open": false}'
```

## Python client for downstream projects

Example:

```python
from promptbranch import ChatGPTServiceClient

with ChatGPTServiceClient("http://localhost:8000", token="change-me") as client:
    print(client.healthz())
    answer = client.ask("Reply with one short sentence that says the service is ready.")
    print(answer)
```

There is also a runnable sample at `examples/promptbranch_service_client_example.py`.

## Installing the promptbranch CLI

Preferred for command-line use:

```bash
pipx install ./chatgpt_claudecode_workflow_v0.0.86.zip
```

From an extracted checkout:

```bash
python -m pip install .
```

After installation the `promptbranch` command is available:


```bash
promptbranch state
promptbranch prompt
promptbranch use "My Project"
promptbranch ask "hello"
```

Shell completion:

```bash
# bash
eval "$(promptbranch completion bash)"

# zsh
mkdir -p ~/.zsh/completions
promptbranch completion zsh > ~/.zsh/completions/_promptbranch

# fish
mkdir -p ~/.config/fish/completions
promptbranch completion fish > ~/.config/fish/completions/promptbranch.fish
```

For other Python programs, prefer importing the package facade instead of the smoke harness:

```python
from promptbranch import ChatGPTServiceClient, ConversationStateStore
```

`promptbranch_cli_sequence_v5.py` remains the primary smoke/integration harness.

## Low-level compatibility CLI usage

The preferred command is `promptbranch`.

The CLI can target either:
- local browser automation directly
- the Docker service API via `--service-base-url`

Headed login check against local automation:

```bash
promptbranch login-check --keep-open
```

Ask one question against local automation:

```bash
promptbranch ask "Explain Python context managers in 5 lines"
```

Ask one question through the Docker service with explicit flags:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me ask "Explain Python context managers in 5 lines"
```

Ask one question through the Docker service without repeating flags each time:

1. Put the service settings in `.env` (loaded automatically by default):

```dotenv
CHATGPT_SERVICE_BASE_URL=http://localhost:8000
CHATGPT_SERVICE_TOKEN=change-me
```

2. Then run the shorter command:

```bash
promptbranch ask "Explain Python context managers in 5 lines"
```

You can also use a JSON config file. The CLI now checks `~/.config/promptbranch/config.json` by default and falls back to `~/.config/chatgpt-cli/config.json` when the new path is absent:

```json
{
  "service_base_url": "http://localhost:8000",
  "service_token": "change-me",
  "service_timeout_seconds": 300
}
```

```bash
promptbranch ask "Explain Python context managers in 5 lines"
promptbranch --config ~/.config/promptbranch/config.json ask "Explain Python context managers in 5 lines"
```

Create a project through the Docker service:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me project-create "Demo Project" --icon folder --color blue
```

Add a text source to a specific project through the Docker service:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me --project-url https://chatgpt.com/g/g-p-.../project project-source-add --type text --value "Reference notes for this project" --name "Notes"
```

Add a file source to a specific project through the Docker service:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me --project-url https://chatgpt.com/g/g-p-.../project project-source-add --type file --file ./docs/spec.pdf
```

Remove a source from a project:

```bash
promptbranch project-source-remove "Notes" --exact --dotenv .env
```

Open the interactive shell through the Docker service:

```bash
promptbranch --service-base-url http://localhost:8000 --service-token change-me shell
```

## Environment variables

Core service settings:
- `CHATGPT_PROJECT_URL`
- `CHATGPT_EMAIL`
- `CHATGPT_PASSWORD`
- `CHATGPT_PASSWORD_FILE` (inside the container this is fixed to `/run/secrets/chatgpt_password` in the compose service)
- `CHATGPT_PROFILE_DIR`
- `CHATGPT_CLI_CONFIG` (optional JSON config file path for CLI defaults)
- `CHATGPT_HEADLESS`
- `CHATGPT_USE_PATCHRIGHT`
- `CHATGPT_BROWSER_CHANNEL`
- `CHATGPT_DISABLE_FEDCM`
- `CHATGPT_FILTER_NO_SANDBOX`
- `CHATGPT_MAX_RETRIES`
- `CHATGPT_RETRY_BACKOFF_SECONDS`
- `CHATGPT_MIN_CONTEXT_SPACING_SECONDS`
- `CHATGPT_CONVERSATION_HISTORY_RATE_LIMIT_COOLDOWN_SECONDS`
- `CHATGPT_SERVICE_TOKEN`
- `CHATGPT_API_TOKEN` (alias for the CLI service token)
- `CHATGPT_SERVICE_BASE_URL`
- `CHATGPT_API_BASE_URL` (alias for the CLI service base URL)
- `CHATGPT_SERVICE_TIMEOUT_SECONDS`
- `CHATGPT_UVICORN_APP`
- `CHATGPT_UVICORN_RELOAD` (enable Uvicorn auto-reload for `docker compose ... up --watch`)
- `PORT`

## Notes

This remains browser automation, so the weak points are unchanged:
- DOM selector drift on chatgpt.com
- Cloudflare or browser challenges
- session expiration
- manual re-login in headed mode when the persistent profile loses auth state
- server-side rate limiting when runs are too aggressive

The added Docker service does not remove those risks. It packages the currently working flow behind a cleaner boundary so other projects can consume it without embedding the browser automation directly.


## Stateful CLI usage

The CLI now keeps lightweight per-profile state in `~/.config/.../<profile>/.promptbranch_state.json` so it can behave more like `git`. If that file is missing it will fall back to the legacy `.chatgpt_cli_state.json`:

- `promptbranch state` shows the remembered current project and conversation
- `promptbranch prompt` emits a compact one-line value for shell prompts or menu-bar widgets
- `promptbranch state-clear` clears the remembered state
- `promptbranch use <project-name|project-url|conversation-url>` selects the current project/chat state
- `promptbranch completion <bash|zsh|fish>` emits shell completion scripts

Typical flow:

```bash
promptbranch project-ensure "My Project"
promptbranch ask --json "hello"
promptbranch prompt
promptbranch state
promptbranch use "My Project"
promptbranch completion bash
```

If no `--project-url` is supplied for project-scoped commands, the CLI reuses the remembered current project when available.

## Python packaging

The preferred Python import surface is now the `promptbranch` package:

```python
from promptbranch import ChatGPTServiceClient, ConversationStateStore
```

The console entry points are installed as:

```bash
promptbranch
chatgpt
```


## List all visible projects

```bash
promptbranch project-list
promptbranch project-list --current
promptbranch project-list --json
```

Select the current project interactively from visible projects:

```bash
promptbranch use --pick
promptbranch use work --pick
```

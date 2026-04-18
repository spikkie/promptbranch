# ChatGPT ClaudeCode Workflow v0.0.49

This build turns the current green `v0.0.45` browser workflow into a reusable Docker-first service that other projects can call over HTTP.

What is stable from the accepted baseline:
- project source add for `text`
- project source add for `file`
- ask flow

What this release adds:
- a dedicated FastAPI app for ChatGPT browser automation: `chatgpt_container_api.py`
- a thin Python client for other projects: `chatgpt_service_client.py`
- a Docker default that now starts the dedicated ChatGPT service instead of the unrelated monolith app
- a compose file and example client script for downstream projects
- optional bearer-token protection for the service via `CHATGPT_SERVICE_TOKEN`

## Reusable Docker service

Build the image:

```bash
./build_chatgpt_service.sh
```

Or directly:

```bash
docker build -t chatgpt-docker-service:0.0.49 .
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
  chatgpt-docker-service:0.0.49
```

Compose option:

```bash
docker compose -f docker-compose.chatgpt-service.yml up --build
```

By default, the compose file now reads the host password file from:

```bash
$HOME/.config/chatgpt/password.txt
```

If your password file lives somewhere else, override it explicitly:

```bash
CHATGPT_PASSWORD_SECRET_FILE="$HOME/.config/chatgpt/password.txt" \
CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS=1 \
  docker compose -f docker-compose.chatgpt-service.yml up --build
```

Or use the helper script:

```bash
./run_chatgpt_service.sh
```

The service starts with:
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
CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS=1 \
  docker compose -f docker-compose.chatgpt-service.yml up --build
```

Then run the existing integration harness against Docker instead of the in-process Python stack:

```bash
python ./chatgpt_full_integration_test.py \
  --service-base-url http://localhost:8000 \
  --service-token change-me
```

Keep the project and skip cleanup while checking the currently stable surface:

```bash
python ./chatgpt_full_integration_test.py \
  --service-base-url http://localhost:8000 \
  --service-token change-me \
  --keep-project \
  --skip "project_source_remove_link,project_source_remove_text,project_source_remove_file"
```

Important:
- `python ./chatgpt_full_integration_test.py` by itself still runs the local Python/browser stack directly.
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
from chatgpt_service_client import ChatGPTServiceClient

with ChatGPTServiceClient("http://localhost:8000", token="change-me") as client:
    print(client.healthz())
    answer = client.ask("Reply with one short sentence that says the service is ready.")
    print(answer)
```

There is also a runnable sample at `examples/chatgpt_service_client_example.py`.

## Running the old monolith app

The repo still contains the previous `main:app` application. If you need that instead of the dedicated ChatGPT service, override the app module:

```bash
docker run --rm -it \
  -e CHATGPT_UVICORN_APP=main:app \
  -p 8000:8000 \
  chatgpt-docker-service:0.0.49
```

## CLI usage remains available

Headed login check:

```bash
python chatgpt_cli.py login-check --keep-open
```

Ask one question:

```bash
python chatgpt_cli.py ask "Explain Python context managers in 5 lines"
```

Add a source to a project:

```bash
python chatgpt_cli.py project-source-add --type text --value "Reference notes for this project" --name "Notes" --dotenv .env
python chatgpt_cli.py project-source-add --type file --file ./docs/spec.pdf --dotenv .env
```

Remove a source from a project:

```bash
python chatgpt_cli.py project-source-remove "Notes" --exact --dotenv .env
```

## Environment variables

Core service settings:
- `CHATGPT_PROJECT_URL`
- `CHATGPT_EMAIL`
- `CHATGPT_PASSWORD`
- `CHATGPT_PASSWORD_FILE`
- `CHATGPT_PROFILE_DIR`
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
- `CHATGPT_UVICORN_APP`
- `PORT`

## Notes

This remains browser automation, so the weak points are unchanged:
- DOM selector drift on chatgpt.com
- Cloudflare or browser challenges
- session expiration
- manual re-login in headed mode when the persistent profile loses auth state
- server-side rate limiting when runs are too aggressive

The added Docker service does not remove those risks. It packages the currently working flow behind a cleaner boundary so other projects can consume it without embedding the browser automation directly.

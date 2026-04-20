# How to configure environment variables and config files

## Goal

Control service defaults, credentials, profile locations, and CLI service access.

## CLI JSON config

Preferred location:

```text
~/.config/promptbranch/config.json
```

Legacy fallback still supported:

```text
~/.config/chatgpt-cli/config.json
```

Example:

```json
{
  "service_base_url": "http://localhost:8000",
  "service_token": "change-me",
  "service_timeout_seconds": 300
}
```

## Important environment variables

- `CHATGPT_PROJECT_URL`
- `CHATGPT_EMAIL`
- `CHATGPT_PASSWORD`
- `CHATGPT_PASSWORD_FILE`
- `CHATGPT_PROFILE_DIR`
- `CHATGPT_SERVICE_BASE_URL`
- `CHATGPT_SERVICE_TOKEN`
- `CHATGPT_SERVICE_TIMEOUT_SECONDS`
- `CHATGPT_UVICORN_APP`
- `CHATGPT_UVICORN_RELOAD`
- `PORT`

## Example with environment-driven CLI use

```bash
promptbranch ask "Explain Python context managers in 5 lines"
```

This stays short when the service settings are already in config or environment.

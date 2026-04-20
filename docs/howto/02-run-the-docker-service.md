# How to run the Docker service

## Goal

Start the FastAPI-backed browser automation service locally.

## Prerequisites

- Docker installed
- a ChatGPT password file on the host
- a persistent profile directory if you want login state to survive restarts

## Quick start

```bash
./run_chatgpt_service.sh
```

This wraps the compose file and starts the `promptbranch-service` image.

## Direct compose start

```bash
CHATGPT_PASSWORD_SECRET_FILE="$HOME/.config/chatgpt/password.txt" CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS=1   docker compose -f docker-compose.chatgpt-service.yml up --build
```

## Development mode

```bash
./run_chatgpt_service_dev.sh
```

Use this when editing Python files and wanting auto-reload.

## Verify the service

```bash
curl http://localhost:8000/healthz
```

Open docs in a browser:

- `http://localhost:8000/docs`

## Stop the service

Use `Ctrl+C` if running attached, or stop the compose stack normally.

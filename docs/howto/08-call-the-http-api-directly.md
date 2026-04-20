# How to call the HTTP API directly

## Goal

Use `curl` or another HTTP client against the FastAPI service.

## Health

```bash
curl http://localhost:8000/healthz
```

## Login check

```bash
curl -X POST http://localhost:8000/v1/login-check   -H 'Authorization: Bearer change-me'   -H 'Content-Type: application/json'   -d '{"keep_open": false}'
```

## Ask

```bash
curl -X POST http://localhost:8000/v1/ask   -H 'Authorization: Bearer change-me'   -F 'prompt=Reply with one short sentence.'   -F 'expect_json=false'
```

## Add a text source

```bash
curl -X POST http://localhost:8000/v1/project-sources   -H 'Authorization: Bearer change-me'   -F 'type=text'   -F 'value=Reference notes for this run'   -F 'name=Notes'
```

## Add a file source

```bash
curl -X POST http://localhost:8000/v1/project-sources   -H 'Authorization: Bearer change-me'   -F 'type=file'   -F 'file=@./docs/spec.pdf'
```

## Remove a source

```bash
curl -X POST http://localhost:8000/v1/project-sources/remove   -H 'Authorization: Bearer change-me'   -H 'Content-Type: application/json'   -d '{"source_name": "Notes", "exact": true, "keep_open": false}'
```

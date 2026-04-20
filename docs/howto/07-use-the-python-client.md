# How to use the Python client

## Goal

Call the promptbranch service from another Python program.

## Basic example

```python
from promptbranch import ChatGPTServiceClient

with ChatGPTServiceClient("http://localhost:8000", token="change-me") as client:
    print(client.healthz())
    result = client.ask("Reply with one short sentence.")
    print(result)
```

## Example file

See:

- `examples/promptbranch_service_client_example.py`

## Typical tasks

- health checks
- login checks
- ask
- project create / resolve / ensure
- add or remove sources

## When to use the client

Use the Python client when another Python service or automation workflow needs a stable interface to the browser-driven ChatGPT automation.

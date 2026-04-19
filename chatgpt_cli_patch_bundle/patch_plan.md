# Patch plan

## 1) `chatgpt_browser_auth/client.py`

### A. Fix `_wait_and_get_json` NameError

Observed failure:

```python
content_present=bool(candidate_text),
NameError: name 'candidate_text' is not defined
```

### Required change

Inside `async def _wait_and_get_json(...)`, initialize the candidate variables **before** any polling loop and before any logging/return path that references them.

Use this pattern:

```python
async def _wait_and_get_json(self, page, response_context=None, ...):
    candidate_text: str = ""
    candidate_json = None
    last_json_error: Exception | None = None
    conversation_url: str = page.url

    # existing polling loop...
    while ...:
        conversation_url = page.url
        candidate_text = await self._extract_latest_assistant_text(page)
        if candidate_text:
            try:
                candidate_json = json.loads(candidate_text)
                # existing success criteria / stability checks
            except Exception as exc:
                last_json_error = exc
        # existing wait / retry logic

    # on success
    return {
        "content": candidate_json,
        "raw_text": candidate_text,
        "conversation_url": conversation_url,
    }
```

### B. Thread `conversation_url` through `ask_question_result`

Add an optional parameter:

```python
async def ask_question_result(
    self,
    prompt: str,
    project_url: str | None = None,
    conversation_url: str | None = None,
    expect_json: bool = False,
    ...
):
```

Thread it into `_run_with_context(...)` and `_ask_question_operation(...)`.

### C. Navigate to a conversation URL when provided

In `_ask_question_operation(...)`, before composing the prompt:

```python
target_url = conversation_url or project_url
if target_url:
    await page.goto(target_url, wait_until="domcontentloaded")
```

Do **not** normalize a `conversation_url` back to the project page. The whole point is to reuse the existing chat thread.

### D. Always return `conversation_url`

Whether `expect_json` is true or false, the final ask result should include:

```python
result["conversation_url"] = page.url
```

That gives the CLI a stable continuation token.

---

## 2) `chatgpt_automation/automation.py`

Update the ask wrapper to accept and forward `conversation_url`:

```python
async def ask_question_result(
    self,
    prompt: str,
    project_url: str | None = None,
    conversation_url: str | None = None,
    expect_json: bool = False,
    ...
):
    return await self.client.ask_question_result(
        prompt=prompt,
        project_url=project_url,
        conversation_url=conversation_url,
        expect_json=expect_json,
        ...
    )
```

---

## 3) `chatgpt_automation/service.py`

Update the public service method signature and forwarding:

```python
async def ask_question_result(
    self,
    prompt: str,
    project_url: str | None = None,
    conversation_url: str | None = None,
    expect_json: bool = False,
    ...
):
    return await self._build_bot().ask_question_result(
        prompt=prompt,
        project_url=project_url,
        conversation_url=conversation_url,
        expect_json=expect_json,
        ...
    )
```

---

## 4) `chatgpt_container_api.py`

For the `/v1/ask` handler, accept `conversation_url` from the JSON payload and forward it unchanged.

Pattern:

```python
payload = await request.json()
result = await _service_for(payload.get("project_url")).ask_question_result(
    prompt=payload["prompt"],
    project_url=payload.get("project_url"),
    conversation_url=payload.get("conversation_url"),
    expect_json=bool(payload.get("expect_json")),
    ...
)
```

The response body should include `conversation_url`.

---

## 5) `chatgpt_service_client.py`

Update the client request model:

```python
async def ask(
    self,
    prompt: str,
    project_url: str | None = None,
    conversation_url: str | None = None,
    expect_json: bool = False,
    ...
):
    payload = {
        "prompt": prompt,
        "project_url": project_url,
        "conversation_url": conversation_url,
        "expect_json": expect_json,
        ...
    }
    return self._json(self._client.post("/v1/ask", json=payload))
```

---

## 6) `chatgpt_cli.py`

### A. Add a new ask option

Add to the `ask` subparser:

```python
ask_parser.add_argument(
    "--conversation-url",
    help="Continue an existing ChatGPT conversation instead of starting from the project page.",
)
```

### B. Forward it in `cmd_ask(...)`

```python
result = await backend.ask(
    prompt=args.prompt,
    project_url=args.project_url,
    conversation_url=args.conversation_url,
    expect_json=args.json,
    ...
)
```

### C. Print the continuation token

For JSON output, ensure the emitted object includes `conversation_url`.

For plain output, print it on a dedicated line before the content:

```python
if result.get("conversation_url"):
    print(f"conversation_url={result['conversation_url']}")
```

That allows the harness to capture it even if the JSON contract changes later.

---

## 7) Optional: add `--conversation-url` to `shell`

Not required for the user's exact request, but it is the obvious symmetry improvement.

---

## 8) Acceptance criteria

The patch is only complete if all of the following hold:

1. `ask --json` no longer raises `NameError` when JSON is parseable.
2. First `ask --json` returns a non-empty `conversation_url`.
3. Second `ask --json --conversation-url <first_url>` returns the **same** `conversation_url`.
4. The second ask is visibly appended to the same chat thread in service logs or UI.
5. The v5 harness exits `0`.

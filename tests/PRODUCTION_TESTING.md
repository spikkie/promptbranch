# Production API smoke tests

These tests are designed to verify that the deployed API is reachable and that the authenticated read paths still work against the live service.

## Safe by default

Default test execution is read-only:
- `GET /`
- `GET /openapi.json`
- `POST /login`
- `GET /protected`
- `GET /receipts`
- `GET /users`
- `POST /token/refresh`

The upload test is opt-in because it mutates production data.

## Required environment variables

```bash
export API_BASE_URL="https://bonnetjes-app.spikkies-it.nl"
export API_TEST_USERNAME="your-production-test-user"
export API_TEST_PASSWORD="your-production-test-password"
```

## Run the production-safe smoke tests

```bash
pytest -m production_safe tests/test_api.py -q
```

## Run the write-path upload test explicitly

```bash
export API_ENABLE_WRITE_TESTS=1
export API_TEST_RECEIPT_FILE="/absolute/path/to/sample-receipt.jpg"
pytest -m write_api tests/test_api.py -q
```

## Notes

- Use a dedicated production test user, not a personal admin account.
- Keep `API_ENABLE_WRITE_TESTS` disabled by default.
- The tests intentionally validate only stable contract points; they do not create or delete users in production.


For slow browser-backed upload diagnostics, set `API_TEST_UPLOAD_TIMEOUT` above the backend wait window. The current diagnostic default is `660` seconds so the backend can finish saving HTML/trace artifacts before the client gives up.

# How to test the service

## Goal

Run the integration harness against either the Docker service or the local browser stack.

## Test the Docker service

Start the service first, then run:

```bash
python ./promptbranch_full_integration_test.py   --service-base-url http://localhost:8000   --service-token change-me
```

## Keep the project for inspection

```bash
python ./promptbranch_full_integration_test.py   --service-base-url http://localhost:8000   --service-token change-me   --keep-project
```

## Test the promptbranch CLI workflow

```bash
python ./promptbranch_cli_sequence_v5.py
```

This covers:

- login check
- project create / resolve / ensure / remove
- source add / remove
- same-chat continuation with `--conversation-url`
- shell

## Run the local stack directly

```bash
python ./promptbranch_full_integration_test.py
```

This bypasses the HTTP service and exercises the local browser automation path.

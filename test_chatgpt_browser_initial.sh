#!/bin/bash
set -euo pipefail

export API_BASE_URL="${API_BASE_URL:-https://bonnetjes-app.spikkies-it.nl}"
export API_TEST_TIMEOUT="${API_TEST_TIMEOUT:-30}"
export API_TEST_BROWSER_TIMEOUT="${API_TEST_BROWSER_TIMEOUT:-300}"

python chatgpt_browser_route_test.py \
  --base-url "$API_BASE_URL" \
  --username "${API_TEST_USERNAME:?API_TEST_USERNAME is required}" \
  --password "${API_TEST_PASSWORD:?API_TEST_PASSWORD is required}" \
  ${API_TEST_RECEIPT_FILE:+--file "$API_TEST_RECEIPT_FILE"}

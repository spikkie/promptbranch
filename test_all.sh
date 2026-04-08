#!/bin/bash
set -euxo pipefail

export API_BASE_URL="https://bonnetjes-app.spikkies-it.nl"
export API_TEST_USERNAME="spikkie"
export API_TEST_PASSWORD="securepassword"
export API_TEST_UPLOAD_TIMEOUT="${API_TEST_UPLOAD_TIMEOUT:-660}"

pytest -m production_safe tests/test_api.py -q

export API_ENABLE_WRITE_TESTS=1
export API_TEST_RECEIPT_FILE="./test.jpeg"

pytest -m write_api tests/test_api.py -q

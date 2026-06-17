# FROM python:3.11-slim
# FROM mcr.microsoft.com/playwright/python:latest
FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy
# FROM mcr.microsoft.com/playwright/python:v1.53.0-jammy

WORKDIR /app

ARG PROMPTBRANCH_VERSION=unknown
ARG PROMPTBRANCH_ARTIFACT_SHA256=unknown
LABEL promptbranch.version="${PROMPTBRANCH_VERSION}"
LABEL promptbranch.artifact_sha256="${PROMPTBRANCH_ARTIFACT_SHA256}"

RUN apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libx11-xcb1 xvfb \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# RUN rm -rf /ms-playwright /root/.cache/ms-playwright 
# && playwright install --with-deps
# RUN playwright install
# RUN playwright install-deps
# RUN playwright install chromium

# RUN rm -rf /ms-playwright /root/.cache/ms-playwright && playwright install --with-deps
RUN patchright install chrome
# RUN playwright install-deps chromium
RUN playwright install --with-deps chromium

RUN rm -rf /app/.pb_profile

COPY . .
RUN python3 - "${PROMPTBRANCH_VERSION}" <<'PY'
from pathlib import Path
import re
import sys

expected = sys.argv[1].strip().removeprefix("v")
version_file = Path("/app/VERSION").read_text(encoding="utf-8", errors="replace").strip().removeprefix("v")
version_py = Path("/app/promptbranch_version.py").read_text(encoding="utf-8", errors="replace")
pyproject = Path("/app/pyproject.toml").read_text(encoding="utf-8", errors="replace")
version_py_match = re.search(r'PACKAGE_VERSION\s*=\s*["\']([^"\']+)["\']', version_py)
pyproject_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', pyproject, re.MULTILINE)
actuals = {
    "VERSION": version_file,
    "promptbranch_version.py": version_py_match.group(1) if version_py_match else "",
    "pyproject.toml": pyproject_match.group(1) if pyproject_match else "",
}
if expected != "unknown":
    mismatches = {key: value for key, value in actuals.items() if value.removeprefix("v") != expected}
    if mismatches:
        print(f"Docker build context version mismatch: expected {expected}; actuals={actuals}", file=sys.stderr)
        raise SystemExit(42)
print(f"Docker build context version verified: expected={expected}; actuals={actuals}")
PY
# Normalize application source permissions for non-root runtime users.
# Host files may have restrictive modes; after COPY, Python must still be able
# to import every module while the container runs as the invoking host UID/GID.
RUN find /app -type d -exec chmod 755 {} \; && \
    find /app -type f -exec chmod 644 {} \; && \
    chmod +x /app/docker/run-chatgpt-service-in-container.sh && \
    find /app -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} \; && \
    if [ -d /app/scripts ]; then find /app/scripts -type f -name '*.sh' -exec chmod +x {} \; ; fi

ENV PYTHONUNBUFFERED=1
ENV CHATGPT_HEADLESS=0
ENV CHATGPT_USE_PATCHRIGHT=1
ENV CHATGPT_BROWSER_CHANNEL=chrome
ENV CHATGPT_DISABLE_FEDCM=1
ENV CHATGPT_FILTER_NO_SANDBOX=0
ENV CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS=1
ENV CHATGPT_UVICORN_APP=promptbranch_container_api:app
ENV CHATGPT_UVICORN_RELOAD=0
ENV PORT=8000

CMD ["/app/docker/run-chatgpt-service-in-container.sh"]

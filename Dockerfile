# FROM python:3.11-slim
# FROM mcr.microsoft.com/playwright/python:latest
FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy
# FROM mcr.microsoft.com/playwright/python:v1.53.0-jammy

WORKDIR /app

ARG PROMPTBRANCH_VERSION=unknown
ARG PROMPTBRANCH_ARTIFACT_SHA256=unknown
ARG PROMPTBRANCH_SOURCE_FINGERPRINT=unknown
LABEL promptbranch.version="${PROMPTBRANCH_VERSION}"
LABEL promptbranch.artifact_sha256="${PROMPTBRANCH_ARTIFACT_SHA256}"
LABEL promptbranch.source_fingerprint="${PROMPTBRANCH_SOURCE_FINGERPRINT}"

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

RUN rm -rf /app/.pb_profile /app/profile

# The source fingerprint is intentionally consumed before COPY so a
# same-size source change with deterministic ZIP mtimes cannot reuse a
# stale build-context layer silently.
RUN printf '%s\n' "${PROMPTBRANCH_SOURCE_FINGERPRINT}" > /tmp/promptbranch_source_fingerprint

COPY . .
RUN python3 - "${PROMPTBRANCH_VERSION}" "${PROMPTBRANCH_SOURCE_FINGERPRINT}" <<'PY'
from pathlib import Path
import hashlib
import re
import sys

expected = sys.argv[1].strip().removeprefix("v")
expected_fingerprint = sys.argv[2].strip() if len(sys.argv) > 2 else "unknown"
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
def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for rel in ("VERSION", "promptbranch_version.py", "pyproject.toml"):
        path = Path("/app") / rel
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
actual_fingerprint = source_fingerprint()
if expected_fingerprint not in ("", "unknown") and actual_fingerprint != expected_fingerprint:
    print(
        f"Docker build context fingerprint mismatch: expected {expected_fingerprint}; actual {actual_fingerprint}; actuals={actuals}",
        file=sys.stderr,
    )
    raise SystemExit(43)
if expected != "unknown":
    mismatches = {key: value for key, value in actuals.items() if value.removeprefix("v") != expected}
    if mismatches:
        print(f"Docker build context version mismatch: expected {expected}; actuals={actuals}", file=sys.stderr)
        raise SystemExit(42)
print(f"Docker build context version verified: expected={expected}; fingerprint={actual_fingerprint}; actuals={actuals}")
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
ENV CHATGPT_DISABLE_FEDCM=0
ENV CHATGPT_FILTER_NO_SANDBOX=0
ENV CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS=1
ENV PROMPTBRANCH_DOCKER_BROWSER_PROFILE=promptbranch
ENV PROMPTBRANCH_PROFILE_DIR=/app/.pb_profile
ENV PROMPTBRANCH_DOCKER_XVFB_SERVICE_MODE=1
ENV PROMPTBRANCH_DOCKER_XVFB_SCREEN=1920x1080x24
ENV CHATGPT_UVICORN_APP=promptbranch_container_api:app
ENV CHATGPT_UVICORN_RELOAD=0
ENV PORT=8000

CMD ["/app/docker/run-chatgpt-service-in-container.sh"]

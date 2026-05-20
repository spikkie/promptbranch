# FROM python:3.11-slim
# FROM mcr.microsoft.com/playwright/python:latest
FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy
# FROM mcr.microsoft.com/playwright/python:v1.53.0-jammy

WORKDIR /app

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

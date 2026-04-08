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

RUN rm -rf /app/profile

COPY . .

ENV PYTHONUNBUFFERED=1
ENV CHATGPT_HEADLESS=0
ENV CHATGPT_USE_PATCHRIGHT=1
ENV CHATGPT_BROWSER_CHANNEL=chrome
ENV CHATGPT_DISABLE_FEDCM=1
ENV CHATGPT_FILTER_NO_SANDBOX=0

CMD ["sh", "-c", "xvfb-run -a -s '-screen 0 1920x1080x24' uvicorn main:app --host 0.0.0.0 --port 8000"]

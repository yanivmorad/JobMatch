# JobMatch API server + background workers (resolver / scraper / AI)
#
# Python 3.12 (3.10 reached end-of-life in Oct 2026).
# bookworm = Debian 12, an OS that `playwright install --with-deps` officially supports.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY requirements.txt .

# Only the Chromium headless shell: the code always launches headless=True,
# so the full Chromium build is never used.
RUN pip install -r requirements.txt \
    && playwright install --with-deps --only-shell chromium \
    && rm -rf /var/lib/apt/lists/*

COPY src/ ./src/

# Run as non-root. data/ (resume + context) and logs/ are mounted at runtime.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data /app/logs \
    && chown -R app:app /app
USER app

EXPOSE 8000

# PORT is injected by most PaaS providers (Render included); 8000 locally.
CMD ["sh", "-c", "exec uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8000}"]

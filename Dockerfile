# JobMatch: API server + background workers (resolver / scraper / AI) + the built dashboard,
# in one service. The dashboard is served by FastAPI from the same origin as the API.
#
#   docker build -t jobmatch .                                   # with Playwright + Chromium
#   docker build -t jobmatch --build-arg INSTALL_PLAYWRIGHT=false .   # smaller, no browser
#
# Without the browser, set ENABLE_PLAYWRIGHT=false at runtime: the scraper then relies on the
# ATS APIs + Jina, and HireMeTech links are analyzed from their public page.

# --- 1. dashboard (static build) ---
FROM node:22-alpine AS dashboard
WORKDIR /dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY dashboard/ ./
# Empty VITE_API_URL = same origin (the server below serves the dashboard)
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# --- 2. server ---
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
ARG INSTALL_PLAYWRIGHT=true
RUN pip install -r requirements.txt \
    && if [ "$INSTALL_PLAYWRIGHT" = "true" ]; then \
         playwright install --with-deps --only-shell chromium; \
       fi \
    && rm -rf /var/lib/apt/lists/*

COPY src/ ./src/
COPY --from=dashboard /dashboard/dist ./dashboard/dist

# Run as non-root. data/ (optional resume/context seed files) and logs/ may be mounted.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data /app/logs \
    && chown -R app:app /app
USER app

EXPOSE 8000

# PORT is injected by most PaaS providers (Render included); 8000 locally.
CMD ["sh", "-c", "exec uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8000}"]

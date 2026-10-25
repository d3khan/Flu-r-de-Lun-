# Dockerfile for Fluér de Luné — Django e-commerce
# Host target: blitz.cloud (Docker container deployment)
#
# Build:
#   docker build -t fluer-de-lune .
# Run (locally, mimicking the platform):
#   docker run -e DATABASE_URL=... -e DJANGO_SECRET_KEY=... \
#     -e DJANGO_ALLOWED_HOSTS=your-app.blitzcloud.app -p 8000:8000 fluer-de-lune

FROM python:3.13-slim

# Keep Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Use the production settings module explicitly so the platform does not
    # need to set RENDER_EXTERNAL_HOSTNAME (Render-specific auto-detect).
    DJANGO_SETTINGS_MODULE=config.settings.production \
    # Port the container listens on; blitz.cloud injects PORT at runtime.
    PORT=8000 \
    # Gunicorn worker count (override with WEB_CONCURRENCY at runtime).
    WEB_CONCURRENCY=3

WORKDIR /app

# System dependencies.
#   libjpeg62-turbo — Pillow image support
#   libpq5          — PostgreSQL client libs (psycopg2-binary bundles its own,
#                     but keeping the client lib is harmless)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (production + base).
COPY requirements/base.txt requirements/production.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements/production.txt

# Copy the application code.
COPY . .

# Expose the app port.
EXPOSE ${PORT}

# The entrypoint runs migrations + collectstatic (needs a live DB + env vars)
# before starting gunicorn, so it must run at container start, not build time.
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:${PORT}", "--workers", "${WEB_CONCURRENCY}", "--timeout", "120"]

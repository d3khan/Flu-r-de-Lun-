#!/bin/sh
set -e

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Creating superuser (if credentials provided)..."
if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] \
   && [ -n "${DJANGO_SUPERUSER_EMAIL}" ] \
   && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
  python manage.py createsuperuser --noinput 2>/dev/null || true
else
  echo "     (skipped: DJANGO_SUPERUSER_* not all set)"
fi

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting gunicorn on 0.0.0.0:${PORT:-8000}..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout 120

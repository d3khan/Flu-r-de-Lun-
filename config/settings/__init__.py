"""
Settings package initialization.

Resolves the active settings module:

1. An explicit DJANGO_SETTINGS_MODULE of "config.settings.production" or
   "config.settings.development" is honoured as-is.
2. Otherwise (e.g. manage.py/wsgi.py set the generic "config.settings"),
   auto-detect: when running on Render (RENDER_EXTERNAL_HOSTNAME is set by
   the platform) use production settings so the external Postgres from
   DATABASE_URL is used and data persists across deploys. Locally fall back
   to base settings.
"""
import os

settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings')
on_render = bool(os.environ.get('RENDER_EXTERNAL_HOSTNAME'))

if settings_module == 'config.settings.production' or (settings_module == 'config.settings' and on_render):
    from .production import *
elif settings_module == 'config.settings.development':
    from .development import *
else:
    from .base import *
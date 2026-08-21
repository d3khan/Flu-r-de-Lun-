"""
Settings package initialization.
Loads appropriate settings module based on DJANGO_SETTINGS_MODULE env var.
"""
import os

# Default to development settings
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.development')

if settings_module == 'config.settings.production':
    from .production import *
elif settings_module == 'config.settings.development':
    from .development import *
else:
    from .base import *
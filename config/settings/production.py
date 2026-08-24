"""
Production settings for Fluér de Luné project.
"""
from .base import *
import dj_database_url

DEBUG = False

# Security
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Security headers
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Static files with WhiteNoise compression
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        # Serve unhashed URLs instead of raising when a file is missing
        # from the manifest (e.g. first boot before collectstatic).
        "OPTIONS": {"manifest_strict": False},
    },
}

# WhiteNoise
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_ALLOW_ALL_ORIGINS = True

# ImgBB Media Storage
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY')

# Email - DISABLED (under development)
# EMAIL_BACKEND = 'apps.core.email_backends.resend_backend.ResendEmailBackend'
# RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
EMAIL_FROM_ADDRESS = os.environ.get('EMAIL_FROM_ADDRESS')
DEFAULT_FROM_EMAIL = f'Fluér de Luné <{os.environ.get("EMAIL_FROM_ADDRESS")}>'

# Password reset timeout - 10 minutes minimum
PASSWORD_RESET_TIMEOUT = 600

# Email timeout to prevent hanging
EMAIL_TIMEOUT = 30

# Cache: LocMemCache by default (safe for the free plan). Set USE_REDIS=true
# in the environment to opt in to the shared Redis instance instead.
USE_REDIS = os.environ.get('USE_REDIS', '').lower() in ('true', '1', 'yes')
REDIS_LOCATION = os.environ.get('REDIS_URL')

if USE_REDIS and REDIS_LOCATION:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_LOCATION,
        }
    }
    # Cache-backed sessions are only safe when every worker shares one Redis.
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Per-worker local memory cache; sessions live in the (Postgres) database
    # so they survive worker restarts without any extra infrastructure.
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
"""
Base settings for Fluér de Luné project.
"""
import os
import re
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',

    # Third-party
    'crispy_forms',
    'crispy_bootstrap5',
    'django_countries',
    'django_htmx',

    # Local apps
    'apps.core',
    'apps.products',
    'apps.cart',
    'apps.wishlist',
    'apps.accounts',
    'apps.orders',
    'apps.payments',
    'apps.checkout',
    'apps.inventory',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'apps.core.context_processors.site_settings',
                'apps.cart.context_processors.cart',
                'apps.wishlist.context_processors.wishlist',
                'apps.products.context_processors.nav_categories',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Login/Logout URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'

# Sites framework
SITE_ID = 1

# Email (configure for production)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Fluér de Luné <noreply@fleurdelune.com>'

# Password reset links are delivered by staff over WhatsApp, so keep the link
# short-lived. Django's token generator reads this setting.
PASSWORD_RESET_TIMEOUT = int(os.environ.get('PASSWORD_RESET_TIMEOUT') or 600)

# App version for cache busting
APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')

# Currency
CURRENCY_SYMBOL = '₦'
CURRENCY_CODE = 'NGN'

# Canonical site URL (used in emails, canonical links, etc.)
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

# Canonical contact details. The business line is 0810 426 0003. Numbers are
# normalised to international format for wa.me links, while the display value
# stays readable. Known stale deployment values are ignored so an old number
# can never come back across the storefront, checkout or WhatsApp hand-off.
CANONICAL_WHATSAPP_NUMBER = '2348104260003'
CANONICAL_CONTACT_PHONE = '+234 810 426 0003'
_STALE_PHONE_DIGITS = {'2347080781217', '2348127918480'}


def _digits(value):
    return re.sub(r'\D', '', value or '')


def normalize_whatsapp_number(value):
    """Return a wa.me-compatible number: 08104260003 -> 2348104260003."""
    digits = _digits(value)
    if len(digits) == 11 and digits.startswith('0'):
        return f'234{digits[1:]}'
    if len(digits) == 10:
        return f'234{digits}'
    return digits


def format_phone(value):
    """Display a Nigerian number in +234 810 426 0003 form."""
    digits = normalize_whatsapp_number(value)
    if len(digits) == 13 and digits.startswith('234'):
        return f'+{digits[:3]} {digits[3:6]} {digits[6:9]} {digits[9:]}'
    return value or ''


_configured_whatsapp = normalize_whatsapp_number(os.environ.get('WHATSAPP_NUMBER', '').strip())
WHATSAPP_NUMBER = (
    _configured_whatsapp
    if _configured_whatsapp and _configured_whatsapp not in _STALE_PHONE_DIGITS
    else CANONICAL_WHATSAPP_NUMBER
)

_configured_phone = os.environ.get('CONTACT_PHONE', '').strip()
CONTACT_PHONE = (
    format_phone(_configured_phone)
    if _configured_phone and _digits(_configured_phone) not in _STALE_PHONE_DIGITS
    else CANONICAL_CONTACT_PHONE
)

# ImgBB Media Storage
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY', '')

# Session settings
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days
SESSION_SAVE_EVERY_REQUEST = True
# Guest sessions (carts) self-destruct when the browser closes.
# Logged-in users get a 30-day extension applied right after login/registration
# (see CustomLoginView / RegisterView), so accounts stay remembered while
# anonymous data truly expires on exit.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# UI: Max characters before word break (for long unbroken strings like product names)
MAX_WORD_LENGTH = int(os.environ.get('MAX_WORD_LENGTH', '10'))

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
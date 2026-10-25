"""Helpers for the single WhatsApp order flow used across the storefront."""
import re
from urllib.parse import quote

from django.conf import settings


def whatsapp_digits(number=None):
    """Return a wa.me-compatible number (international digits only)."""
    value = number if number is not None else getattr(settings, 'WHATSAPP_NUMBER', '')
    digits = re.sub(r'\D', '', value or '')
    if len(digits) == 11 and digits.startswith('0'):
        return f'234{digits[1:]}'
    if len(digits) == 10:
        return f'234{digits}'
    return digits


def build_whatsapp_url(message='', number=None):
    """Build a wa.me URL with an optional pre-filled message."""
    digits = whatsapp_digits(number)
    if not digits:
        return '#'
    url = f'https://wa.me/{digits}'
    if message:
        url = f'{url}?text={quote(message, safe="")}'
    return url


def order_message(order):
    """Pre-filled message a customer sends after placing an order."""
    return (
        f'Hello Fluér de Luné! I just placed order {order.order_number}. '
        f'Name: {order.full_name}. '
        f'Total: ₦{order.total:,.2f}. '
        'Please help me complete this order and let me know how I can receive it.'
    )


def order_whatsapp_url(order):
    return build_whatsapp_url(order_message(order))

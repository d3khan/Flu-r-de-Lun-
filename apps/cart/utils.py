"""
Shared shipping calculation utilities for cart and checkout.
"""
import os


# Read from environment with sensible defaults
SHIPPING_COST = int(os.environ.get('SHIPPING_COST', '1500'))
FREE_SHIPPING_THRESHOLD = int(os.environ.get('FREE_SHIPPING_THRESHOLD', '50000'))


def calculate_shipping(subtotal):
    """
    Calculate shipping cost based on subtotal.
    Free shipping when subtotal >= FREE_SHIPPING_THRESHOLD.
    """
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        return 0
    return SHIPPING_COST
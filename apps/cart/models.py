from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.products.models import Product
from apps.cart.utils import calculate_shipping


class Cart(models.Model):
    """Shopping cart for both authenticated and anonymous users."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name=_('User')
    )
    session_key = models.CharField(_('Session Key'), max_length=40, blank=True, db_index=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Cart')
        verbose_name_plural = _('Carts')
        ordering = ['-updated_at']

    def __str__(self):
        if self.user:
            return f'Cart for {self.user.email}'
        return f'Anonymous Cart ({self.session_key[:8]}...)'

    @property
    def total_items(self):
        """Total quantity of all items."""
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        """Total price of all items (subtotal)."""
        return sum(item.total_price for item in self.items.all())

    @property
    def shipping_cost(self):
        """Shipping cost for this cart."""
        return calculate_shipping(self.total_price)

    @property
    def grand_total(self):
        """Grand total including shipping."""
        return self.total_price + self.shipping_cost

    @property
    def item_count(self):
        """Number of distinct items."""
        return self.items.count()

    def add_item(self, product, quantity=1):
        """Add or update item in cart."""
        item, created = self.items.get_or_create(
            product=product,
            defaults={'quantity': quantity}
        )
        if not created:
            item.quantity += quantity
            item.save()
        return item

    def remove_item(self, product):
        """Remove item from cart."""
        self.items.filter(product=product).delete()

    def clear(self):
        """Clear all items."""
        self.items.all().delete()

    def merge_with(self, other_cart):
        """Merge another cart into this one (e.g., on login)."""
        for item in other_cart.items.all():
            existing = self.items.filter(product=item.product).first()
            if existing:
                existing.quantity += item.quantity
                existing.save()
            else:
                item.cart = self
                item.save()
        other_cart.delete()


class CartItem(models.Model):
    """Individual item in a cart."""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Cart')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name=_('Product')
    )
    quantity = models.PositiveIntegerField(_('Quantity'), default=1)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Cart Item')
        verbose_name_plural = _('Cart Items')
        unique_together = ['cart', 'product']
        ordering = ['created_at']

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

    @property
    def total_price(self):
        """Total price for this line item."""
        return self.product.price * self.quantity

    def can_increase_quantity(self):
        """Check if quantity can be increased based on stock."""
        return self.quantity < self.product.stock_quantity

    def get_max_quantity(self):
        """Get maximum allowed quantity."""
        return self.product.stock_quantity
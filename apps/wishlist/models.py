from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.products.models import Product


class Wishlist(models.Model):
    """User wishlist."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist',
        verbose_name=_('User')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Wishlist')
        verbose_name_plural = _('Wishlists')

    def __str__(self):
        return f'Wishlist for {self.user.email}'

    @property
    def total_items(self):
        return self.items.count()

    def add_product(self, product):
        """Add product to wishlist."""
        item, created = self.items.get_or_create(product=product)
        return item, created

    def remove_product(self, product):
        """Remove product from wishlist."""
        self.items.filter(product=product).delete()

    def has_product(self, product):
        """Check if product is in wishlist."""
        return self.items.filter(product=product).exists()

    def move_to_cart(self, product, cart):
        """Move product from wishlist to cart."""
        self.remove_product(product)
        cart.add_item(product)


class WishlistItem(models.Model):
    """Individual item in a wishlist."""
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Wishlist')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name=_('Product')
    )
    added_at = models.DateTimeField(_('Added At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Wishlist Item')
        verbose_name_plural = _('Wishlist Items')
        unique_together = ['wishlist', 'product']
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.product.name} in wishlist'
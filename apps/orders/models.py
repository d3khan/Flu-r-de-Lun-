from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

from apps.products.models import Product


class Order(models.Model):
    """Customer order."""
    PAYMENT_METHOD_CHOICES = [
        ('gateway', _('Payment Gateway')),
        ('manual', _('Manual Transfer')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('confirmed', _('Confirmed')),
        ('processing', _('Processing')),
        ('shipped', _('Shipped')),
        ('delivered', _('Delivered')),
        ('cancelled', _('Cancelled')),
        ('refunded', _('Refunded')),
    ]

    # User relation (nullable for guest orders)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name=_('User')
    )
    session_key = models.CharField(_('Session Key'), max_length=40, blank=True)
    
    # Order number (human-readable)
    order_number = models.CharField(_('Order Number'), max_length=20, unique=True, editable=False)
    
    # Customer info (snapshot at time of order)
    first_name = models.CharField(_('First Name'), max_length=100)
    last_name = models.CharField(_('Last Name'), max_length=100)
    email = models.EmailField(_('Email'))
    phone = models.CharField(_('Phone'), max_length=20)
    
    # Shipping address
    shipping_address_line_1 = models.CharField(_('Address Line 1'), max_length=255)
    shipping_address_line_2 = models.CharField(_('Address Line 2'), max_length=255, blank=True)
    shipping_city = models.CharField(_('City'), max_length=100)
    shipping_state = models.CharField(_('State'), max_length=100)
    shipping_postal_code = models.CharField(_('Postal Code'), max_length=20, blank=True)
    shipping_country = CountryField(_('Country'), default='NG')
    
    # Billing address (optional, separate from shipping)
    billing_same_as_shipping = models.BooleanField(_('Same as Shipping'), default=True)
    billing_first_name = models.CharField(_('Billing First Name'), max_length=100, blank=True)
    billing_last_name = models.CharField(_('Billing Last Name'), max_length=100, blank=True)
    billing_address_line_1 = models.CharField(_('Billing Address Line 1'), max_length=255, blank=True)
    billing_address_line_2 = models.CharField(_('Billing Address Line 2'), max_length=255, blank=True)
    billing_city = models.CharField(_('Billing City'), max_length=100, blank=True)
    billing_state = models.CharField(_('Billing State'), max_length=100, blank=True)
    billing_postal_code = models.CharField(_('Billing Postal Code'), max_length=20, blank=True)
    billing_country = CountryField(_('Billing Country'), default='NG', blank=True)
    
    # Payment
    payment_method = models.CharField(_('Payment Method'), max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_reference = models.CharField(_('Payment Reference'), max_length=100, blank=True)
    payment_verified = models.BooleanField(_('Payment Verified'), default=False)
    payment_verified_at = models.DateTimeField(_('Payment Verified At'), null=True, blank=True)
    
    # Totals
    subtotal = models.DecimalField(_('Subtotal'), max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(_('Shipping Cost'), max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(_('Discount'), max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(_('Tax'), max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(_('Total'), max_digits=10, decimal_places=2)
    
    # Status
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(_('Notes'), blank=True)
    
    # Tracking
    tracking_number = models.CharField(_('Tracking Number'), max_length=100, blank=True)
    tracking_url = models.URLField(_('Tracking URL'), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    confirmed_at = models.DateTimeField(_('Confirmed At'), null=True, blank=True)
    shipped_at = models.DateTimeField(_('Shipped At'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('Delivered At'), null=True, blank=True)
    cancelled_at = models.DateTimeField(_('Cancelled At'), null=True, blank=True)

    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['order_number']),
        ]

    def __str__(self):
        return f'Order {self.order_number}'

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('orders:detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate unique order number."""
        import uuid
        return f'FDL-{uuid.uuid4().hex[:8].upper()}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def shipping_full_address(self):
        lines = [self.shipping_address_line_1]
        if self.shipping_address_line_2:
            lines.append(self.shipping_address_line_2)
        lines.append(f'{self.shipping_city}, {self.shipping_state}')
        if self.shipping_postal_code:
            lines.append(self.shipping_postal_code)
        lines.append(str(self.shipping_country))
        return '\n'.join(lines)

    @property
    def can_cancel(self):
        return self.status in ['pending', 'confirmed']

    @property
    def is_paid(self):
        return self.payment_verified or self.payment_method == 'manual'


class OrderItem(models.Model):
    """Individual line item in an order."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Order')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Product')
    )
    # Snapshot of product data at time of order
    product_name = models.CharField(_('Product Name'), max_length=200)
    product_sku = models.CharField(_('Product SKU'), max_length=50, blank=True)
    product_image = models.ImageField(_('Product Image'), upload_to='orders/', blank=True)
    price = models.DecimalField(_('Price'), max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(_('Quantity'))
    
    class Meta:
        verbose_name = _('Order Item')
        verbose_name_plural = _('Order Items')
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} x {self.product_name}'

    @property
    def total_price(self):
        return self.price * self.quantity


class OrderStatusHistory(models.Model):
    """Track order status changes."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name=_('Order')
    )
    status = models.CharField(_('Status'), max_length=20, choices=Order.STATUS_CHOICES)
    note = models.TextField(_('Note'), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Order Status History')
        verbose_name_plural = _('Order Status History')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.order_number} - {self.get_status_display()}'
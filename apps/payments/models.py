from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Order


class ManualPaymentInfo(models.Model):
    """Bank and WhatsApp details for manual payments."""
    bank_name = models.CharField(_('Bank Name'), max_length=100)
    account_name = models.CharField(_('Account Name'), max_length=100)
    account_number = models.CharField(_('Account Number'), max_length=20)
    whatsapp_number = models.CharField(
        _('WhatsApp Number'),
        max_length=20,
        help_text=_('Format: 2348012345678 (no + or spaces)')
    )
    whatsapp_message_template = models.TextField(
        _('WhatsApp Message Template'),
        default=_('Hi Fluér de Luné, I want to pay for order {order_number}. Amount: {amount}. My name: {name}')
    )
    instructions = models.TextField(_('Instructions'), blank=True,
        help_text=_('Additional instructions for manual payment'))
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Manual Payment Info')
        verbose_name_plural = _('Manual Payment Info')

    def __str__(self):
        return f'{self.bank_name} - {self.account_name}'

    def get_whatsapp_url(self, order):
        """Generate WhatsApp URL with pre-filled message."""
        message = self.whatsapp_message_template.format(
            order_number=order.order_number,
            amount=f'{order.total:,.2f}',
            name=order.full_name,
            email=order.email,
            phone=order.phone
        )
        import urllib.parse
        encoded_message = urllib.parse.quote(message)
        return f'https://wa.me/{self.whatsapp_number}?text={encoded_message}'

    def save(self, *args, **kwargs):
        # Ensure only one active instance
        if self.is_active:
            ManualPaymentInfo.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()


class PaymentTransaction(models.Model):
    """Payment transaction record for gateway payments."""
    GATEWAY_CHOICES = [
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('success', _('Success')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='transaction',
        verbose_name=_('Order')
    )
    gateway = models.CharField(_('Gateway'), max_length=20, choices=GATEWAY_CHOICES)
    reference = models.CharField(_('Reference'), max_length=100, unique=True)
    amount = models.DecimalField(_('Amount'), max_digits=10, decimal_places=2)
    currency = models.CharField(_('Currency'), max_length=3, default='NGN')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Gateway response data
    gateway_response = models.JSONField(_('Gateway Response'), default=dict, blank=True)
    gateway_reference = models.CharField(_('Gateway Reference'), max_length=100, blank=True)
    
    # Customer info (for reconciliation)
    customer_email = models.EmailField(_('Customer Email'))
    customer_name = models.CharField(_('Customer Name'), max_length=200)
    
    # Metadata
    metadata = models.JSONField(_('Metadata'), default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    verified_at = models.DateTimeField(_('Verified At'), null=True, blank=True)
    paid_at = models.DateTimeField(_('Paid At'), null=True, blank=True)

    class Meta:
        verbose_name = _('Payment Transaction')
        verbose_name_plural = _('Payment Transactions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['gateway_reference']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f'{self.gateway} - {self.reference} - {self.status}'

    def mark_success(self, gateway_response=None):
        """Mark transaction as successful."""
        from django.utils import timezone
        self.status = 'success'
        self.verified_at = timezone.now()
        self.paid_at = timezone.now()
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()
        
        # Update order
        self.order.payment_verified = True
        self.order.payment_verified_at = timezone.now()
        self.order.payment_reference = self.reference
        self.order.status = 'confirmed'
        self.order.confirmed_at = timezone.now()
        self.order.save()

    def mark_failed(self, gateway_response=None):
        """Mark transaction as failed."""
        self.status = 'failed'
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()


class PaymentLink(models.Model):
    """Generated payment links for hosted checkout."""
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment_link',
        verbose_name=_('Order')
    )
    gateway = models.CharField(_('Gateway'), max_length=20, choices=PaymentTransaction.GATEWAY_CHOICES)
    url = models.URLField(_('Payment URL'))
    reference = models.CharField(_('Reference'), max_length=100)
    expires_at = models.DateTimeField(_('Expires At'))
    is_used = models.BooleanField(_('Used'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Payment Link')
        verbose_name_plural = _('Payment Links')

    def __str__(self):
        return f'Payment Link for {self.order.order_number}'

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
import os
import re

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def default_contact_email():
    """Contact email from environment (.env is the source of truth)."""
    return os.environ.get('CONTACT_EMAIL', '')


class SiteSettings(models.Model):
    """Singleton model for site-wide settings."""
    site_name = models.CharField(_('Site Name'), max_length=100, default='Fluér de Luné')
    site_tagline = models.CharField(_('Tagline'), max_length=200, default='Minimalist Luxury Eyewear')
    logo = models.ImageField(_('Logo'), upload_to='site/', blank=True)
    favicon = models.ImageField(_('Favicon'), upload_to='site/', blank=True)
    
    # Contact info
    email = models.EmailField(_('Contact Email'), default=default_contact_email)
    phone = models.CharField(_('Phone'), max_length=20, blank=True)
    address = models.TextField(_('Address'), blank=True)
    
    # Social media
    instagram_url = models.URLField(_('Instagram'), blank=True)
    facebook_url = models.URLField(_('Facebook'), blank=True)
    twitter_url = models.URLField(_('Twitter/X'), blank=True)
    tiktok_url = models.URLField(_('TikTok'), blank=True)
    
    # Business WhatsApp line used for every order hand-off
    whatsapp_number = models.CharField(_('WhatsApp Number'), max_length=20,
        help_text=_('Format: 2347080781217 (no + or spaces)'), blank=True)
    whatsapp_message = models.TextField(_('WhatsApp Message Template'),
        default=_('Hi Fluér de Luné, I want to inquire about {product_name}.'), blank=True)

    # Customer support expectations
    business_hours = models.CharField(_('Business Hours'), max_length=200, blank=True,
        help_text=_('e.g. Mon-Sat, 9:00am-6:00pm WAT'))
    response_time = models.CharField(_('Response Time'), max_length=100, blank=True,
        help_text=_('e.g. We typically reply within 2 hours'))
    
    # SEO
    meta_description = models.TextField(_('Meta Description'), max_length=160, blank=True)
    meta_keywords = models.TextField(_('Meta Keywords'), blank=True)
    
    # Analytics
    google_analytics_id = models.CharField(_('Google Analytics ID'), max_length=50, blank=True)
    facebook_pixel_id = models.CharField(_('Facebook Pixel ID'), max_length=50, blank=True)
    
    class Meta:
        verbose_name = _('Site Settings')
        verbose_name_plural = _('Site Settings')
    
    def __str__(self):
        return self.site_name

    @property
    def logo_exists(self):
        """Return True only when the stored logo file can actually be served."""
        if not self.logo:
            return False
        try:
            return self.logo.storage.exists(self.logo.name)
        except Exception:
            return False

    @property
    def phone_href(self):
        """Dial-safe phone value for tel: links."""
        return re.sub(r'[^\d+]', '', self.phone or '')

    def save(self, *args, **kwargs):
        # Enforce singleton and keep the WhatsApp number in wa.me format.
        self.pk = 1
        if self.whatsapp_number:
            self.whatsapp_number = re.sub(r'\D', '', self.whatsapp_number)
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the singleton instance and enforce canonical contacts."""
        obj, created = cls.objects.get_or_create(pk=1)

        # Environment variables are the source of truth for editable contact
        # copy. The WhatsApp number and phone are canonical settings so every
        # page and template always points at the same business line.
        env_sync = {
            'email': (os.environ.get('CONTACT_EMAIL', '').strip(), None),
            'business_hours': (os.environ.get('BUSINESS_HOURS', '').strip(), None),
            'response_time': (os.environ.get('RESPONSE_TIME', '').strip(), None),
            'whatsapp_number': (getattr(settings, 'WHATSAPP_NUMBER', ''), 'digits'),
            'phone': (getattr(settings, 'CONTACT_PHONE', ''), None),
        }
        changed = []
        for field, (value, transform) in env_sync.items():
            if transform == 'digits':
                value = re.sub(r'\D', '', value or '')
            if value and getattr(obj, field) != value:
                setattr(obj, field, value)
                changed.append(field)
        if changed:
            obj.save(update_fields=changed)
        return obj


class ContactMessage(models.Model):
    """Contact form submissions."""
    name = models.CharField(_('Name'), max_length=100)
    email = models.EmailField(_('Email'))
    phone = models.CharField(_('Phone'), max_length=20, blank=True)
    subject = models.CharField(_('Subject'), max_length=200)
    message = models.TextField(_('Message'))
    is_read = models.BooleanField(_('Read'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Contact Message')
        verbose_name_plural = _('Contact Messages')
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} - {self.subject}'
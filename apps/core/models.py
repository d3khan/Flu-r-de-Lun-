from django.db import models
from django.utils.translation import gettext_lazy as _
import os


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
    
    # WhatsApp for manual orders
    whatsapp_number = models.CharField(_('WhatsApp Number'), max_length=20, 
        help_text=_('Format: 2348012345678 (no + or spaces)'), blank=True)
    whatsapp_message = models.TextField(_('WhatsApp Message Template'), 
        default=_('Hi Fluér de Luné, I want to inquire about {product_name}.'), blank=True)
    
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
    
    def save(self, *args, **kwargs):
        # Enforce singleton
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get or create the singleton instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        # The .env CONTACT_EMAIL is the source of truth for the main-site
        # contact email; keep the stored row in sync so it is shown
        # consistently on every page (footer, contact page, etc.).
        env_email = os.environ.get('CONTACT_EMAIL', '').strip()
        if env_email and obj.email != env_email:
            obj.email = env_email
            obj.save(update_fields=['email'])
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
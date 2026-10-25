from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Custom user model using email as username."""
    email = models.EmailField(_('Email Address'), unique=True)
    phone = models.CharField(
        _('Phone Number'),
        max_length=20,
        blank=False,
        help_text=_(
            'WhatsApp number used for password reset links. Include the '
            'country code, e.g. +234 810 426 0003.'
        ),
    )
    date_of_birth = models.DateField(_('Date of Birth'), null=True, blank=True)
    is_verified = models.BooleanField(_('Verified'), default=False)
    email_verified_at = models.DateTimeField(_('Email Verified At'), null=True, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return first_name + last_name."""
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name or self.username

    def get_short_name(self):
        return self.first_name or self.username

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_countries.fields import CountryField


class CustomUser(AbstractUser):
    """Custom user model using email as username."""
    email = models.EmailField(_('Email Address'), unique=True)
    phone = models.CharField(_('Phone Number'), max_length=20, blank=True)
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


class Address(models.Model):
    """User address book."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name=_('User')
    )
    label = models.CharField(_('Label'), max_length=50, help_text=_('e.g., Home, Work'))
    first_name = models.CharField(_('First Name'), max_length=100)
    last_name = models.CharField(_('Last Name'), max_length=100)
    phone = models.CharField(_('Phone'), max_length=20)
    address_line_1 = models.CharField(_('Address Line 1'), max_length=255)
    address_line_2 = models.CharField(_('Address Line 2'), max_length=255, blank=True)
    city = models.CharField(_('City'), max_length=100)
    state = models.CharField(_('State'), max_length=100)
    postal_code = models.CharField(_('Postal Code'), max_length=20, blank=True)
    country = CountryField(default='NG')
    is_default = models.BooleanField(_('Default'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Address')
        verbose_name_plural = _('Addresses')
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.label} - {self.first_name} {self.last_name}'

    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def get_full_address(self):
        """Return formatted address."""
        lines = [self.address_line_1]
        if self.address_line_2:
            lines.append(self.address_line_2)
        lines.append(f'{self.city}, {self.state}')
        if self.postal_code:
            lines.append(self.postal_code)
        lines.append(str(self.country))
        return '\n'.join(lines)
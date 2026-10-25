import re

from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, UserChangeForm, AuthenticationForm,
    PasswordChangeForm, SetPasswordForm, PasswordResetForm,
)
from django.utils.translation import gettext_lazy as _

from .models import CustomUser


def _validated_phone(value):
    """Require a dialable phone number (country code, 10-15 digits)."""
    phone = (value or '').strip()
    digits = re.sub(r'\D', '', phone)
    if not 10 <= len(digits) <= 15:
        raise forms.ValidationError(_(
            'Enter a valid phone number with its country code, '
            'e.g. +234 810 426 0003.'
        ))
    return phone


class StyledFieldsMixin:
    """Apply the site's form-control style to every field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            if 'form-control' not in existing:
                field.widget.attrs['class'] = f'{existing} form-control'.strip()


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form."""
    email = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('your@email.com'),
            'autocomplete': 'email',
            'required': True,
        })
    )
    first_name = forms.CharField(
        label=_('First Name'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('First Name'),
            'autocomplete': 'given-name',
        })
    )
    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Last Name'),
            'autocomplete': 'family-name',
        })
    )
    phone = forms.CharField(
        label=_('Phone Number'),
        max_length=20,
        required=True,
        help_text=_(
            'Use the WhatsApp number linked to this account. Password reset '
            'links are sent to it on WhatsApp.'
        ),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('+234 8XX XXX XXXX'),
            'autocomplete': 'tel',
            'required': True,
        })
    )
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Create Password'),
            'autocomplete': 'new-password',
        })
    )
    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm Password'),
            'autocomplete': 'new-password',
        })
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(_('A user with this email already exists.'))
        return email

    def clean_phone(self):
        return _validated_phone(self.cleaned_data.get('phone'))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.username = self.cleaned_data['email'].lower()
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Custom user profile update form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('password', None)

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'phone', 'date_of_birth')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_phone(self):
        return _validated_phone(self.cleaned_data.get('phone'))


class CustomAuthenticationForm(StyledFieldsMixin, AuthenticationForm):
    """Custom login form using email."""
    username = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('your@email.com'),
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Password'),
            'autocomplete': 'current-password',
        })
    )


class CustomPasswordChangeForm(StyledFieldsMixin, PasswordChangeForm):
    """Password change with site styling."""


class CustomSetPasswordForm(StyledFieldsMixin, SetPasswordForm):
    """Password reset confirmation with site styling."""


class CustomPasswordResetForm(StyledFieldsMixin, PasswordResetForm):
    """Password reset form with site styling."""
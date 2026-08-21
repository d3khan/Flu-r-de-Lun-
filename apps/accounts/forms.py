from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, UserChangeForm, AuthenticationForm,
    PasswordChangeForm, SetPasswordForm,
)
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, Address


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
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('+234 8XX XXX XXXX'),
            'autocomplete': 'tel',
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

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.username = self.cleaned_data['email'].lower()
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


class AddressForm(forms.ModelForm):
    """Address form."""
    class Meta:
        model = Address
        fields = [
            'label', 'first_name', 'last_name', 'phone',
            'address_line_1', 'address_line_2', 'city', 'state',
            'postal_code', 'country', 'is_default'
        ]
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Home')}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Street address')}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Apartment, suite, etc.')}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'label': _('Address Label'),
            'address_line_1': _('Address Line 1'),
            'address_line_2': _('Address Line 2'),
            'postal_code': _('Postal Code'),
        }


class CustomPasswordChangeForm(StyledFieldsMixin, PasswordChangeForm):
    """Password change with site styling."""


class CustomSetPasswordForm(StyledFieldsMixin, SetPasswordForm):
    """Password reset confirmation with site styling."""
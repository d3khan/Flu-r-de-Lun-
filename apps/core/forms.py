from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    """Contact form with custom styling."""
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Your Name'),
                'aria-label': _('Your Name'),
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Your Email'),
                'aria-label': _('Your Email'),
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Phone Number (optional)'),
                'aria-label': _('Phone Number'),
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Subject'),
                'aria-label': _('Subject'),
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Your Message'),
                'aria-label': _('Your Message'),
            }),
        }
        labels = {
            'name': _('Name'),
            'email': _('Email'),
            'phone': _('Phone'),
            'subject': _('Subject'),
            'message': _('Message'),
        }
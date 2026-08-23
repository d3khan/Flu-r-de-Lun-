"""
Forms for inventory management.
"""
import os
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.products.models import Product, Category, ProductImage


class StyledFieldsMixin:
    """Apply the site's form-control style to every field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            if 'form-control' not in existing:
                field.widget.attrs['class'] = f'{existing} form-control'.strip()


class ProductForm(StyledFieldsMixin, forms.ModelForm):
    """Form for creating/editing products."""

    # Additional field for primary image upload
    primary_image = forms.ImageField(
        label=_('Primary Image'),
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        help_text=_('Main product image (will be marked as primary)')
    )

    # Additional fields for multiple images (handled in view via request.FILES.getlist)
    additional_images = forms.FileField(
        label=_('Additional Images'),
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        help_text=_('Upload additional images (select multiple files)')
    )

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'category', 'description',
            'price', 'compare_at_price',
            'stock_quantity', 'low_stock_threshold', 'weight',
            'sku', 'is_active', 'is_featured', 'is_new_arrival', 'is_bestseller',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Product Name')}),
            'slug': forms.TextInput(attrs={'placeholder': _('auto-generated from name')}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': _('Product description...')}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': _('0.00')}),
            'compare_at_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': _('0.00')}),
            'stock_quantity': forms.NumberInput(attrs={'min': '0', 'placeholder': _('0')}),
            'low_stock_threshold': forms.NumberInput(attrs={'min': '1', 'placeholder': _('5')}),
            'weight': forms.NumberInput(attrs={'step': '0.001', 'min': '0', 'placeholder': _('0.000')}),
            'sku': forms.TextInput(attrs={'placeholder': _('Auto-generated if empty')}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_new_arrival': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_bestseller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'compare_at_price': _('Compare At Price (Sale)'),
            'low_stock_threshold': _('Low Stock Threshold'),
            'stock_quantity': _('Stock Quantity'),
        }
        help_texts = {
            'compare_at_price': _('Original price for sale display. Leave empty if not on sale.'),
            'low_stock_threshold': _('Alert when stock falls below this quantity.'),
            'sku': _('Leave empty to auto-generate from product name.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make slug optional since it's auto-generated
        self.fields['slug'].required = False
        # Order categories by name
        self.fields['category'].queryset = Category.objects.filter(is_active=True).order_by('name')
        self.fields['category'].empty_label = _('Select a category (optional)')

    def clean_primary_image(self):
        """Validate primary image file."""
        image = self.cleaned_data.get('primary_image')
        if image:
            # Validate file size (max 10MB)
            if image.size > 10 * 1024 * 1024:
                raise ValidationError(_('Image file size must be under 10MB.'))
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if image.content_type not in allowed_types:
                raise ValidationError(_('Unsupported image format. Use JPEG, PNG, WebP, or GIF.'))
        return image

    def clean_additional_images(self):
        """Validate additional images."""
        # Note: This field handles multiple files via widget, but Django only gives us one
        # We'll handle multiple files in the view
        return None

    def save(self, commit=True):
        product = super().save(commit=False)
        if commit:
            product.save()
            # Handle primary image upload
            primary_image = self.cleaned_data.get('primary_image')
            if primary_image:
                # Remove existing primary image
                ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)
                # Create new primary image
                ProductImage.objects.create(
                    product=product,
                    image=primary_image,
                    is_primary=True,
                    sort_order=0,
                    alt_text=product.name
                )
        return product


class ProductStockForm(StyledFieldsMixin, forms.ModelForm):
    """Quick form for updating stock quantity only."""

    class Meta:
        model = Product
        fields = ['stock_quantity', 'low_stock_threshold']
        widgets = {
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '0',
                'placeholder': _('Stock Quantity'),
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg',
                'min': '1',
                'placeholder': _('Low Stock Threshold'),
            }),
        }
        labels = {
            'stock_quantity': _('Stock Quantity'),
            'low_stock_threshold': _('Low Stock Alert At'),
        }


class CategoryForm(StyledFieldsMixin, forms.ModelForm):
    """Form for managing categories."""

    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'image', 'is_active', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Category Name')}),
            'slug': forms.TextInput(attrs={'placeholder': _('auto-generated from name')}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': _('Category description...')}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'min': '0', 'placeholder': _('0')}),
        }
        help_texts = {
            'sort_order': _('Lower numbers appear first.'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False

    def clean_image(self):
        """Validate category image."""
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 5 * 1024 * 1024:
                raise ValidationError(_('Image file size must be under 5MB.'))
            allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if image.content_type not in allowed_types:
                raise ValidationError(_('Unsupported image format. Use JPEG, PNG, WebP, or GIF.'))
        return image


class ProductImageForm(StyledFieldsMixin, forms.ModelForm):
    """Form for managing product images."""

    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_primary', 'sort_order']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'alt_text': forms.TextInput(attrs={'placeholder': _('Alt text for accessibility')}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'min': '0', 'placeholder': _('0')}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 10 * 1024 * 1024:
                raise ValidationError(_('Image file size must be under 10MB.'))
            allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            if image.content_type not in allowed_types:
                raise ValidationError(_('Unsupported image format. Use JPEG, PNG, WebP, or GIF.'))
        return image
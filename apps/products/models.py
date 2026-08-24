from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Product category."""
    name = models.CharField(_('Name'), max_length=100)
    slug = models.SlugField(_('Slug'), unique=True)
    description = models.TextField(_('Description'), blank=True)
    image = models.ImageField(_('Image'), upload_to='categories/', blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    sort_order = models.PositiveIntegerField(_('Sort Order'), default=0)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:category', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Product model with inventory tracking."""
    name = models.CharField(_('Name'), max_length=200)
    slug = models.SlugField(_('Slug'), unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name=_('Category')
    )
    description = models.TextField(_('Description'))
    price = models.DecimalField(_('Price'), max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(
        _('Compare At Price'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Original price for sale display')
    )
    stock_quantity = models.PositiveIntegerField(_('Stock Quantity'), default=0)
    low_stock_threshold = models.PositiveIntegerField(_('Low Stock Threshold'), default=5)
    is_active = models.BooleanField(_('Active'), default=True)
    is_featured = models.BooleanField(_('Featured'), default=False)
    is_new_arrival = models.BooleanField(_('New Arrival'), default=False)
    is_bestseller = models.BooleanField(_('Best Seller'), default=False)
    sku = models.CharField(_('SKU'), max_length=50, unique=True, blank=True)
    weight = models.DecimalField(_('Weight (kg)'), max_digits=6, decimal_places=3, default=0)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['is_active', 'is_new_arrival']),
            models.Index(fields=['is_active', 'is_bestseller']),
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            self.sku = f'FDL-{self.id or "NEW"}-{slugify(self.name)[:10].upper()}'
        super().save(*args, **kwargs)

    @property
    def in_stock(self):
        """Check if product is in stock."""
        return self.stock_quantity > 0

    @property
    def stock_status(self):
        """Return human-readable stock status."""
        if self.stock_quantity == 0:
            return 'out_of_stock'
        elif self.stock_quantity <= self.low_stock_threshold:
            return 'low_stock'
        return 'in_stock'

    @property
    def stock_status_display(self):
        """Return display text for stock status."""
        if self.stock_quantity == 0:
            return _('Out of Stock')
        elif self.stock_quantity <= self.low_stock_threshold:
            return _('Low Stock')
        return _('In Stock')

    @property
    def primary_image(self):
        """Get primary product image."""
        return self.images.filter(is_primary=True).first() or self.images.first()

    @property
    def discount_percentage(self):
        """Calculate discount percentage if on sale."""
        if self.compare_at_price and self.compare_at_price > self.price:
            return int(((self.compare_at_price - self.price) / self.compare_at_price) * 100)
        return 0

    @property
    def is_on_sale(self):
        return self.discount_percentage > 0


class ProductImage(models.Model):
    """Product images stored on ImgBB."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Product')
    )
    image = models.ImageField(_('Image'), upload_to='products/')
    alt_text = models.CharField(_('Alt Text'), max_length=200, blank=True)
    is_primary = models.BooleanField(_('Primary'), default=False)
    sort_order = models.PositiveIntegerField(_('Sort Order'), default=0)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    # ImgBB metadata
    imgbb_delete_url = models.URLField(_('ImgBB Delete URL'), blank=True)
    imgbb_id = models.CharField(_('ImgBB Image ID'), max_length=50, blank=True)
    imgbb_display_url = models.URLField(_('ImgBB Display URL'), blank=True)
    imgbb_thumb_url = models.URLField(_('ImgBB Thumbnail URL'), blank=True)
    imgbb_medium_url = models.URLField(_('ImgBB Medium URL'), blank=True)

    class Meta:
        verbose_name = _('Product Image')
        verbose_name_plural = _('Product Images')
        ordering = ['sort_order', 'created_at']

    def __str__(self):
        return f'{self.product.name} - Image {self.sort_order}'

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Note: ImgBB deletion is handled explicitly in views with user consent
        super().delete(*args, **kwargs)
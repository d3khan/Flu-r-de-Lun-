from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'alt_text', 'is_primary', 'sort_order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'is_active', 'image_preview')
    list_editable = ('sort_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    list_filter = ('is_active',)

    @admin.display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;" />', obj.image.url)
        return '—'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'price', 'compare_at_price',
        'stock_quantity', 'stock_badge', 'is_active',
        'is_featured', 'is_new_arrival', 'is_bestseller',
    )
    list_filter = ('is_active', 'is_featured', 'is_new_arrival', 'is_bestseller', 'category')
    list_editable = ('price', 'stock_quantity', 'is_active', 'is_featured', 'is_new_arrival', 'is_bestseller')
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'category', 'description', 'sku')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'low_stock_threshold', 'weight')
        }),
        ('Flags & Visibility', {
            'fields': ('is_active', 'is_featured', 'is_new_arrival', 'is_bestseller')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Stock')
    def stock_badge(self, obj):
        color = {'in_stock': '#2d7d46', 'low_stock': '#b8860b', 'out_of_stock': '#c0392b'}[obj.stock_status]
        return format_html('<b style="color:{};">{} ({})</b>', color, obj.stock_status_display, obj.stock_quantity)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and obj.pk:
            # SKU references id; save again to fill it in on first create
            if 'NEW' in obj.sku:
                obj.sku = ''
                obj.save()

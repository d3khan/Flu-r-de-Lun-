from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'product_name', 'product_sku', 'price', 'quantity')
    readonly_fields = ('product_name', 'product_sku')


class StatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('status', 'note', 'created_by', 'created_at')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'full_name', 'email', 'total',
        'payment_method', 'payment_badge', 'status_badge', 'created_at',
    )
    list_filter = ('status', 'payment_method', 'payment_verified', 'created_at')
    search_fields = ('order_number', 'email', 'first_name', 'last_name', 'phone')
    readonly_fields = (
        'order_number', 'user', 'session_key', 'subtotal', 'total',
        'payment_verified_at', 'confirmed_at', 'shipped_at', 'delivered_at',
        'cancelled_at', 'created_at', 'updated_at', 'stock_deducted',
    )
    inlines = [OrderItemInline, StatusHistoryInline]
    date_hierarchy = 'created_at'
    actions = ['mark_confirmed', 'mark_shipped']

    fieldsets = (
        ('Order', {'fields': ('order_number', 'user', 'session_key', 'status')}),
        ('Customer', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Payment', {
            'fields': ('payment_method', 'payment_reference',
                       'payment_verified', 'payment_verified_at'),
        }),
        ('Totals', {'fields': ('subtotal', 'discount', 'tax', 'total', 'stock_deducted')}),
        ('Notes', {'fields': ('notes',), 'classes': ('collapse',)}),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'shipped_at',
                       'delivered_at', 'cancelled_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Deduct on first entry to Confirmed/Processing/Delivered; the order
        # itself guards against deducting more than once.
        obj.apply_status_stock()

    @admin.display(description='Payment')
    def payment_badge(self, obj):
        if obj.payment_verified:
            return format_html('<b style="color:#2d7d46;">Paid ✓</b>')
        return format_html('<span style="color:#b8860b;">Unpaid</span>')

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'pending': '#b8860b', 'confirmed': '#2c7be5', 'processing': '#2c7be5',
            'shipped': '#2d7d46', 'delivered': '#2d7d46',
            'cancelled': '#c0392b', 'refunded': '#c0392b',
        }
        return format_html('<b style="color:{};">{}</b>',
                           colors.get(obj.status, '#4d4237'), obj.get_status_display())

    @admin.action(description='Mark selected orders as confirmed')
    def mark_confirmed(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for order in queryset.filter(status='pending'):
            order.status = 'confirmed'
            if not order.confirmed_at:
                order.confirmed_at = timezone.now()
            order.save()
            order.apply_status_stock()
            OrderStatusHistory.objects.create(order=order, status='confirmed', note='Confirmed via admin')
            updated += 1
        self.message_user(request, f'{updated} order(s) confirmed.')

    @admin.action(description='Mark selected orders as shipped')
    def mark_shipped(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for order in queryset.filter(status__in=['confirmed', 'processing']):
            order.status = 'shipped'
            if not order.shipped_at:
                order.shipped_at = timezone.now()
            order.save()
            order.apply_status_stock()
            OrderStatusHistory.objects.create(order=order, status='shipped', note='Shipped via admin')
            updated += 1
        self.message_user(request, f'{updated} order(s) marked shipped.')

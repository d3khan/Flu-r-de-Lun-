from django.contrib import admin

from .models import ManualPaymentInfo, PaymentTransaction, PaymentLink


@admin.register(ManualPaymentInfo)
class ManualPaymentInfoAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_name', 'account_number', 'whatsapp_number', 'is_active')
    fields = ('bank_name', 'account_name', 'account_number',
              'whatsapp_number', 'whatsapp_message_template', 'instructions', 'is_active')

    def save_model(self, request, obj, form, change):
        # Only one active set of bank details at a time
        if obj.is_active:
            ManualPaymentInfo.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'order_link', 'gateway', 'amount', 'currency',
                    'status_colored', 'customer_email', 'created_at')
    list_filter = ('status', 'gateway', 'created_at')
    search_fields = ('reference', 'gateway_reference', 'customer_email', 'order__order_number')
    readonly_fields = ('gateway_response',)
    date_hierarchy = 'created_at'

    @admin.display(description='Order')
    def order_link(self, obj):
        return obj.order.order_number

    @admin.display(description='Status')
    def status_colored(self, obj):
        colors = {'success': '#2d7d46', 'failed': '#c0392b', 'cancelled': '#c0392b'}
        color = colors.get(obj.status, '#b8860b')
        return f'{obj.status.upper()}'


@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    list_display = ('order', 'gateway', 'url', 'is_used', 'is_expired_display', 'expires_at', 'created_at')
    list_filter = ('gateway', 'is_used')
    search_fields = ('reference', 'order__order_number')

    @admin.display(description='Expired?', boolean=True)
    def is_expired_display(self, obj):
        return obj.is_expired

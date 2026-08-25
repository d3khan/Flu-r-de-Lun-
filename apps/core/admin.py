from django.contrib import admin

from .models import SiteSettings, ContactMessage


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'email', 'whatsapp_number', 'business_hours')

    fieldsets = (
        ('Brand', {
            'fields': ('site_name', 'site_tagline', 'logo', 'favicon'),
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'address'),
        }),
        ('Customer Support', {
            'fields': ('business_hours', 'response_time'),
            'description': 'Shown on the contact page, footer and manual payment step. Leave blank to hide.',
        }),
        ('WhatsApp', {
            'fields': ('whatsapp_number', 'whatsapp_message'),
            'description': 'Number format: 2348012345678 (no + or spaces). Powers WhatsApp buttons site-wide.',
        }),
        ('SEO', {
            'fields': ('meta_description', 'meta_keywords'),
            'classes': ('collapse',),
        }),
        ('Analytics', {
            'fields': ('google_analytics_id', 'facebook_pixel_id'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        # Singleton: only allow editing the existing row
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
    list_editable = ('is_read',)

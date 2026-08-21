from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Address


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    ordering = ('-created_at',)
    list_display = ('email', 'username', 'first_name', 'last_name', 'phone',
                    'is_staff', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone')
    list_filter = ('is_staff', 'is_superuser', 'is_verified', 'date_joined')
    inlines = [AddressInline]

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'date_of_birth')}),
        ('Permissions', {'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('label', 'full_name_short', 'city', 'state', 'phone', 'is_default', 'user')
    list_filter = ('is_default', 'state')
    search_fields = ('first_name', 'last_name', 'city', 'phone', 'user__email')

    @admin.display(description='Name')
    def full_name_short(self, obj):
        return f'{obj.first_name} {obj.last_name}'

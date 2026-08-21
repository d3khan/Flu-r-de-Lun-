from django.contrib import admin

from .models import Wishlist


class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items', 'updated_at')
    search_fields = ('user__email',)


admin.site.register(Wishlist, WishlistAdmin)

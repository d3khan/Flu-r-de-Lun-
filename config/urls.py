"""
URL configuration for Fluér de Luné project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Literal path (NOT static_url()): resolving through the manifest-backed
    # storage at import time crashes every manage.py command in a fresh
    # build container before collectstatic has produced the manifest.
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.svg', permanent=True)),

    # Core pages (home, about, contact)
    path('', include('apps.core.urls', namespace='core')),

    # Products catalog
    path('shop/', include('apps.products.urls', namespace='products')),

    # Shopping cart
    path('cart/', include('apps.cart.urls', namespace='cart')),

    # Wishlist
    path('wishlist/', include('apps.wishlist.urls', namespace='wishlist')),

    # User accounts
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),

    # Orders
    path('orders/', include('apps.orders.urls', namespace='orders')),

    # Payments
    path('payments/', include('apps.payments.urls', namespace='payments')),

    # Checkout
    path('checkout/', include('apps.checkout.urls', namespace='checkout')),

    # Inventory Management (Basic Auth protected)
    path('inventory/', include('apps.inventory.urls', namespace='inventory')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error pages
handler404 = 'apps.core.views.handler404'
handler500 = 'apps.core.views.handler500'


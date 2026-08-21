"""
URL configuration for Fluér de Luné project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from django.templatetags.static import static as static_url

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url=static_url('images/favicon.svg'), permanent=True)),

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
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error pages
handler404 = 'apps.core.views.handler404'
handler500 = 'apps.core.views.handler500'


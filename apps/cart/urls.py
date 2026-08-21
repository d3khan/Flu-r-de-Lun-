from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.CartDetailView.as_view(), name='detail'),
    path('add/<int:product_id>/', views.cart_add, name='add'),
    path('update/<int:item_id>/', views.cart_update, name='update'),
    path('remove/<int:item_id>/', views.cart_remove, name='remove'),
    path('clear/', views.cart_clear, name='clear'),
    
    # HTMX partials
    path('drawer/', views.cart_drawer, name='drawer'),
    path('count/', views.cart_count, name='count'),
]
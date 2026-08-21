from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='list'),
    path('category/<slug:slug>/', views.category_detail, name='category'),
    path('<slug:slug>/', views.ProductDetailView.as_view(), name='detail'),
    
    # HTMX partials
    path('partials/card/<int:product_id>/', views.product_card, name='product_card'),
    path('partials/quick-view/<int:product_id>/', views.product_quick_view, name='quick_view'),
    path('api/check-stock/<int:product_id>/', views.check_stock, name='check_stock'),
]
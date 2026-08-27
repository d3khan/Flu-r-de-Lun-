"""
URL configuration for inventory app.
"""
from django.urls import path

from . import views

app_name = 'inventory'

urlpatterns = [
    # Authentication
    path('login/', views.inventory_login, name='login'),
    path('logout/', views.inventory_logout, name='logout'),

    # Dashboard
    path('', views.inventory_dashboard, name='dashboard'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/stock/', views.product_stock_update, name='product_stock_update'),

    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Orders
    path('orders/', views.inventory_order_list, name='order_list'),
    path('orders/<int:pk>/', views.inventory_order_detail, name='order_detail'),
    path('orders/<int:pk>/verify/', views.inventory_order_verify, name='order_verify'),
    path('orders/<int:pk>/status/', views.inventory_order_status, name='order_status'),
]
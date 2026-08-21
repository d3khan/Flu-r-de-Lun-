from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.OrderHistoryView.as_view(), name='history'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='detail'),
    path('guest/', views.guest_order_lookup, name='guest_lookup'),
    path('guest/<str:order_number>/', views.guest_order_detail, name='guest_detail'),
    path('<int:pk>/cancel/', views.order_cancel, name='cancel'),
    path('<int:pk>/reorder/', views.order_reorder, name='reorder'),
    
    # Admin
    path('admin/', views.order_list_admin, name='admin_list'),
    path('admin/<int:pk>/', views.order_detail_admin, name='admin_detail'),
]
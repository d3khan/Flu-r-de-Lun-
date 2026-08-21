from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('callback/<int:order_id>/', views.payment_callback, name='callback'),
    path('webhook/', views.payment_webhook, name='webhook'),
    path('initiate/<int:order_id>/', views.initiate_gateway_payment, name='initiate'),
    path('manual-info/', views.manual_payment_info, name='manual_info'),
    path('method-select/<int:order_id>/', views.payment_method_select, name='method_select'),
]
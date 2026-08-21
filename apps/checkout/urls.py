from django.urls import path
from . import views

app_name = 'checkout'

urlpatterns = [
    path('shipping/', views.checkout_step1_shipping, name='step1'),
    path('payment-method/', views.checkout_step2_payment, name='step2'),
    path('payment/', views.checkout_step3_payment, name='step3'),
    path('gateway/<int:order_id>/', views.gateway_payment, name='gateway_payment'),
    path('manual/<int:order_id>/', views.manual_payment, name='manual_payment'),
    path('confirmation/<int:order_id>/', views.order_confirmation, name='confirmation'),
    
    # AJAX endpoints
    path('validate-stock/', views.checkout_validate_stock, name='validate_stock'),
    path('save-address/', views.checkout_save_address, name='save_address'),
]
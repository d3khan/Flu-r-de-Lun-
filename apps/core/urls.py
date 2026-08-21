from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('shipping/', views.ShippingView.as_view(), name='shipping'),
    path('returns/', views.ReturnsView.as_view(), name='returns'),
    path('offline/', views.OfflineView.as_view(), name='offline'),
    
    # HTMX partials
    path('partials/whatsapp-button/', views.whatsapp_button, name='whatsapp_button'),
]
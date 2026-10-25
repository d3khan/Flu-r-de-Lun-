from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('password/change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    
    # Password reset - self-service is disabled (no email/SMS provider).
    # Staff generate a link in inventory and send it over WhatsApp.
    path('password/reset/', views.password_reset_under_development, name='password_reset'),
    # TEMPORARY test mode: opens the reset link without delivering it.
    path('password/reset/instant/', views.password_reset_instant, name='password_reset_instant'),
    path('password/reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
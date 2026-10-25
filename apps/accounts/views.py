from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordResetView,
    PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.http import Http404

from .models import CustomUser
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm,
    CustomAuthenticationForm,
    CustomPasswordChangeForm, CustomSetPasswordForm,
    CustomPasswordResetForm,
)


class RegisterView(CreateView):
    """User registration."""
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        # Keep registered users remembered for 30 days even though sessions
        # otherwise expire when the browser closes (guest data lifecycle).
        self.request.session.set_expiry(60 * 60 * 24 * 30)
        messages.success(self.request, _('Welcome to Fluér de Luné! Your account has been created.'))
        return response

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return super().dispatch(request, *args, **kwargs)


class CustomLoginView(LoginView):
    """Custom login view."""
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        # 30-day remember-me: overrides the browser-close expiry applied to
        # anonymous sessions (guest carts/wishlists still die on exit).
        self.request.session.set_expiry(60 * 60 * 24 * 30)
        messages.success(self.request, _('Welcome back!'))
        return response


class CustomLogoutView(LogoutView):
    """Custom logout view."""
    next_page = 'core:home'

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            messages.success(request, _('You have been logged out.'))
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordChangeView(PasswordChangeView):
    """Custom password change."""
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        messages.success(self.request, _('Your password has been changed.'))
        return response


class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


@login_required
def profile(request):
    """User profile dashboard."""
    from apps.orders.models import Order
    
    recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    context = {
        'recent_orders': recent_orders,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    """Edit user profile."""
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile updated successfully.'))
            return redirect('accounts:profile')
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, 'accounts/profile_edit.html', {'form': form})


def password_reset_under_development(request):
    """Password reset landing page: staff-assisted, plus a test-only shortcut."""
    # site_settings comes from the context processor; passing an explicit
    # value here (e.g. None) would override it and blank the contact
    # email in this template and the shared footer.
    return render(request, 'accounts/password_reset_under_development.html', {
        'password_reset_test_mode': getattr(
            settings, 'PASSWORD_RESET_TEST_MODE', False
        ),
    })


@require_POST
def password_reset_instant(request):
    """TEMPORARY test mode: open a reset link without delivering it.

    While PASSWORD_RESET_TEST_MODE is on, anyone who knows an account email
    can reset that account, so it is off by default in production. Delete the
    marked block in password_reset_under_development.html to hide the entry
    point, and unset PASSWORD_RESET_TEST_MODE to close this endpoint.
    """
    if not getattr(settings, 'PASSWORD_RESET_TEST_MODE', False):
        raise Http404

    email = (request.POST.get('email') or '').strip()
    account = get_user_model().objects.filter(
        email__iexact=email, is_active=True
    ).first()

    if account is None:
        messages.error(request, _('No active account uses that email address.'))
        return redirect('accounts:password_reset')

    # Exercise the real reset-email path (console backend locally) before
    # opening the same signed link in the browser.
    reset_form = CustomPasswordResetForm({'email': account.email})
    if reset_form.is_valid():
        reset_form.save(
            request=request,
            use_https=request.is_secure(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
        )

    uidb64 = urlsafe_base64_encode(force_bytes(account.pk))
    token = default_token_generator.make_token(account)
    return redirect(
        'accounts:password_reset_confirm',
        uidb64=uidb64,
        token=token,
    )

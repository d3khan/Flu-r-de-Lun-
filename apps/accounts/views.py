from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordResetView,
    PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, ListView, DetailView, DeleteView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse

from .models import CustomUser, Address
from .forms import (
    CustomUserCreationForm, CustomUserChangeForm,
    CustomAuthenticationForm, AddressForm,
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


class AddressListView(LoginRequiredMixin, ListView):
    model = Address
    template_name = 'accounts/address_list.html'
    context_object_name = 'addresses'

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressCreateView(LoginRequiredMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = 'accounts/address_form.html'
    success_url = reverse_lazy('accounts:address_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        # If this is the first address, make it default
        if not Address.objects.filter(user=self.request.user).exists():
            form.instance.is_default = True
        messages.success(self.request, _('Address added successfully.'))
        return super().form_valid(form)


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = 'accounts/address_form.html'
    success_url = reverse_lazy('accounts:address_list')

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, _('Address updated successfully.'))
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    model = Address
    template_name = 'accounts/address_confirm_delete.html'
    success_url = reverse_lazy('accounts:address_list')

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Address deleted.'))
        return super().delete(request, *args, **kwargs)


@login_required
def address_set_default(request, pk):
    """Set address as default via HTMX."""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    address.is_default = True
    address.save()
    
    if request.htmx:
        return JsonResponse({'success': True})
    return redirect('accounts:address_list')


def password_reset_under_development(request):
    """Temporary page for password reset under development."""
    # site_settings comes from the context processor; passing an explicit
    # value here (e.g. None) would override it and blank the contact
    # email in this template and the shared footer.
    return render(request, 'accounts/password_reset_under_development.html')
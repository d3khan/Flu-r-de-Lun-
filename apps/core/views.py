from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import TemplateView, FormView
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse

from .models import SiteSettings, ContactMessage
from .forms import ContactForm


class HomeView(TemplateView):
    """Home page with hero, featured products, and brand story."""
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.products.models import Product, Category
        
        # Featured products
        context['featured_products'] = Product.objects.filter(
            is_active=True, is_featured=True
        ).select_related('category').prefetch_related('images')[:8]
        
        # New arrivals
        context['new_arrivals'] = Product.objects.filter(
            is_active=True
        ).select_related('category').prefetch_related('images').order_by('-created_at')[:8]
        
        # Categories
        context['categories'] = Category.objects.filter(is_active=True)[:6]
        
        return context


class AboutView(TemplateView):
    """About page with brand story."""
    template_name = 'core/about.html'


class ContactView(FormView):
    """Contact page with form."""
    template_name = 'core/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('core:contact')
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Thank you for your message! We'll get back to you soon."))
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['site_settings'] = SiteSettings.get_settings()
        return context


class PrivacyView(TemplateView):
    template_name = 'core/privacy.html'


class TermsView(TemplateView):
    template_name = 'core/terms.html'


class ShippingView(TemplateView):
    template_name = 'core/shipping.html'


class ReturnsView(TemplateView):
    template_name = 'core/returns.html'


class OfflineView(TemplateView):
    """Offline fallback page (service worker)."""
    template_name = 'core/offline.html'


def handler404(request, exception):
    """Custom 404 error page."""
    return render(request, 'core/404.html', status=404)


def handler500(request):
    """Custom 500 error page."""
    return render(request, 'core/500.html', status=500)


# HTMX partial views

def whatsapp_button(request):
    """Return WhatsApp button partial for HTMX."""
    site_settings = SiteSettings.get_settings()
    product_name = request.GET.get('product', '')
    
    if site_settings.whatsapp_number:
        message = site_settings.whatsapp_message.format(product_name=product_name)
        whatsapp_url = f'https://wa.me/{site_settings.whatsapp_number}?text={message}'
    else:
        whatsapp_url = '#'
    
    return render(request, 'core/partials/_whatsapp_button.html', {
        'whatsapp_url': whatsapp_url,
        'site_settings': site_settings,
    })
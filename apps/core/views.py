from django.shortcuts import render
from django.views.generic import TemplateView
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from urllib.parse import quote

from .models import SiteSettings
from apps.wishlist.utils import annotate_in_wishlist


# Icon markup for each contact channel. Kept here so the contact page
# template stays generic: adding a channel means one new SiteSettings field
# plus one entry here and one entry in ContactView.contact_methods().
CONTACT_ICONS = {
    'email': mark_safe(
        '<rect x="3" y="5" width="18" height="14" rx="2"/>'
        '<path d="m3 7 9 6 9-6"/>'
    ),
    'phone': mark_safe(
        '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 '
        '19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 '
        '0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 '
        '6 6l1.2-1.2a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.7 2z"/>'
    ),
    'clock': mark_safe(
        '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'
    ),
    'whatsapp': mark_safe(
        '<path d="M12 2a10 10 0 0 0-8.6 15L2 22l5.2-1.4A10 10 0 1 0 12 2z'
        'm4.6 12.1c-.2.6-1.2 1.1-1.7 1.2-.4.1-1 .1-1.6-.1-.4-.2-.9-.3-1.5-'
        '.6-2.7-1.1-4.4-3.7-4.5-3.9-.1-.2-1.1-1.4-1.1-2.7s.7-1.9.9-2.2c.2-'
        '.2.5-.3.7-.3h.5c.2 0 .4 0 .6.4.2.5.7 1.7.8 1.9v.5c0 .2-.1.3-.3.5'
        'l-.4.5c-.1.2-.4.3-.1.7a6.7 6.7 0 0 0 3.4 3c.2.1.4.1.5-.1l.8-1c.2-'
        '.2.4-.3.6-.1.2.1 1.4.7 1.7.8s.4.2.5.3c0 .1 0 .6-.2 1.2z"/>'
    ),
    'pin': mark_safe(
        '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 1 1 16 0Z"/>'
        '<circle cx="12" cy="10" r="3"/>'
    ),
    'instagram': mark_safe(
        '<rect x="2.5" y="2.5" width="19" height="19" rx="5"/>'
        '<circle cx="12" cy="12" r="4.25"/>'
        '<circle cx="17.4" cy="6.6" r="1" fill="currentColor" stroke="none"/>'
    ),
    'facebook': mark_safe(
        '<path d="M13.5 21v-7h2.4l.4-3h-2.8V9.1c0-.9.3-1.5 1.6-1.5h1.3V4.9'
        'c-.3 0-1.1-.1-2-.1-2 0-3.4 1.2-3.4 3.5V11H8.5v3H11v7h2.5z"/>'
    ),
    'twitter': mark_safe(
        '<path d="M17.2 3h3l-6.6 7.6L21.5 21h-6.1l-4.8-6.3L5.1 21h-3l7.1-8.1'
        'L2.7 3h6.2l4.3 5.7L17.2 3zm-1.1 16.2h1.7L7.9 4.7H6.1l10 14.5z"/>'
    ),
    'tiktok': mark_safe(
        '<path d="M16.7 3c.4 2.1 1.8 3.5 3.8 3.8v3c-1.5 0-2.8-.4-3.8-1.2v5.9'
        'c0 3.5-2.4 5.8-5.6 5.8-3.1 0-5.6-2.4-5.6-5.5 0-3 2.4-5.5 5.5-5.5.3 0 '
        '.6 0 .9.1v3.1c-.3-.1-.6-.2-.9-.2-1.4 0-2.5 1.1-2.5 2.5s1.1 2.5 2.6 '
        '2.5c1.4 0 2.5-1.1 2.5-2.6V3h3.1z"/>'
    ),
}


class HomeView(TemplateView):
    """Home page with hero, featured products, and brand story."""
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.products.models import Product, Category

        # Featured products (flag-driven)
        context['featured_products'] = annotate_in_wishlist(
            Product.objects.filter(is_active=True, is_featured=True)
            .select_related('category').prefetch_related('images')
            .order_by('-created_at')[:8],
            self.request.user,
        )

        # New arrivals (flag-driven, newest first)
        context['new_arrivals'] = annotate_in_wishlist(
            Product.objects.filter(is_active=True, is_new_arrival=True)
            .select_related('category').prefetch_related('images')
            .order_by('-created_at')[:8],
            self.request.user,
        )

        # Best sellers (flag-driven)
        context['best_sellers'] = annotate_in_wishlist(
            Product.objects.filter(is_active=True, is_bestseller=True)
            .select_related('category').prefetch_related('images')[:8],
            self.request.user,
        )

        # Categories
        context['categories'] = Category.objects.filter(is_active=True)[:6]

        return context


class AboutView(TemplateView):
    """About page with brand story."""
    template_name = 'core/about.html'


class ContactView(TemplateView):
    """Contact page.

    The contact form was removed because no email provider is configured,
    so submissions had nowhere to go. Customers reach us through the contact
    methods listed here instead, which are driven by SiteSettings so a new
    channel (Instagram, X, Telegram, …) only needs one SiteSettings field
    plus one entry in CONTACT_ICONS and contact_methods().
    """
    template_name = 'core/contact.html'

    def contact_methods(self, site_settings):
        """Build the list of contact methods shown on the page."""
        methods = []

        if site_settings.email:
            methods.append({
                'key': 'email',
                'title': _('Email'),
                'href': f'mailto:{site_settings.email}',
                'text': site_settings.email,
                'external': False,
                'icon_html': CONTACT_ICONS['email'],
            })

        if site_settings.phone:
            methods.append({
                'key': 'phone',
                'title': _('Phone'),
                'href': f'tel:{site_settings.phone_href}',
                'text': site_settings.phone,
                'external': False,
                'icon_html': CONTACT_ICONS['phone'],
            })

        if site_settings.business_hours or site_settings.response_time:
            lines = []
            if site_settings.business_hours:
                lines.append(site_settings.business_hours)
            if site_settings.response_time:
                lines.append(site_settings.response_time)
            methods.append({
                'key': 'clock',
                'title': _('Support Hours'),
                'href': None,
                'lines': lines,
                'external': False,
                'icon_html': CONTACT_ICONS['clock'],
            })

        if site_settings.whatsapp_number:
            methods.append({
                'key': 'whatsapp',
                'title': _('WhatsApp'),
                'href': (
                    'https://wa.me/'
                    f'{site_settings.whatsapp_number}?text='
                    f'{quote(str(_("Hello Fluér de Luné!")))}'
                ),
                'text': _('Chat with us instantly'),
                'external': True,
                'icon_html': CONTACT_ICONS['whatsapp'],
            })

        for key, url, title in (
            ('instagram', site_settings.instagram_url, _('Instagram')),
            ('facebook', site_settings.facebook_url, _('Facebook')),
            ('twitter', site_settings.twitter_url, _('Twitter / X')),
            ('tiktok', site_settings.tiktok_url, _('TikTok')),
        ):
            if url:
                methods.append({
                    'key': key,
                    'title': title,
                    'href': url,
                    'text': title,
                    'external': True,
                    'icon_html': CONTACT_ICONS[key],
                })

        return methods

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site_settings = SiteSettings.get_settings()
        context['site_settings'] = site_settings
        context['contact_methods'] = self.contact_methods(site_settings)
        return context


class PrivacyView(TemplateView):
    template_name = 'core/privacy.html'


class TermsView(TemplateView):
    template_name = 'core/terms.html'


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
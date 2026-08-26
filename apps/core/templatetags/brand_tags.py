from django import template
from django.urls import reverse
from urllib.parse import quote

register = template.Library()


@register.filter
def brand_first(value):
    """First word of the site name (dark part of the two-tone wordmark)."""
    if not value:
        return ''
    return str(value).split(' ', 1)[0]


@register.filter
def brand_rest(value):
    """Everything after the first word of the site name (gold accent part)."""
    if not value:
        return ''
    parts = str(value).split(' ', 1)
    return parts[1] if len(parts) > 1 else ''


@register.simple_tag
def image_proxy_url(url, width=None, height=None):
    """
    Generate a proxied image URL for external images (e.g., ImgBB).
    Usage: {% image_proxy_url image.large_url %} or {% image_proxy_url image.thumbnail_url 400 400 %}
    """
    if not url:
        return ''
    
    # Only proxy ImgBB images
    allowed_hosts = ['ibb.co', 'i.ibb.co', 'imgbb.com']
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.netloc not in allowed_hosts:
            return url  # Return original for local/other images
    except Exception:
        return url
    
    proxy_url = reverse('products:image_proxy')
    params = f'url={quote(url)}'
    if width:
        params += f'&w={width}'
    if height:
        params += f'&h={height}'
    return f'{proxy_url}?{params}'

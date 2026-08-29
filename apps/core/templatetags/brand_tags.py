from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe
from urllib.parse import quote

register = template.Library()


@register.filter
def break_long_words(value, max_length=None):
    """
    Insert zero-width spaces in words longer than max_length to allow breaking.
    Usage: {{ product.name|break_long_words }} or {{ product.name|break_long_words:15 }}
    Default max_length from settings.MAX_WORD_LENGTH (default 10).
    """
    if not value:
        return ''
    
    if max_length is None:
        max_length = getattr(settings, 'MAX_WORD_LENGTH', 10)
    else:
        try:
            max_length = int(max_length)
        except (ValueError, TypeError):
            max_length = getattr(settings, 'MAX_WORD_LENGTH', 10)
    
    if max_length <= 0:
        return value
    
    text = str(value)
    result = []
    for word in text.split(' '):
        if len(word) > max_length:
            # Insert zero-width space every max_length characters
            chunks = [word[i:i+max_length] for i in range(0, len(word), max_length)]
            result.append('&#8203;'.join(chunks))
        else:
            result.append(word)
    
    return mark_safe(' '.join(result))


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
    
    # Only proxy ImgBB images (ibb.co and subdomains, plus imgbb.com)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not (parsed.netloc.endswith('ibb.co') or parsed.netloc == 'imgbb.com'):
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

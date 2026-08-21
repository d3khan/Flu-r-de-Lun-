from django import template

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

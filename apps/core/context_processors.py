from .models import SiteSettings


def site_settings(request):
    """Add site settings to all templates."""
    return {
        'site_settings': SiteSettings.get_settings(),
    }
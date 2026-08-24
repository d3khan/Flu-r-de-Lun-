from .models import Category


def nav_categories(request):
    """Add active categories to all templates (header/footer navigation)."""
    return {
        'nav_categories': Category.objects.filter(is_active=True).order_by('sort_order', 'name')[:3],
    }

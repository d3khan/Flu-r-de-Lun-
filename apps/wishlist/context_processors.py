from .models import Wishlist


def wishlist(request):
    """Add wishlist count to all templates."""
    if request.user.is_authenticated:
        wishlist_obj, created = Wishlist.objects.get_or_create(user=request.user)
        count = wishlist_obj.total_items
    else:
        count = 0
    return {
        'wishlist_count': count,
    }
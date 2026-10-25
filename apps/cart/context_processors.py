from .models import Cart


def cart(request):
    """Add cart to all templates."""
    if request.user.is_authenticated:
        cart_obj, created = Cart.objects.get_or_create(user=request.user, session_key='')
    else:
        if not request.session.session_key:
            request.session.create()
        cart_obj, created = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            user__isnull=True
        )
    return {
        'cart': cart_obj,
        'cart_count': cart_obj.total_items,
    }
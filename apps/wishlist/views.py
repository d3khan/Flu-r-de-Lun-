from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .models import Wishlist, WishlistItem
from apps.products.models import Product
from apps.cart.models import Cart


def get_or_create_wishlist(request):
    """Get or create wishlist for authenticated user."""
    if not request.user.is_authenticated:
        return None
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    return wishlist


@login_required
def wishlist_detail(request):
    """Display wishlist contents."""
    wishlist = get_or_create_wishlist(request)
    return render(request, 'wishlist/detail.html', {'wishlist': wishlist})


@require_POST
@login_required
def wishlist_add(request, product_id):
    """Add product to wishlist."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    wishlist = get_or_create_wishlist(request)
    
    item, created = wishlist.add_product(product)
    
    if request.htmx:
        return JsonResponse({
            'success': True,
            'created': created,
            'in_wishlist': True,
            'count': wishlist.total_items,
        })
    
    if created:
        messages.success(request, _('Added to wishlist!'))
    else:
        messages.info(request, _('Already in your wishlist.'))
    return redirect('products:detail', slug=product.slug)


@require_POST
@login_required
def wishlist_remove(request, product_id):
    """Remove product from wishlist."""
    wishlist = get_or_create_wishlist(request)
    wishlist.remove_product(get_object_or_404(Product, id=product_id))
    
    if request.htmx:
        return JsonResponse({
            'success': True,
            'in_wishlist': False,
            'count': wishlist.total_items,
        })
    
    messages.success(request, _('Removed from wishlist.'))
    return redirect('wishlist:detail')


@require_POST
@login_required
def wishlist_toggle(request, product_id):
    """Toggle product in wishlist."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    wishlist = get_or_create_wishlist(request)
    
    if wishlist.has_product(product):
        wishlist.remove_product(product)
        in_wishlist = False
        message = _('Removed from wishlist.')
    else:
        wishlist.add_product(product)
        in_wishlist = True
        message = _('Added to wishlist!')
    
    if request.htmx:
        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'count': wishlist.total_items,
            'message': message,
        })
    
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'products:list'))


@login_required
def wishlist_move_to_cart(request, product_id):
    """Move product from wishlist to cart."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    wishlist = get_or_create_wishlist(request)
    
    from apps.cart.models import Cart
    cart = Cart.objects.get_or_create(user=request.user, session_key='')[0]
    
    wishlist.move_to_cart(product, cart)
    
    if request.htmx:
        response = render(request, 'cart/partials/_drawer.html', {'cart': cart})
        response['HX-Trigger'] = 'cartUpdated'
        return response
    
    messages.success(request, _('Moved to cart!'))
    return redirect('cart:detail')


@login_required
def wishlist_count(request):
    """Return wishlist count for HTMX badge update."""
    wishlist = get_or_create_wishlist(request)
    count = wishlist.total_items
    return JsonResponse({'count': count})
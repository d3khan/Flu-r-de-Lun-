from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .models import Cart, CartItem
from apps.products.models import Product


def get_or_create_cart(request):
    """Get or create cart for current request."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user, session_key='')
        # Merge session cart if exists
        if request.session.session_key:
            session_cart = Cart.objects.filter(
                session_key=request.session.session_key,
                user__isnull=True
            ).first()
            if session_cart and session_cart != cart:
                cart.merge_with(session_cart)
    else:
        if not request.session.session_key:
            request.session.create()
        cart, created = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            user__isnull=True
        )
    return cart


class CartDetailView(View):
    """Display cart contents."""
    def get(self, request):
        cart = get_or_create_cart(request)
        return render(request, 'cart/detail.html', {'cart': cart})


@require_POST

def cart_add(request, product_id):
    """Add product to cart."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    quantity = int(request.POST.get('quantity', 1))
    
    if not product.in_stock:
        if request.htmx:
            return JsonResponse({'error': _('Product is out of stock')}, status=400)
        messages.error(request, _('This product is out of stock.'))
        return redirect('products:detail', slug=product.slug)
    
    if quantity > product.stock_quantity:
        quantity = product.stock_quantity
    
    cart = get_or_create_cart(request)
    item = cart.add_item(product, quantity)

    if request.htmx:
        # Full drawer (keeps the auto-open behaviour) plus OOB fragments so
        # the underlying cart page stays in sync when it is open too.
        drawer = render(request, 'cart/partials/_drawer.html', {'cart': cart})
        oob = render(request, 'cart/partials/_cart_mutations.html', {'cart': cart})
        response = HttpResponse(
            drawer.content.decode('utf-8') + oob.content.decode('utf-8'),
            content_type='text/html; charset=utf-8',
        )
        response['HX-Trigger'] = 'cartUpdated'
        return response

    messages.success(request, _('Added to cart!'))
    return redirect('cart:detail')


@require_POST

def cart_update(request, item_id):
    """Update cart item quantity."""
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = item.quantity

    if quantity > 0:
        if quantity > item.product.stock_quantity:
            quantity = item.product.stock_quantity
        item.quantity = quantity
        item.save()
    else:
        item.delete()

    if request.htmx:
        # Broadcast: refreshes page region, drawer body and drawer footer
        # together so every cart surface stays in sync.
        response = render(request, 'cart/partials/_cart_mutations.html', {'cart': cart})
        response['HX-Trigger'] = 'cartUpdated'
        return response

    return redirect('cart:detail')


@require_POST

def cart_remove(request, item_id):
    """Remove item from cart."""
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item.delete()

    if request.htmx:
        response = render(request, 'cart/partials/_cart_mutations.html', {'cart': cart})
        response['HX-Trigger'] = 'cartUpdated'
        return response

    messages.success(request, _('Item removed from cart.'))
    return redirect('cart:detail')


def cart_drawer(request):
    """Return cart drawer partial for HTMX."""
    cart = get_or_create_cart(request)
    return render(request, 'cart/partials/_drawer.html', {'cart': cart})


def cart_count(request):
    """Return cart count for HTMX badge update."""
    cart = get_or_create_cart(request)
    return JsonResponse({
        'count': cart.total_items,
        'total': str(cart.total_price),
    })


def cart_clear(request):
    """Clear cart."""
    cart = get_or_create_cart(request)
    cart.clear()

    if request.htmx:
        response = render(request, 'cart/partials/_cart_mutations.html', {'cart': cart})
        response['HX-Trigger'] = 'cartUpdated'
        return response

    return redirect('cart:detail')
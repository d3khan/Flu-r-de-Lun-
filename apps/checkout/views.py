from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.http import JsonResponse

from apps.cart.models import Cart, CartItem
from apps.products.models import Product
from apps.orders.models import Order, OrderItem
from apps.core.models import SiteSettings
from apps.core.utils.whatsapp import order_whatsapp_url


def get_or_create_cart(request):
    """Get or create cart for current request."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user, session_key='')
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


def _contact_details_from_session(request):
    """Return the contact details saved during checkout.

    Older sessions used the key ``checkout_shipping`` and carried address
    fields; only the contact fields are reused now.
    """
    details = request.session.get('checkout_details')
    if details:
        return details
    legacy = request.session.get('checkout_shipping') or {}
    if legacy:
        return {key: legacy.get(key, '') for key in ('first_name', 'last_name', 'email', 'phone')}
    return None


def checkout_step1_details(request):
    """Step 1: name, email and phone for the WhatsApp order."""
    cart = get_or_create_cart(request)

    if not cart.items.exists():
        messages.warning(request, _('Your cart is empty.'))
        return redirect('cart:detail')

    initial = {}
    if request.user.is_authenticated:
        initial = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': request.user.phone,
        }

    if request.method == 'POST':
        details = {
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
            'email': request.POST.get('email', '').strip().lower(),
            'phone': request.POST.get('phone', '').strip(),
        }
        request.session['checkout_details'] = details

        required = ['first_name', 'last_name', 'email', 'phone']
        missing = [f for f in required if not details.get(f)]

        if missing:
            messages.error(request, _('Please fill in all required fields.'))
            # Keep what the customer already typed instead of resetting the
            # form to the saved profile values.
            initial = {**initial, **details}
        else:
            return redirect('checkout:step2')

    subtotal = cart.total_price
    context = {
        'cart': cart,
        'subtotal': subtotal,
        'total': subtotal,
        'initial': initial,
        'step': 1,
    }
    return render(request, 'checkout/step1_details.html', context)


def checkout_step2_payment(request):
    """Step 2: review the order and continue to WhatsApp."""
    cart = get_or_create_cart(request)

    if not cart.items.exists():
        return redirect('cart:detail')

    details = _contact_details_from_session(request)
    if not details:
        return redirect('checkout:step1')

    subtotal = cart.total_price
    total = subtotal

    if request.method == 'POST':
        request.session['checkout_payment_method'] = 'whatsapp'
        return redirect('checkout:step3')

    context = {
        'cart': cart,
        'details': details,
        'subtotal': subtotal,
        'total': total,
        'step': 2,
    }
    return render(request, 'checkout/step2_payment.html', context)


def checkout_step3_payment(request):
    """Step 3: review the order, then place it."""
    cart = get_or_create_cart(request)

    if not cart.items.exists():
        return redirect('cart:detail')

    details = _contact_details_from_session(request)
    payment_method = request.session.get('checkout_payment_method')

    if not details or not payment_method:
        return redirect('checkout:step1')

    # Sessions created before the WhatsApp-only flow may still hold an old
    # value. Normalise instead of sending the customer through a dead route.
    if payment_method != 'whatsapp':
        payment_method = request.session['checkout_payment_method'] = 'whatsapp'

    subtotal = cart.total_price
    total = subtotal

    if request.method == 'POST':
        # Never create an order for an item that has sold out or whose stock
        # dropped while the customer was in checkout.
        unavailable = []
        for item in cart.items.select_related('product'):
            if (
                not item.product
                or not item.product.in_stock
                or item.quantity > item.product.stock_quantity
            ):
                unavailable.append(item.product.name if item.product else str(item))
        if unavailable:
            messages.error(
                request,
                _('Some items are no longer available: %(items)s. Please review your cart.')
                % {'items': ', '.join(unavailable)},
            )
            return redirect('cart:detail')

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key if not request.user.is_authenticated else '',
                first_name=details['first_name'],
                last_name=details['last_name'],
                email=details['email'],
                phone=details['phone'],
                payment_method='whatsapp',
                subtotal=subtotal,
                shipping_cost=0,
                total=total,
                status='pending',
            )

            for item in cart.items.select_related('product'):
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    product_sku=item.product.sku,
                    price=item.product.price,
                    quantity=item.quantity,
                )

            # Stock stays in the catalogue until the order is confirmed,
            # processing or delivered (see Order.apply_status_stock).
            cart.clear()
            request.session['checkout_order_id'] = order.id

        return redirect('checkout:whatsapp_payment', order_id=order.id)

    context = {
        'cart': cart,
        'details': details,
        'subtotal': subtotal,
        'total': total,
        'step': 3,
    }
    return render(request, 'checkout/step3_payment.html', context)


def _owned_order_or_none(request, order_id):
    """Return the order only when it belongs to this customer/session."""
    order = get_object_or_404(Order, id=order_id)
    if request.user.is_authenticated and order.user_id == request.user.id:
        return order
    if (
        order.user_id is None
        and order.session_key
        and order.session_key == request.session.session_key
    ):
        return order
    return None


def whatsapp_payment(request, order_id):
    """Show the WhatsApp hand-off for a newly placed order."""
    order = _owned_order_or_none(request, order_id)
    if order is None:
        return redirect('core:home')

    site_settings = SiteSettings.get_settings()
    context = {
        'order': order,
        'whatsapp_url': order_whatsapp_url(order),
        'whatsapp_number': site_settings.whatsapp_number,
        'whatsapp_display': site_settings.whatsapp_display,
    }
    return render(request, 'checkout/whatsapp_payment.html', context)


def order_confirmation(request, order_id):
    """Order confirmation page."""
    order = _owned_order_or_none(request, order_id)
    if order is None:
        return redirect('core:home')

    # Clear checkout session data
    for key in ['checkout_details', 'checkout_shipping', 'checkout_payment_method', 'checkout_order_id']:
        request.session.pop(key, None)

    context = {
        'order': order,
        'whatsapp_url': order_whatsapp_url(order),
    }
    return render(request, 'checkout/confirmation.html', context)


@require_POST
def checkout_validate_stock(request):
    """AJAX endpoint to validate stock before checkout."""
    cart = get_or_create_cart(request)
    
    out_of_stock = []
    low_stock = []
    
    for item in cart.items.all():
        if not item.product.in_stock:
            out_of_stock.append(item.product.name)
        elif item.quantity > item.product.stock_quantity:
            low_stock.append({
                'name': item.product.name,
                'available': item.product.stock_quantity,
                'requested': item.quantity,
            })
    
    return JsonResponse({
        'valid': len(out_of_stock) == 0 and len(low_stock) == 0,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
    })

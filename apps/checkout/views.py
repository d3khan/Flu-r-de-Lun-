from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings

from apps.cart.models import Cart, CartItem
from apps.products.models import Product
from apps.orders.models import Order, OrderItem
from apps.accounts.models import Address
from apps.payments.models import ManualPaymentInfo


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


from apps.cart.utils import calculate_shipping


def checkout_step1_shipping(request):
    """Step 1: Shipping information."""
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        messages.warning(request, _('Your cart is empty.'))
        return redirect('cart:detail')
    
    # Pre-fill from user profile if authenticated
    initial = {}
    if request.user.is_authenticated:
        initial = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': request.user.phone,
        }
        
        # Try to get default address
        default_address = Address.objects.filter(user=request.user, is_default=True).first()
        if default_address:
            initial.update({
                'address_line_1': default_address.address_line_1,
                'address_line_2': default_address.address_line_2,
                'city': default_address.city,
                'state': default_address.state,
                'postal_code': default_address.postal_code,
            })
    
    if request.method == 'POST':
        # Store shipping info in session
        request.session['checkout_shipping'] = {
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
            'email': request.POST.get('email', '').strip().lower(),
            'phone': request.POST.get('phone', '').strip(),
            'address_line_1': request.POST.get('address_line_1', '').strip(),
            'address_line_2': request.POST.get('address_line_2', '').strip(),
            'city': request.POST.get('city', '').strip(),
            'state': request.POST.get('state', '').strip(),
            'postal_code': request.POST.get('postal_code', '').strip(),
        }
        
        # Validate required fields
        shipping = request.session['checkout_shipping']
        required = ['first_name', 'last_name', 'email', 'phone', 'address_line_1', 'city', 'state']
        missing = [f for f in required if not shipping.get(f)]
        
        if missing:
            messages.error(request, _('Please fill in all required fields.'))
        else:
            return redirect('checkout:step2')
    
    subtotal = cart.total_price
    shipping_cost = calculate_shipping(subtotal)
    
    context = {
        'cart': cart,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': subtotal + shipping_cost,
        'initial': initial,
        'step': 1,
    }
    return render(request, 'checkout/step1_shipping.html', context)


def checkout_step2_payment(request):
    """Step 2: Payment method selection."""
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        return redirect('cart:detail')
    
    shipping = request.session.get('checkout_shipping')
    if not shipping:
        return redirect('checkout:step1')
    
    payments_enabled = getattr(settings, 'PAYMENTS_ENABLED', False)
    
    subtotal = cart.total_price
    shipping_cost = calculate_shipping(subtotal)
    total = subtotal + shipping_cost
    
    payment_info = ManualPaymentInfo.get_active()
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        if payment_method not in ['gateway', 'manual']:
            messages.error(request, _('Please select a payment method.'))
        elif payment_method == 'gateway' and not payments_enabled:
            # Online payments are not available yet
            return render(request, 'checkout/payment_under_development.html')
        else:
            request.session['checkout_payment_method'] = payment_method
            return redirect('checkout:step3')
    
    context = {
        'cart': cart,
        'shipping': shipping,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
        'payment_info': payment_info,
        'step': 2,
    }
    return render(request, 'checkout/step2_payment.html', context)


def checkout_step3_payment(request):
    """Step 3: Payment processing."""
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        return redirect('cart:detail')
    
    shipping = request.session.get('checkout_shipping')
    payment_method = request.session.get('checkout_payment_method')
    
    if not shipping or not payment_method:
        return redirect('checkout:step1')
    
    subtotal = cart.total_price
    shipping_cost = calculate_shipping(subtotal)
    total = subtotal + shipping_cost
    
    payment_info = ManualPaymentInfo.get_active()
    
    # Block gateway payment if disabled
    if payment_method == 'gateway' and not getattr(settings, 'PAYMENTS_ENABLED', False):
        return render(request, 'checkout/payment_under_development.html')
    
    if request.method == 'POST':
        with transaction.atomic():
            # Create order
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key if not request.user.is_authenticated else '',
                first_name=shipping['first_name'],
                last_name=shipping['last_name'],
                email=shipping['email'],
                phone=shipping['phone'],
                shipping_address_line_1=shipping['address_line_1'],
                shipping_address_line_2=shipping['address_line_2'],
                shipping_city=shipping['city'],
                shipping_state=shipping['state'],
                shipping_postal_code=shipping['postal_code'],
                shipping_country='NG',
                payment_method=payment_method,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                total=total,
                status='pending',
            )
            
            # Create order items
            for item in cart.items.all():
                if item.product and item.product.in_stock:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        product_sku=item.product.sku,
                        price=item.product.price,
                        quantity=item.quantity,
                    )
                    # Decrease stock
                    item.product.stock_quantity -= item.quantity
                    item.product.save()
            
            # Save order ID in session for payment step
            request.session['checkout_order_id'] = order.id
            
            if payment_method == 'gateway':
                if not getattr(settings, 'PAYMENTS_ENABLED', False):
                    return render(request, 'checkout/payment_under_development.html')
                return redirect('checkout:gateway_payment', order_id=order.id)
            else:
                return redirect('checkout:manual_payment', order_id=order.id)
    
    context = {
        'cart': cart,
        'shipping': shipping,
        'payment_method': payment_method,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total,
        'payment_info': payment_info,
        'step': 3,
    }
    return render(request, 'checkout/step3_payment.html', context)


def gateway_payment(request, order_id):
    """Gateway payment page."""
    if not getattr(settings, 'PAYMENTS_ENABLED', False):
        return render(request, 'checkout/payment_under_development.html')
    
    order = get_object_or_404(Order, id=order_id)
    
    # Verify ownership
    if request.user.is_authenticated and order.user != request.user:
        return redirect('core:home')
    if not request.user.is_authenticated and order.session_key != request.session.session_key:
        return redirect('core:home')
    
    payment_info = ManualPaymentInfo.get_active()
    
    context = {
        'order': order,
        'payment_info': payment_info,
    }
    return render(request, 'checkout/gateway_payment.html', context)


def manual_payment(request, order_id):
    """Manual payment instructions page."""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify ownership
    if request.user.is_authenticated and order.user != request.user:
        return redirect('core:home')
    if not request.user.is_authenticated and order.session_key != request.session.session_key:
        return redirect('core:home')
    
    payment_info = ManualPaymentInfo.get_active()
    
    context = {
        'order': order,
        'payment_info': payment_info,
        'whatsapp_url': payment_info.get_whatsapp_url(order) if payment_info else '#',
    }
    return render(request, 'checkout/manual_payment.html', context)


def order_confirmation(request, order_id):
    """Order confirmation page."""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify ownership
    if request.user.is_authenticated and order.user != request.user:
        return redirect('core:home')
    if not request.user.is_authenticated and order.session_key != request.session.session_key:
        return redirect('core:home')
    
    # Clear checkout session data
    for key in ['checkout_shipping', 'checkout_payment_method', 'checkout_order_id']:
        request.session.pop(key, None)
    
    context = {
        'order': order,
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


def checkout_save_address(request):
    """Save address to user profile from checkout."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    address = Address.objects.create(
        user=request.user,
        label=request.POST.get('label', 'Home'),
        first_name=request.POST.get('first_name'),
        last_name=request.POST.get('last_name'),
        phone=request.POST.get('phone'),
        address_line_1=request.POST.get('address_line_1'),
        address_line_2=request.POST.get('address_line_2', ''),
        city=request.POST.get('city'),
        state=request.POST.get('state'),
        postal_code=request.POST.get('postal_code', ''),
        country='NG',
        is_default=request.POST.get('is_default') == 'true',
    )
    
    return JsonResponse({'success': True, 'address_id': address.id})
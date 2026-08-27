from django.shortcuts import render, get_object_or_404, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Order, OrderItem, OrderStatusHistory
from apps.cart.models import Cart
from apps.products.models import Product


class OrderHistoryView(LoginRequiredMixin, ListView):
    """User's order history."""
    model = Order
    template_name = 'orders/history.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product')


class OrderDetailView(LoginRequiredMixin, DetailView):
    """Order detail view."""
    model = Order
    template_name = 'orders/detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items__product', 'status_history')


def guest_order_lookup(request):
    """Guest order lookup form; posts order number + email."""
    if request.method == 'POST':
        order_number = request.POST.get('order_number', '').strip().upper()
        email = request.POST.get('email', '').strip().lower()
        if order_number and email:
            return redirect(f"{reverse('orders:guest_detail', kwargs={'order_number': order_number})}?email={email}")
        messages.error(request, _('Please enter your order number and email.'))
    return render(request, 'orders/guest_lookup.html', {'order_number': ''})


def guest_order_detail(request, order_number):
    """Guest order lookup by order number and email."""
    email = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
    elif request.method == 'GET':
        email = request.GET.get('email', '').strip().lower()

    if email:
        order = Order.objects.filter(order_number=order_number.upper(), email__iexact=email).first()
        if order:
            return render(request, 'orders/detail.html', {'order': order, 'guest': True})
        messages.error(request, _('Order not found. Please check your order number and email.'))
    return render(request, 'orders/guest_lookup.html', {'order_number': order_number})


@require_POST
@login_required
def order_cancel(request, pk):
    """Cancel an order."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    
    if not order.can_cancel:
        messages.error(request, _('This order cannot be cancelled.'))
        return redirect('orders:detail', pk=pk)
    
    with transaction.atomic():
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.save()
            
        OrderStatusHistory.objects.create(
            order=order,
            status='cancelled',
            note=_('Cancelled by customer'),
            created_by=request.user
        )
            
        # Restore stock
        for item in order.items.all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save()
    messages.success(request, _('Order cancelled successfully.'))
    return redirect('orders:detail', pk=pk)
    

@login_required
def order_reorder(request, pk):
    """Reorder items from a previous order."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    cart = Cart.objects.get_or_create(user=request.user, session_key='')[0]
    
    added_count = 0
    for item in order.items.all():
        if item.product and item.product.is_active and item.product.in_stock:
            cart.add_item(item.product, item.quantity)
            added_count += 1
    
    if added_count:
        messages.success(request, _(f'{added_count} item(s) added to cart.'))
    else:
        messages.warning(request, _('No items from this order are currently available.'))
    
    return redirect('cart:detail')


# Admin/staff views (can be moved to admin.py later)

def order_list_admin(request):
    """Admin order list with filters."""
    if not request.user.is_staff:
        return redirect('core:home')
    
    orders = Order.objects.all().select_related('user').prefetch_related('items')
    
    # Filters
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    payment_method = request.GET.get('payment_method')
    if payment_method:
        orders = orders.filter(payment_method=payment_method)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'orders': page_obj,
        'status_choices': Order.STATUS_CHOICES,
        'payment_method_choices': Order.PAYMENT_METHOD_CHOICES,
        'current_status': status,
        'current_payment_method': payment_method,
    }
    return render(request, 'orders/admin_list.html', context)


def order_detail_admin(request, pk):
    """Admin order detail with status update."""
    if not request.user.is_staff:
        return redirect('core:home')
    
    order = get_object_or_404(Order, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        note = request.POST.get('note', '')
        
        if new_status and new_status != order.status:
            old_status = order.status
            order.status = new_status
            
            # Set timestamps

            now = timezone.now()
            if new_status == 'confirmed' and not order.confirmed_at:
                order.confirmed_at = now
            elif new_status == 'shipped' and not order.shipped_at:
                order.shipped_at = now
            elif new_status == 'delivered' and not order.delivered_at:
                order.delivered_at = now
            elif new_status == 'cancelled' and not order.cancelled_at:
                order.cancelled_at = now
            
            order.save()
            
            OrderStatusHistory.objects.create(
                order=order,
                status=new_status,
                note=note or f'Status changed from {old_status} to {new_status}',
                created_by=request.user
            )
            
            messages.success(request, _('Order status updated.'))
            return redirect('orders:admin_detail', pk=pk)
    
    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'orders/admin_detail.html', context)


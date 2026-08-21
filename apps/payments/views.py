from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import json

from .models import PaymentTransaction, PaymentLink, ManualPaymentInfo
from .services import get_payment_service, create_payment_for_order
from apps.orders.models import Order


def payment_callback(request, order_id):
    """Handle payment gateway callback (redirect after payment)."""
    order = get_object_or_404(Order, id=order_id)
    
    # Get reference from query params
    reference = request.GET.get('reference') or request.GET.get('tx_ref')
    
    if not reference:
        messages.error(request, _('Invalid payment callback.'))
        return redirect('checkout:step3_payment', order_id=order.id)
    
    # Verify payment
    service = get_payment_service()
    result = service.verify_payment(reference)
    
    if result.get('success'):
        # Update transaction
        try:
            transaction = PaymentTransaction.objects.get(reference=reference)
            transaction.mark_success(result.get('gateway_response'))
        except PaymentTransaction.DoesNotExist:
            # Create if doesn't exist
            PaymentTransaction.objects.create(
                order=order,
                gateway=service.__class__.__name__.replace('Service', '').lower(),
                reference=reference,
                amount=result['amount'],
                currency=result['currency'],
                customer_email=order.email,
                customer_name=order.full_name,
                gateway_response=result.get('gateway_response', {}),
                gateway_reference=result.get('gateway_reference', ''),
                status='success',
                verified_at=timezone.now(),
                paid_at=timezone.now(),
            )
            order.payment_verified = True
            order.payment_verified_at = timezone.now()
            order.payment_reference = reference
            order.status = 'confirmed'
            order.confirmed_at = timezone.now()
            order.save()
        
        # Mark payment link as used
        PaymentLink.objects.filter(order=order).update(is_used=True)
        
        messages.success(request, _('Payment successful! Your order has been confirmed.'))
        return redirect('orders:detail', pk=order.pk)
    else:
        # Mark transaction as failed
        try:
            transaction = PaymentTransaction.objects.get(reference=reference)
            transaction.mark_failed(result)
        except PaymentTransaction.DoesNotExist:
            pass
        
        messages.error(request, _('Payment verification failed. Please contact support.'))
        return redirect('checkout:step3_payment', order_id=order.id)


@csrf_exempt
@require_POST
def payment_webhook(request):
    """Handle payment gateway webhooks."""
    service = get_payment_service()
    
    # Verify signature
    signature = request.headers.get('X-Paystack-Signature') or request.headers.get('Verif-Hash')
    if not service.verify_webhook(request.body, signature):
        return HttpResponse('Invalid signature', status=400)
    
    try:
        payload = json.loads(request.body)
        result = service.process_webhook(payload)
        
        if result.get('success'):
            reference = result.get('reference')
            try:
                transaction = PaymentTransaction.objects.get(reference=reference)
                if result.get('success'):
                    transaction.mark_success(result.get('gateway_response'))
                else:
                    transaction.mark_failed(result)
            except PaymentTransaction.DoesNotExist:
                pass
        
        return HttpResponse('OK')
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)


def initiate_gateway_payment(request, order_id):
    """AJAX endpoint to create payment link and redirect."""
    order = get_object_or_404(Order, id=order_id)
    
    if order.payment_method != 'gateway':
        return JsonResponse({'success': False, 'error': 'Invalid payment method'}, status=400)
    
    result = create_payment_for_order(order, request)
    
    if result['success']:
        return JsonResponse({'success': True, 'redirect_url': result['url']})
    else:
        return JsonResponse({'success': False, 'error': result['error']}, status=400)


def manual_payment_info(request):
    """Return manual payment info for HTMX."""
    info = ManualPaymentInfo.get_active()
    order_id = request.GET.get('order_id')
    order = None
    if order_id:
        order = get_object_or_404(Order, id=order_id)
    
    context = {
        'payment_info': info,
        'order': order,
    }
    return render(request, 'payments/partials/_manual_payment_info.html', context)


def payment_method_select(request, order_id):
    """Payment method selection partial."""
    order = get_object_or_404(Order, id=order_id)
    payment_info = ManualPaymentInfo.get_active()
    
    context = {
        'order': order,
        'payment_info': payment_info,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'flutterwave_public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
    }
    return render(request, 'payments/partials/_payment_method_select.html', context)
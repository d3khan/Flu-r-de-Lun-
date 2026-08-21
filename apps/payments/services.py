"""
Payment gateway services for Paystack and Flutterwave.
Uses Payment Links (hosted checkout) - no card data touches our server.
"""
import json
import hmac
import hashlib
import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

from .models import PaymentTransaction, PaymentLink, ManualPaymentInfo


class PaymentGatewayError(Exception):
    """Custom exception for payment gateway errors."""
    pass


class BasePaymentService:
    """Base class for payment gateways."""
    
    def __init__(self):
        self.base_url = ''
        self.secret_key = ''
        self.public_key = ''
    
    def create_payment_link(self, order, callback_url, cancel_url):
        """Create a hosted payment page link."""
        raise NotImplementedError
    
    def verify_payment(self, reference):
        """Verify payment status from gateway."""
        raise NotImplementedError
    
    def verify_webhook(self, payload, signature):
        """Verify webhook signature."""
        raise NotImplementedError
    
    def _make_request(self, method, endpoint, data=None, headers=None):
        """Make HTTP request to gateway API."""
        url = f'{self.base_url}{endpoint}'
        default_headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }
        if headers:
            default_headers.update(headers)
        
        try:
            response = requests.request(
                method, url, json=data, headers=default_headers, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise PaymentGatewayError(f'Gateway request failed: {str(e)}')


class PaystackService(BasePaymentService):
    """Paystack payment gateway integration."""
    
    def __init__(self):
        super().__init__()
        self.base_url = 'https://api.paystack.co'
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
    
    def create_payment_link(self, order, callback_url, cancel_url):
        """Create Paystack payment page link."""
        # Paystack uses Initialize Transaction which returns authorization_url
        data = {
            'email': order.email,
            'amount': int(order.total * 100),  # Paystack expects amount in kobo
            'currency': 'NGN',
            'reference': order.order_number,
            'callback_url': callback_url,
            'metadata': {
                'order_id': order.id,
                'order_number': order.order_number,
                'customer_name': order.full_name,
                'customer_phone': order.phone,
                'cancel_action': cancel_url,
            },
            'channels': ['card', 'bank', 'ussd', 'qr', 'mobile_money', 'bank_transfer'],
        }
        
        response = self._make_request('POST', '/transaction/initialize', data)
        
        if response.get('status') and response['data'].get('authorization_url'):
            return {
                'url': response['data']['authorization_url'],
                'reference': response['data']['reference'],
                'access_code': response['data']['access_code'],
            }
        raise PaymentGatewayError(response.get('message', 'Failed to create payment link'))
    
    def verify_payment(self, reference):
        """Verify Paystack transaction."""
        response = self._make_request('GET', f'/transaction/verify/{reference}')
        
        if response.get('status') and response['data'].get('status') == 'success':
            return {
                'success': True,
                'reference': response['data']['reference'],
                'amount': Decimal(response['data']['amount']) / 100,
                'currency': response['data']['currency'],
                'gateway_reference': response['data'].get('id'),
                'paid_at': response['data'].get('paid_at'),
                'channel': response['data'].get('channel'),
                'customer': response['data'].get('customer'),
                'metadata': response['data'].get('metadata'),
                'gateway_response': response['data'],
            }
        return {'success': False, 'message': response.get('message', 'Verification failed')}
    
    def verify_webhook(self, payload, signature):
        """Verify Paystack webhook signature."""
        expected = hmac.new(
            self.secret_key.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    def process_webhook(self, payload):
        """Process Paystack webhook event."""
        event = payload.get('event')
        data = payload.get('data', {})
        
        if event == 'charge.success':
            reference = data.get('reference')
            return self.verify_payment(reference)
        
        return {'success': False, 'message': f'Unhandled event: {event}'}


class FlutterwaveService(BasePaymentService):
    """Flutterwave payment gateway integration."""
    
    def __init__(self):
        super().__init__()
        self.base_url = 'https://api.flutterwave.com/v3'
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.public_key = settings.FLUTTERWAVE_PUBLIC_KEY
        self.encryption_key = settings.FLUTTERWAVE_ENCRYPTION_KEY
    
    def create_payment_link(self, order, callback_url, cancel_url):
        """Create Flutterwave payment link."""
        data = {
            'tx_ref': order.order_number,
            'amount': float(order.total),
            'currency': 'NGN',
            'redirect_url': callback_url,
            'customer': {
                'email': order.email,
                'name': order.full_name,
                'phonenumber': order.phone,
            },
            'customizations': {
                'title': 'Fluér de Luné',
                'description': f'Order {order.order_number}',
                'logo': f'{settings.SITE_URL}{settings.STATIC_URL}images/logo.svg',
            },
            'meta': {
                'order_id': order.id,
                'order_number': order.order_number,
            },
            'payment_options': 'card,banktransfer,ussd,mobilemoney,barter',
        }
        
        response = self._make_request('POST', '/payments', data)
        
        if response.get('status') == 'success' and response['data'].get('link'):
            return {
                'url': response['data']['link'],
                'reference': response['data']['tx_ref'],
            }
        raise PaymentGatewayError(response.get('message', 'Failed to create payment link'))
    
    def verify_payment(self, reference):
        """Verify Flutterwave transaction."""
        response = self._make_request('GET', f'/transactions/verify_by_reference?tx_ref={reference}')
        
        if response.get('status') == 'success' and response['data']:
            tx = response['data'][0] if isinstance(response['data'], list) else response['data']
            if tx.get('status') == 'successful':
                return {
                    'success': True,
                    'reference': tx['tx_ref'],
                    'amount': Decimal(str(tx['amount'])),
                    'currency': tx['currency'],
                    'gateway_reference': tx.get('id') or tx.get('flw_ref'),
                    'paid_at': tx.get('created_at'),
                    'channel': tx.get('payment_type'),
                    'customer': tx.get('customer'),
                    'metadata': tx.get('meta'),
                    'gateway_response': tx,
                }
        return {'success': False, 'message': response.get('message', 'Verification failed')}
    
    def verify_webhook(self, payload, signature):
        """Verify Flutterwave webhook signature."""
        expected = hmac.new(
            self.encryption_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    def process_webhook(self, payload):
        """Process Flutterwave webhook event."""
        event = payload.get('event')
        data = payload.get('data', {})
        
        if event == 'charge.completed' and data.get('status') == 'successful':
            reference = data.get('tx_ref')
            return self.verify_payment(reference)
        
        return {'success': False, 'message': f'Unhandled event: {event}'}


def get_payment_service():
    """Get the configured payment service."""
    gateway = getattr(settings, 'PAYMENT_GATEWAY', 'paystack')
    if gateway == 'flutterwave':
        return FlutterwaveService()
    return PaystackService()


def create_payment_for_order(order, request):
    """Create payment link for an order."""
    service = get_payment_service()
    
    callback_url = request.build_absolute_uri(
        reverse('payments:callback', kwargs={'order_id': order.id})
    )
    cancel_url = request.build_absolute_uri(
        reverse('checkout:step3_payment', kwargs={'order_id': order.id})
    )
    
    try:
        result = service.create_payment_link(order, callback_url, cancel_url)
        
        # Save payment link
        PaymentLink.objects.create(
            order=order,
            gateway=service.__class__.__name__.replace('Service', '').lower(),
            url=result['url'],
            reference=result['reference'],
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        
        # Create pending transaction
        PaymentTransaction.objects.create(
            order=order,
            gateway=service.__class__.__name__.replace('Service', '').lower(),
            reference=result['reference'],
            amount=order.total,
            customer_email=order.email,
            customer_name=order.full_name,
            status='pending',
        )
        
        return {'success': True, 'url': result['url']}
    
    except PaymentGatewayError as e:
        return {'success': False, 'error': str(e)}
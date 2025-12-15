# -*- coding: utf-8 -*-
"""
Payment Integration
Iyzico and Stripe payment gateway support
"""
import os
import uuid
import hashlib
import hmac
import base64
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class PaymentProvider:
    """Base class for payment providers."""
    
    def create_payment(self, amount: float, currency: str, **kwargs) -> Dict:
        raise NotImplementedError
    
    def verify_payment(self, payment_id: str) -> Dict:
        raise NotImplementedError
    
    def refund_payment(self, payment_id: str, amount: float = None) -> Dict:
        raise NotImplementedError


class IyzicoPayment(PaymentProvider):
    """
    Iyzico payment integration for Turkish market.
    
    Required env vars:
        IYZICO_API_KEY: API key from Iyzico dashboard
        IYZICO_SECRET_KEY: Secret key from Iyzico dashboard
        IYZICO_BASE_URL: https://sandbox-api.iyzipay.com (sandbox) or https://api.iyzipay.com (production)
    """
    
    def __init__(self):
        self.api_key = os.getenv('IYZICO_API_KEY', '')
        self.secret_key = os.getenv('IYZICO_SECRET_KEY', '')
        self.base_url = os.getenv('IYZICO_BASE_URL', 'https://sandbox-api.iyzipay.com')
    
    def _generate_auth_string(self, uri: str, request_string: str) -> str:
        """Generate authorization header for Iyzico."""
        random_string = str(uuid.uuid4()).replace('-', '')[:8]
        sha_string = hashlib.sha1(
            (random_string + request_string).encode('utf-8')
        ).digest()
        authorization_string = 'IYZWS ' + self.api_key + ':' + base64.b64encode(sha_string).decode()
        return authorization_string, random_string
    
    def _make_request(self, endpoint: str, data: Dict) -> Dict:
        """Make authenticated request to Iyzico."""
        url = f"{self.base_url}{endpoint}"
        request_string = json.dumps(data, separators=(',', ':'))
        
        auth, random = self._generate_auth_string(endpoint, request_string)
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': auth,
            'x-iyzi-rnd': random
        }
        
        response = requests.post(url, data=request_string, headers=headers)
        return response.json()
    
    def create_checkout_form(
        self,
        amount: float,
        buyer_email: str,
        buyer_name: str,
        buyer_id: str,
        callback_url: str,
        currency: str = 'TRY',
        credit_package: str = 'standard',
        buyer_ip: str = None,
        buyer_identity_no: str = None
    ) -> Dict:
        """
        Create Iyzico checkout form for credit purchase.
        
        Args:
            amount: Payment amount
            buyer_email: Buyer's email
            buyer_name: Buyer's full name
            buyer_id: Internal buyer ID
            callback_url: URL to redirect after payment
            currency: Currency code (TRY, USD, EUR)
            credit_package: Package identifier
        
        Returns:
            dict: Contains checkoutFormContent (HTML) and token
        """
        conversation_id = str(uuid.uuid4())
        
        data = {
            'locale': 'tr',
            'conversationId': conversation_id,
            'price': str(amount),
            'paidPrice': str(amount),
            'currency': currency,
            'basketId': f'CREDITS_{credit_package}_{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'paymentGroup': 'PRODUCT',
            'callbackUrl': callback_url,
            'enabledInstallments': [1, 2, 3, 6, 9],
            'buyer': {
                'id': buyer_id,
                'name': buyer_name.split()[0] if ' ' in buyer_name else buyer_name,
                'surname': buyer_name.split()[-1] if ' ' in buyer_name else buyer_name,
                'email': buyer_email,
                'identityNumber': buyer_identity_no or '11111111111',  # Real TC if provided, else placeholder
                'registrationAddress': 'Turkey',
                'city': 'Istanbul',
                'country': 'Turkey',
                'ip': buyer_ip or '127.0.0.1'  # Real IP from request.remote_addr
            },
            'shippingAddress': {
                'contactName': buyer_name,
                'city': 'Istanbul',
                'country': 'Turkey',
                'address': 'Turkey'
            },
            'billingAddress': {
                'contactName': buyer_name,
                'city': 'Istanbul',
                'country': 'Turkey',
                'address': 'Turkey'
            },
            'basketItems': [
                {
                    'id': f'CREDITS_{credit_package}',
                    'name': f'Sınav Kredisi - {credit_package.title()} Paket',
                    'category1': 'Dijital Ürün',
                    'itemType': 'VIRTUAL',
                    'price': str(amount)
                }
            ]
        }
        
        result = self._make_request('/payment/iyzipos/checkoutform/initialize/auth/ecom', data)
        
        return {
            'success': result.get('status') == 'success',
            'token': result.get('token'),
            'checkout_form_content': result.get('checkoutFormContent'),
            'conversation_id': conversation_id,
            'error': result.get('errorMessage')
        }
    
    def verify_payment(self, token: str) -> Dict:
        """
        Verify payment after callback.
        
        Args:
            token: Payment token from callback
        
        Returns:
            dict: Payment verification result
        """
        data = {
            'locale': 'tr',
            'token': token
        }
        
        result = self._make_request('/payment/iyzipos/checkoutform/auth/ecom/detail', data)
        
        return {
            'success': result.get('status') == 'success' and result.get('paymentStatus') == 'SUCCESS',
            'payment_id': result.get('paymentId'),
            'amount': float(result.get('paidPrice', 0)),
            'currency': result.get('currency'),
            'card_last_four': result.get('lastFourDigits'),
            'basket_id': result.get('basketId'),
            'error': result.get('errorMessage')
        }


class StripePayment(PaymentProvider):
    """
    Stripe payment integration for international market.
    
    Required env vars:
        STRIPE_SECRET_KEY: sk_test_... or sk_live_...
        STRIPE_PUBLISHABLE_KEY: pk_test_... or pk_live_...
        STRIPE_WEBHOOK_SECRET: whsec_...
    """
    
    def __init__(self):
        self.secret_key = os.getenv('STRIPE_SECRET_KEY', '')
        self.publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
        
        # Set Stripe API key
        try:
            import stripe
            stripe.api_key = self.secret_key
            self.stripe = stripe
        except ImportError:
            self.stripe = None
            logger.warning("Stripe library not installed. Run: pip install stripe")
    
    def create_checkout_session(
        self,
        amount: int,  # Amount in cents
        currency: str,
        customer_email: str,
        success_url: str,
        cancel_url: str,
        credit_amount: int,
        metadata: Dict = None
    ) -> Dict:
        """
        Create Stripe checkout session.
        
        Args:
            amount: Amount in cents
            currency: Currency code (usd, eur, try)
            customer_email: Customer email
            success_url: URL for successful payment
            cancel_url: URL for cancelled payment
            credit_amount: Number of credits to add
            metadata: Additional metadata
        
        Returns:
            dict: Session details including URL
        """
        if not self.stripe:
            return {'success': False, 'error': 'Stripe not configured'}
        
        try:
            session = self.stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'unit_amount': amount,
                        'product_data': {
                            'name': f'{credit_amount} Sınav Kredisi',
                            'description': 'Skills Test Center sınav kredisi'
                        }
                    },
                    'quantity': 1
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata={
                    'credit_amount': credit_amount,
                    **(metadata or {})
                }
            )
            
            return {
                'success': True,
                'session_id': session.id,
                'checkout_url': session.url,
                'publishable_key': self.publishable_key
            }
            
        except Exception as e:
            logger.error(f"Stripe checkout error: {e}")
            return {'success': False, 'error': str(e)}
    
    def verify_webhook(self, payload: bytes, signature: str) -> Tuple[bool, Optional[Dict]]:
        """
        Verify Stripe webhook signature.
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
        
        Returns:
            tuple: (is_valid, event_data)
        """
        if not self.stripe:
            return False, None
        
        try:
            event = self.stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return True, event
        except Exception as e:
            logger.error(f"Webhook verification failed: {e}")
            return False, None
    
    def handle_successful_payment(self, session_id: str) -> Dict:
        """
        Handle successful payment from webhook.
        
        Args:
            session_id: Checkout session ID
        
        Returns:
            dict: Payment details
        """
        if not self.stripe:
            return {'success': False, 'error': 'Stripe not configured'}
        
        try:
            session = self.stripe.checkout.Session.retrieve(session_id)
            
            return {
                'success': True,
                'payment_intent': session.payment_intent,
                'customer_email': session.customer_email,
                'amount_total': session.amount_total,
                'currency': session.currency,
                'credit_amount': int(session.metadata.get('credit_amount', 0)),
                'company_id': session.metadata.get('company_id')
            }
            
        except Exception as e:
            logger.error(f"Session retrieval error: {e}")
            return {'success': False, 'error': str(e)}


class CreditPackage:
    """Credit package definitions."""
    
    PACKAGES = {
        'starter': {
            'credits': 10,
            'price_try': 500,
            'price_usd': 25,
            'price_eur': 23,
            'name': 'Başlangıç Paketi',
            'description': '10 sınav kredisi',
            'popular': False
        },
        'standard': {
            'credits': 50,
            'price_try': 2000,
            'price_usd': 100,
            'price_eur': 92,
            'name': 'Standart Paket',
            'description': '50 sınav kredisi',
            'popular': True,
            'discount': 20
        },
        'premium': {
            'credits': 100,
            'price_try': 3500,
            'price_usd': 175,
            'price_eur': 160,
            'name': 'Premium Paket',
            'description': '100 sınav kredisi',
            'popular': False,
            'discount': 30
        },
        'enterprise': {
            'credits': 500,
            'price_try': 15000,
            'price_usd': 750,
            'price_eur': 690,
            'name': 'Kurumsal Paket',
            'description': '500 sınav kredisi',
            'popular': False,
            'discount': 40
        }
    }
    
    @classmethod
    def get_package(cls, package_id: str) -> Optional[Dict]:
        return cls.PACKAGES.get(package_id)
    
    @classmethod
    def get_all_packages(cls) -> Dict:
        return cls.PACKAGES
    
    @classmethod
    def calculate_price(cls, package_id: str, currency: str = 'TRY') -> Optional[float]:
        package = cls.get_package(package_id)
        if not package:
            return None
        
        currency_key = f'price_{currency.lower()}'
        return package.get(currency_key, package.get('price_try'))


def get_payment_provider(region: str = 'TR') -> PaymentProvider:
    """
    Get appropriate payment provider for region.
    
    Args:
        region: Country/region code
    
    Returns:
        PaymentProvider instance
    """
    if region == 'TR':
        return IyzicoPayment()
    else:
        return StripePayment()

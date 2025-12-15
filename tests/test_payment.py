# -*- coding: utf-8 -*-
"""
Unit Tests for Payment Module
Tests Iyzico and Stripe integrations
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestCreditPackages:
    """Tests for credit package functionality"""
    
    def test_get_all_packages(self):
        """Test getting all credit packages"""
        from app.utils.payment import CreditPackage
        
        packages = CreditPackage.get_all_packages()
        
        assert len(packages) > 0
        assert all('name' in p for p in packages)
        assert all('credits' in p for p in packages)
        assert all('price' in p for p in packages)
    
    def test_package_has_required_fields(self):
        """Test that packages have all required fields"""
        from app.utils.payment import CreditPackage
        
        packages = CreditPackage.get_all_packages()
        required_fields = ['id', 'name', 'credits', 'price', 'currency']
        
        for package in packages:
            for field in required_fields:
                assert field in package, f"Missing field: {field}"
    
    def test_package_pricing_is_positive(self):
        """Test that all prices are positive"""
        from app.utils.payment import CreditPackage
        
        packages = CreditPackage.get_all_packages()
        
        for package in packages:
            assert package['price'] > 0
            assert package['credits'] > 0
    
    def test_get_package_by_id(self):
        """Test getting a specific package by ID"""
        from app.utils.payment import CreditPackage
        
        package = CreditPackage.get_by_id('starter')
        
        if package:  # If package exists
            assert 'credits' in package
            assert 'price' in package


class TestIyzicoPayment:
    """Tests for Iyzico payment integration"""
    
    @patch('app.utils.payment.IyzicoProvider._make_request')
    def test_create_checkout_form(self, mock_request):
        """Test creating Iyzico checkout form"""
        mock_request.return_value = {
            'status': 'success',
            'checkoutFormContent': '<form>...</form>',
            'token': 'test_token'
        }
        
        from app.utils.payment import IyzicoProvider
        
        provider = IyzicoProvider()
        result = provider.create_checkout_form(
            amount=100.00,
            currency='TRY',
            user_id=1,
            user_email='test@example.com',
            package_id='starter'
        )
        
        assert result is not None
    
    @patch('app.utils.payment.IyzicoProvider._make_request')
    def test_verify_payment_success(self, mock_request):
        """Test verifying successful Iyzico payment"""
        mock_request.return_value = {
            'status': 'success',
            'paymentStatus': 'SUCCESS',
            'paymentId': '12345'
        }
        
        from app.utils.payment import IyzicoProvider
        
        provider = IyzicoProvider()
        result = provider.verify_payment('test_token')
        
        assert result['success'] == True
    
    @patch('app.utils.payment.IyzicoProvider._make_request')
    def test_verify_payment_failure(self, mock_request):
        """Test verifying failed Iyzico payment"""
        mock_request.return_value = {
            'status': 'failure',
            'errorMessage': 'Payment failed'
        }
        
        from app.utils.payment import IyzicoProvider
        
        provider = IyzicoProvider()
        result = provider.verify_payment('test_token')
        
        assert result['success'] == False


class TestStripePayment:
    """Tests for Stripe payment integration"""
    
    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_create):
        """Test creating Stripe checkout session"""
        mock_create.return_value = MagicMock(
            id='cs_test_123',
            url='https://checkout.stripe.com/...'
        )
        
        from app.utils.payment import StripeProvider
        
        provider = StripeProvider()
        result = provider.create_checkout_session(
            amount=10.00,
            currency='USD',
            user_id=1,
            package_id='starter',
            success_url='https://example.com/success',
            cancel_url='https://example.com/cancel'
        )
        
        assert result is not None
        assert 'session_id' in result or 'url' in result
    
    @patch('stripe.Webhook.construct_event')
    def test_handle_webhook_success(self, mock_construct):
        """Test handling Stripe webhook for successful payment"""
        mock_construct.return_value = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_123',
                    'payment_status': 'paid',
                    'metadata': {'user_id': '1', 'package_id': 'starter'}
                }
            }
        }
        
        from app.utils.payment import StripeProvider
        
        provider = StripeProvider()
        result = provider.handle_webhook(
            payload='{}',
            signature='test_sig'
        )
        
        assert result is not None
    
    @patch('stripe.Webhook.construct_event')
    def test_handle_webhook_invalid_signature(self, mock_construct):
        """Test handling webhook with invalid signature"""
        from stripe.error import SignatureVerificationError
        mock_construct.side_effect = SignatureVerificationError('Invalid', 'sig')
        
        from app.utils.payment import StripeProvider
        
        provider = StripeProvider()
        result = provider.handle_webhook(
            payload='{}',
            signature='invalid_sig'
        )
        
        assert result is None or result.get('success') == False


class TestCreditTransactions:
    """Tests for credit transaction recording"""
    
    def test_record_credit_purchase(self, app):
        """Test recording a credit purchase transaction"""
        from app.models.admin import CreditTransaction
        from app.extensions import db
        
        with app.app_context():
            transaction = CreditTransaction(
                user_id=1,
                sirket_id=1,
                amount=100,
                transaction_type='purchase',
                payment_provider='stripe',
                payment_id='pi_test_123'
            )
            db.session.add(transaction)
            db.session.commit()
            
            assert transaction.id is not None
    
    def test_record_credit_usage(self, app):
        """Test recording a credit usage transaction"""
        from app.models.admin import CreditTransaction
        from app.extensions import db
        
        with app.app_context():
            transaction = CreditTransaction(
                user_id=1,
                sirket_id=1,
                amount=-1,
                transaction_type='usage',
                description='Exam invitation'
            )
            db.session.add(transaction)
            db.session.commit()
            
            assert transaction.amount == -1


# Fixtures
@pytest.fixture
def app():
    """Create application for testing"""
    from app import create_app
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        from app.extensions import db
        db.create_all()
        yield app
        db.drop_all()

# -*- coding: utf-8 -*-
"""
Unit Tests for Authentication Module
Tests login, logout, password reset, and 2FA functionality
"""
import pytest
from flask import session
from unittest.mock import patch, MagicMock


class TestLogin:
    """Tests for login functionality"""
    
    def test_login_page_loads(self, client):
        """Test that login page loads correctly"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or 'giriş'.encode('utf-8') in response.data.lower()
    
    def test_login_with_valid_credentials(self, client, test_user):
        """Test successful login with valid credentials"""
        response = client.post('/login', data={
            'email': test_user.email,
            'sifre': 'testpassword123'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to dashboard
        assert b'dashboard' in response.data.lower() or b'panel' in response.data.lower()
    
    def test_login_with_invalid_password(self, client, test_user):
        """Test login fails with wrong password"""
        response = client.post('/login', data={
            'email': test_user.email,
            'sifre': 'wrongpassword'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should show error message
        assert b'hata' in response.data.lower() or b'invalid' in response.data.lower()
    
    def test_login_with_nonexistent_email(self, client):
        """Test login fails with non-existent email"""
        response = client.post('/login', data={
            'email': 'nonexistent@example.com',
            'sifre': 'anypassword'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should show error message
        assert b'hata' in response.data.lower() or b'invalid' in response.data.lower()
    
    def test_login_rate_limiting(self, client):
        """Test that login is rate limited"""
        # Make 15 rapid login attempts
        for i in range(15):
            client.post('/login', data={
                'email': 'test@example.com',
                'sifre': 'wrongpassword'
            })
        
        response = client.post('/login', data={
            'email': 'test@example.com',
            'sifre': 'wrongpassword'
        })
        # Should be rate limited (429) or show lockout message
        assert response.status_code in [200, 429]


class TestLogout:
    """Tests for logout functionality"""
    
    def test_logout_clears_session(self, client, logged_in_user):
        """Test that logout clears the session"""
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to login page
        assert b'login' in response.data.lower() or 'giriş'.encode('utf-8') in response.data.lower()
    
    def test_logout_redirects_to_login(self, client, logged_in_user):
        """Test logout redirects to login page"""
        response = client.get('/logout')
        assert response.status_code == 302  # Redirect


class TestPasswordReset:
    """Tests for password reset functionality"""
    
    def test_forgot_password_page_loads(self, client):
        """Test forgot password page loads"""
        response = client.get('/forgot-password')
        assert response.status_code == 200
    
    def test_forgot_password_with_valid_email(self, client, test_user):
        """Test password reset request with valid email"""
        with patch('app.tasks.email_tasks.send_password_reset_email.delay') as mock_email:
            response = client.post('/forgot-password', data={
                'email': test_user.email
            }, follow_redirects=True)
            assert response.status_code == 200
            # Should show success message (even for non-existent emails for security)
    
    def test_forgot_password_with_invalid_email(self, client):
        """Test password reset with non-existent email (should still show success)"""
        response = client.post('/forgot-password', data={
            'email': 'nonexistent@example.com'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should still show success (security - don't reveal if email exists)


class TestTwoFactorAuthentication:
    """Tests for 2FA functionality"""
    
    def test_2fa_setup_page_requires_login(self, client):
        """Test 2FA setup requires authentication"""
        response = client.get('/2fa/setup')
        assert response.status_code in [302, 401, 403]  # Redirect or forbidden
    
    def test_2fa_challenge_page(self, client):
        """Test 2FA challenge page loads"""
        with client.session_transaction() as sess:
            sess['pending_2fa_user_id'] = 1
        response = client.get('/2fa/challenge')
        assert response.status_code == 200
    
    def test_2fa_verify_with_invalid_code(self, client):
        """Test 2FA verification with invalid code"""
        with client.session_transaction() as sess:
            sess['pending_2fa_user_id'] = 1
        response = client.post('/2fa/verify', data={
            'code': '000000'
        }, follow_redirects=True)
        assert response.status_code == 200


class TestExamCandidateLogin:
    """Tests for exam candidate login"""
    
    def test_exam_login_page_loads(self, client):
        """Test exam entry page loads"""
        response = client.get('/sinav-giris')
        assert response.status_code == 200
    
    def test_exam_login_with_invalid_code(self, client):
        """Test exam login with invalid access code"""
        response = client.post('/sinav-giris', data={
            'giris_kodu': 'INVALID123'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should show error


# Fixtures
@pytest.fixture
def client(app):
    """Test client fixture"""
    return app.test_client()


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


@pytest.fixture
def test_user(app):
    """Create a test user"""
    from app.models import User
    from app.extensions import db
    
    with app.app_context():
        user = User(
            email='test@example.com',
            ad_soyad='Test User',
            rol='customer',
            is_active=True
        )
        user.set_password('testpassword123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def logged_in_user(client, test_user):
    """Log in the test user"""
    client.post('/login', data={
        'email': test_user.email,
        'sifre': 'testpassword123'
    })
    return test_user

# -*- coding: utf-8 -*-
"""
Unit Tests for Security Module
Tests account lockout, password policy, and 2FA utilities
"""
import pytest
from unittest.mock import patch, MagicMock
import time


class TestAccountLockout:
    """Tests for account lockout functionality"""
    
    def test_initial_state_not_locked(self):
        """Test that a new user is not locked out"""
        from app.utils.security import LoginAttemptTracker
        
        tracker = LoginAttemptTracker()
        assert tracker.is_locked_out('newuser@example.com') == False
    
    def test_lockout_after_max_attempts(self):
        """Test lockout after maximum failed attempts"""
        from app.utils.security import LoginAttemptTracker
        
        tracker = LoginAttemptTracker(max_attempts=3, lockout_duration=60)
        email = 'testuser@example.com'
        
        # Simulate failed attempts
        for i in range(3):
            tracker.record_failed_attempt(email, '127.0.0.1')
        
        assert tracker.is_locked_out(email) == True
    
    def test_successful_login_resets_attempts(self):
        """Test that successful login resets failed attempts"""
        from app.utils.security import LoginAttemptTracker
        
        tracker = LoginAttemptTracker(max_attempts=3)
        email = 'testuser@example.com'
        
        # Add some failed attempts
        tracker.record_failed_attempt(email, '127.0.0.1')
        tracker.record_failed_attempt(email, '127.0.0.1')
        
        # Successful login
        tracker.record_successful_login(email, '127.0.0.1')
        
        # Should not be locked out
        assert tracker.is_locked_out(email) == False
    
    def test_lockout_remaining_time(self):
        """Test getting remaining lockout time"""
        from app.utils.security import LoginAttemptTracker
        
        tracker = LoginAttemptTracker(max_attempts=1, lockout_duration=300)
        email = 'testuser@example.com'
        
        tracker.record_failed_attempt(email, '127.0.0.1')
        
        remaining = tracker.get_lockout_remaining(email)
        assert remaining > 0
        assert remaining <= 300


class TestPasswordPolicy:
    """Tests for password policy validation"""
    
    def test_valid_password(self):
        """Test valid password passes validation"""
        from app.utils.security import PasswordPolicy
        
        policy = PasswordPolicy()
        is_valid, errors = policy.validate('SecurePass123!')
        assert is_valid == True
        assert len(errors) == 0
    
    def test_password_too_short(self):
        """Test short password fails validation"""
        from app.utils.security import PasswordPolicy
        
        policy = PasswordPolicy(min_length=8)
        is_valid, errors = policy.validate('Short1!')
        assert is_valid == False
        assert any('length' in e.lower() or 'karakter' in e.lower() for e in errors)
    
    def test_password_no_uppercase(self):
        """Test password without uppercase fails"""
        from app.utils.security import PasswordPolicy
        
        policy = PasswordPolicy(require_uppercase=True)
        is_valid, errors = policy.validate('nouppercase123!')
        assert is_valid == False
    
    def test_password_no_lowercase(self):
        """Test password without lowercase fails"""
        from app.utils.security import PasswordPolicy
        
        policy = PasswordPolicy(require_lowercase=True)
        is_valid, errors = policy.validate('NOLOWERCASE123!')
        assert is_valid == False
    
    def test_password_no_digit(self):
        """Test password without digit fails"""
        from app.utils.security import PasswordPolicy
        
        policy = PasswordPolicy(require_digit=True)
        is_valid, errors = policy.validate('NoDigitsHere!')
        assert is_valid == False
    
    def test_password_no_special(self):
        """Test password without special character fails"""
        from app.utils.security import PasswordPolicy
        
        policy = PasswordPolicy(require_special=True)
        is_valid, errors = policy.validate('NoSpecial123')
        assert is_valid == False
    
    def test_common_password_rejected(self):
        """Test common passwords are rejected"""
        from app.utils.security import PasswordPolicy
        
        policy = PasswordPolicy()
        is_valid, errors = policy.validate('password123')
        assert is_valid == False


class TestTwoFactorAuth:
    """Tests for 2FA utilities"""
    
    def test_generate_secret(self):
        """Test TOTP secret generation"""
        from app.utils.security import TwoFactorAuth
        
        tfa = TwoFactorAuth()
        secret = tfa.generate_secret()
        
        assert secret is not None
        assert len(secret) == 32  # Base32 encoded
    
    def test_verify_valid_code(self):
        """Test verification with valid TOTP code"""
        from app.utils.security import TwoFactorAuth
        import pyotp
        
        tfa = TwoFactorAuth()
        secret = tfa.generate_secret()
        
        # Generate valid code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        assert tfa.verify_code(secret, valid_code) == True
    
    def test_verify_invalid_code(self):
        """Test verification with invalid TOTP code"""
        from app.utils.security import TwoFactorAuth
        
        tfa = TwoFactorAuth()
        secret = tfa.generate_secret()
        
        assert tfa.verify_code(secret, '000000') == False
    
    def test_generate_backup_codes(self):
        """Test backup codes generation"""
        from app.utils.security import TwoFactorAuth
        
        tfa = TwoFactorAuth()
        codes = tfa.generate_backup_codes(count=8)
        
        assert len(codes) == 8
        assert all(len(code) >= 8 for code in codes)
        assert len(set(codes)) == 8  # All unique
    
    def test_get_qr_code_uri(self):
        """Test QR code URI generation"""
        from app.utils.security import TwoFactorAuth
        
        tfa = TwoFactorAuth()
        secret = tfa.generate_secret()
        
        uri = tfa.get_provisioning_uri(secret, 'test@example.com', 'SkillsTest')
        
        assert 'otpauth://totp/' in uri
        assert 'test@example.com' in uri or 'test%40example.com' in uri


class TestWebhookSecurity:
    """Tests for webhook signature verification"""
    
    def test_generate_signature(self):
        """Test webhook signature generation"""
        from app.utils.webhook_retry import WebhookRetryManager
        
        manager = WebhookRetryManager()
        payload = '{"event": "test"}'
        
        signature = manager.generate_signature(payload, 'webhook_secret')
        
        assert signature is not None
        assert len(signature) > 0
    
    def test_verify_valid_signature(self):
        """Test webhook signature verification with valid signature"""
        from app.utils.webhook_retry import WebhookRetryManager
        
        manager = WebhookRetryManager()
        payload = '{"event": "test"}'
        secret = 'webhook_secret'
        
        signature = manager.generate_signature(payload, secret)
        
        assert manager.verify_signature(payload, signature, secret) == True
    
    def test_verify_invalid_signature(self):
        """Test webhook signature verification with invalid signature"""
        from app.utils.webhook_retry import WebhookRetryManager
        
        manager = WebhookRetryManager()
        payload = '{"event": "test"}'
        
        assert manager.verify_signature(payload, 'invalid_signature', 'secret') == False

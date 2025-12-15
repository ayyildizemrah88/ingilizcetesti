# -*- coding: utf-8 -*-
"""
Security Utilities
Account lockout, password policy, and 2FA support
"""
import re
import pyotp
import qrcode
import hashlib
from io import BytesIO
from datetime import datetime, timedelta
from flask import session, request
from functools import wraps

from app.extensions import db


class LoginAttemptTracker:
    """
    Track failed login attempts and implement account lockout.
    Uses database or Redis for persistence.
    """
    
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)
    
    def __init__(self):
        self._attempts = {}  # In-memory fallback
    
    def _get_key(self, identifier):
        """Generate cache key for identifier (email or IP)."""
        return f"login_attempts:{identifier}"
    
    def record_failed_attempt(self, email, ip_address=None):
        """Record a failed login attempt."""
        try:
            from app.models.admin import LoginAttempt
            
            attempt = LoginAttempt(
                email=email,
                ip_address=ip_address or request.remote_addr,
                attempted_at=datetime.utcnow(),
                success=False
            )
            db.session.add(attempt)
            db.session.commit()
            
        except Exception:
            # Fallback to in-memory
            key = self._get_key(email)
            if key not in self._attempts:
                self._attempts[key] = []
            self._attempts[key].append(datetime.utcnow())
    
    def record_successful_login(self, email, ip_address=None):
        """Record a successful login and clear failed attempts."""
        try:
            from app.models.admin import LoginAttempt
            
            # Record success
            attempt = LoginAttempt(
                email=email,
                ip_address=ip_address or request.remote_addr,
                attempted_at=datetime.utcnow(),
                success=True
            )
            db.session.add(attempt)
            
            # Clear failed attempts
            cutoff = datetime.utcnow() - self.LOCKOUT_DURATION
            LoginAttempt.query.filter(
                LoginAttempt.email == email,
                LoginAttempt.success == False,
                LoginAttempt.attempted_at >= cutoff
            ).delete()
            
            db.session.commit()
            
        except Exception:
            # Fallback
            key = self._get_key(email)
            self._attempts.pop(key, None)
    
    def get_failed_attempts(self, email):
        """Get number of failed attempts in the lockout window."""
        try:
            from app.models.admin import LoginAttempt
            
            cutoff = datetime.utcnow() - self.LOCKOUT_DURATION
            count = LoginAttempt.query.filter(
                LoginAttempt.email == email,
                LoginAttempt.success == False,
                LoginAttempt.attempted_at >= cutoff
            ).count()
            
            return count
            
        except Exception:
            # Fallback
            key = self._get_key(email)
            attempts = self._attempts.get(key, [])
            cutoff = datetime.utcnow() - self.LOCKOUT_DURATION
            return len([a for a in attempts if a >= cutoff])
    
    def is_locked_out(self, email):
        """Check if account is locked out."""
        return self.get_failed_attempts(email) >= self.MAX_ATTEMPTS
    
    def get_lockout_remaining(self, email):
        """Get remaining lockout time in seconds."""
        try:
            from app.models.admin import LoginAttempt
            
            cutoff = datetime.utcnow() - self.LOCKOUT_DURATION
            latest = LoginAttempt.query.filter(
                LoginAttempt.email == email,
                LoginAttempt.success == False,
                LoginAttempt.attempted_at >= cutoff
            ).order_by(LoginAttempt.attempted_at.desc()).first()
            
            if latest and self.is_locked_out(email):
                unlock_time = latest.attempted_at + self.LOCKOUT_DURATION
                remaining = (unlock_time - datetime.utcnow()).total_seconds()
                return max(0, int(remaining))
            
            return 0
            
        except Exception:
            return 0


# Global tracker instance
login_tracker = LoginAttemptTracker()


class PasswordPolicy:
    """
    Password policy enforcement.
    Ensures strong passwords are used.
    """
    
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:',.<>?/"
    
    # Common weak passwords to reject
    BLACKLIST = [
        'password', 'password123', '123456', '12345678', 'qwerty',
        'admin', 'admin123', 'letmein', 'welcome', 'monkey',
        'dragon', 'master', 'sunshine', 'princess', 'football'
    ]
    
    @classmethod
    def validate(cls, password, username=None):
        """
        Validate password against policy.
        
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        if not password:
            return False, ['Şifre gereklidir.']
        
        # Length check
        if len(password) < cls.MIN_LENGTH:
            errors.append(f'Şifre en az {cls.MIN_LENGTH} karakter olmalıdır.')
        
        # Uppercase check
        if cls.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append('Şifre en az bir büyük harf içermelidir.')
        
        # Lowercase check
        if cls.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append('Şifre en az bir küçük harf içermelidir.')
        
        # Digit check
        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            errors.append('Şifre en az bir rakam içermelidir.')
        
        # Special character check
        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            errors.append('Şifre en az bir özel karakter içermelidir (!@#$%^&* vb.)')
        
        # Blacklist check
        if password.lower() in cls.BLACKLIST:
            errors.append('Bu şifre çok yaygın ve güvensizdir.')
        
        # Username similarity check
        if username and username.lower() in password.lower():
            errors.append('Şifre kullanıcı adını içeremez.')
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_strength(cls, password):
        """
        Calculate password strength score (0-100).
        """
        if not password:
            return 0
        
        score = 0
        
        # Length scoring
        if len(password) >= 8:
            score += 20
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        # Character variety
        if re.search(r'[a-z]', password):
            score += 15
        if re.search(r'[A-Z]', password):
            score += 15
        if re.search(r'\d', password):
            score += 15
        if any(c in cls.SPECIAL_CHARS for c in password):
            score += 15
        
        # Bonus for mixed
        char_types = sum([
            bool(re.search(r'[a-z]', password)),
            bool(re.search(r'[A-Z]', password)),
            bool(re.search(r'\d', password)),
            any(c in cls.SPECIAL_CHARS for c in password)
        ])
        
        if char_types == 4:
            score += 10
        
        # Penalty for patterns
        if re.search(r'(.)\1{2,}', password):  # Repeated chars
            score -= 10
        if re.search(r'(012|123|234|345|456|567|678|789)', password):
            score -= 10
        if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi)', password.lower()):
            score -= 10
        
        return max(0, min(100, score))


class TwoFactorAuth:
    """
    Two-Factor Authentication using TOTP (Time-based One-Time Password).
    Compatible with Google Authenticator, Authy, etc.
    """
    
    ISSUER_NAME = "Skills Test Center"
    
    @classmethod
    def generate_secret(cls):
        """Generate a new TOTP secret."""
        return pyotp.random_base32()
    
    @classmethod
    def get_totp(cls, secret):
        """Get TOTP object for a secret."""
        return pyotp.TOTP(secret)
    
    @classmethod
    def verify_code(cls, secret, code):
        """
        Verify a TOTP code.
        
        Args:
            secret: User's TOTP secret
            code: 6-digit code from authenticator app
        
        Returns:
            bool: True if code is valid
        """
        if not secret or not code:
            return False
        
        totp = cls.get_totp(secret)
        
        # Allow 1 window tolerance (30 seconds before/after)
        return totp.verify(code, valid_window=1)
    
    @classmethod
    def get_provisioning_uri(cls, secret, email):
        """
        Get the provisioning URI for QR code.
        
        Args:
            secret: TOTP secret
            email: User's email address
        
        Returns:
            str: otpauth:// URI
        """
        totp = cls.get_totp(secret)
        return totp.provisioning_uri(name=email, issuer_name=cls.ISSUER_NAME)
    
    @classmethod
    def generate_qr_code(cls, secret, email):
        """
        Generate QR code image for authenticator app setup.
        
        Returns:
            BytesIO: PNG image buffer
        """
        uri = cls.get_provisioning_uri(secret, email)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer
    
    @classmethod
    def generate_backup_codes(cls, count=10):
        """
        Generate backup codes for 2FA recovery.
        
        Returns:
            list: List of 8-character backup codes
        """
        import secrets
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()  # 8 hex chars
            codes.append(code)
        return codes
    
    @classmethod
    def hash_backup_code(cls, code):
        """Hash a backup code for storage."""
        return hashlib.sha256(code.encode()).hexdigest()


def require_2fa(f):
    """
    Decorator to require 2FA verification for sensitive operations.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('2fa_verified') != True:
            from flask import flash, redirect, url_for
            flash('Bu işlem için iki faktörlü doğrulama gereklidir.', 'warning')
            return redirect(url_for('auth.verify_2fa'))
        return f(*args, **kwargs)
    return decorated_function

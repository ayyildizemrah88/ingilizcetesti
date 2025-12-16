# -*- coding: utf-8 -*-
"""
Redis Login Tracker
High-performance login attempt tracking using Redis
Prevents DoS attacks on database during brute force attempts
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Configuration
MAX_FAILED_ATTEMPTS = int(os.getenv('MAX_FAILED_ATTEMPTS', '5'))
LOCKOUT_DURATION_MINUTES = int(os.getenv('LOCKOUT_DURATION_MINUTES', '30'))
ATTEMPT_WINDOW_MINUTES = int(os.getenv('ATTEMPT_WINDOW_MINUTES', '15'))


class RedisLoginTracker:
    """
    Redis-based login attempt tracker.
    
    Benefits over database tracking:
    - No database writes during brute force attacks
    - Automatic expiration of old attempts
    - Distributed across multiple app instances
    - Much higher throughput for tracking
    
    Usage:
        tracker = RedisLoginTracker()
        
        # On failed login
        if not tracker.is_locked(email):
            tracker.record_failed_attempt(email, ip)
        
        # On successful login
        tracker.clear_attempts(email)
    """
    
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self._redis = None
        self.max_attempts = MAX_FAILED_ATTEMPTS
        self.lockout_duration = timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        self.attempt_window = timedelta(minutes=ATTEMPT_WINDOW_MINUTES)
    
    @property
    def redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(self.redis_url)
            except ImportError:
                logger.warning("Redis not available for login tracking")
                return None
        return self._redis
    
    def _get_attempts_key(self, identifier: str) -> str:
        """Get Redis key for tracking attempts."""
        return f"login:attempts:{identifier}"
    
    def _get_lockout_key(self, identifier: str) -> str:
        """Get Redis key for lockout status."""
        return f"login:locked:{identifier}"
    
    def record_failed_attempt(self, email: str, ip_address: str = None) -> Tuple[int, bool]:
        """
        Record a failed login attempt.
        
        Args:
            email: User email
            ip_address: Client IP address
            
        Returns:
            Tuple of (attempt_count, is_now_locked)
        """
        if not self.redis:
            return self._fallback_record(email)
        
        try:
            # Use both email and IP for tracking
            keys = [self._get_attempts_key(email)]
            if ip_address:
                keys.append(self._get_attempts_key(f"ip:{ip_address}"))
            
            pipe = self.redis.pipeline()
            
            for key in keys:
                # Increment attempt counter
                pipe.incr(key)
                # Set expiration (attempts expire after window)
                pipe.expire(key, int(self.attempt_window.total_seconds()))
            
            results = pipe.execute()
            
            # Get the highest attempt count
            attempt_count = max(results[0], results[2] if ip_address else 0)
            
            # Check if should lock out
            if attempt_count >= self.max_attempts:
                self._lock_account(email, ip_address)
                return attempt_count, True
            
            logger.info(f"Failed login attempt {attempt_count}/{self.max_attempts} for {email}")
            return attempt_count, False
            
        except Exception as e:
            logger.error(f"Redis error in record_failed_attempt: {e}")
            return self._fallback_record(email)
    
    def _lock_account(self, email: str, ip_address: str = None):
        """Lock account after too many failed attempts."""
        if not self.redis:
            return
        
        try:
            lockout_seconds = int(self.lockout_duration.total_seconds())
            
            # Lock by email
            self.redis.setex(
                self._get_lockout_key(email),
                lockout_seconds,
                datetime.utcnow().isoformat()
            )
            
            # Also lock by IP if provided
            if ip_address:
                self.redis.setex(
                    self._get_lockout_key(f"ip:{ip_address}"),
                    lockout_seconds,
                    datetime.utcnow().isoformat()
                )
            
            logger.warning(f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes: {email}")
            
        except Exception as e:
            logger.error(f"Redis error in lock_account: {e}")
    
    def is_locked(self, email: str, ip_address: str = None) -> Tuple[bool, Optional[int]]:
        """
        Check if account is locked.
        
        Args:
            email: User email
            ip_address: Client IP address
            
        Returns:
            Tuple of (is_locked, remaining_seconds)
        """
        if not self.redis:
            return False, None
        
        try:
            # Check email lockout
            email_ttl = self.redis.ttl(self._get_lockout_key(email))
            if email_ttl > 0:
                return True, email_ttl
            
            # Check IP lockout
            if ip_address:
                ip_ttl = self.redis.ttl(self._get_lockout_key(f"ip:{ip_address}"))
                if ip_ttl > 0:
                    return True, ip_ttl
            
            return False, None
            
        except Exception as e:
            logger.error(f"Redis error in is_locked: {e}")
            return False, None
    
    def get_remaining_attempts(self, email: str) -> int:
        """Get remaining login attempts before lockout."""
        if not self.redis:
            return self.max_attempts
        
        try:
            attempts = self.redis.get(self._get_attempts_key(email))
            if attempts:
                return max(0, self.max_attempts - int(attempts))
            return self.max_attempts
            
        except Exception:
            return self.max_attempts
    
    def clear_attempts(self, email: str, ip_address: str = None):
        """Clear failed attempts after successful login."""
        if not self.redis:
            return
        
        try:
            keys = [
                self._get_attempts_key(email),
                self._get_lockout_key(email)
            ]
            
            if ip_address:
                keys.extend([
                    self._get_attempts_key(f"ip:{ip_address}"),
                    self._get_lockout_key(f"ip:{ip_address}")
                ])
            
            self.redis.delete(*keys)
            logger.info(f"Cleared login attempts for {email}")
            
        except Exception as e:
            logger.error(f"Redis error in clear_attempts: {e}")
    
    def unlock_account(self, email: str, ip_address: str = None):
        """Manually unlock an account (admin function)."""
        self.clear_attempts(email, ip_address)
        logger.info(f"Account unlocked by admin: {email}")
    
    def _fallback_record(self, email: str) -> Tuple[int, bool]:
        """Fallback when Redis is unavailable."""
        # Log but allow login (fail open)
        logger.warning(f"Redis unavailable - login tracking disabled for {email}")
        return 0, False
    
    def get_lockout_stats(self) -> dict:
        """Get current lockout statistics (admin function)."""
        if not self.redis:
            return {'error': 'Redis not available'}
        
        try:
            # Count locked accounts
            locked_emails = len(list(self.redis.scan_iter("login:locked:*")))
            locked_ips = len(list(self.redis.scan_iter("login:locked:ip:*")))
            
            return {
                'locked_accounts': locked_emails,
                'locked_ips': locked_ips,
                'max_attempts': self.max_attempts,
                'lockout_duration_minutes': LOCKOUT_DURATION_MINUTES
            }
            
        except Exception as e:
            return {'error': str(e)}


# Helper functions for easy use
_tracker = None

def get_login_tracker() -> RedisLoginTracker:
    """Get global login tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = RedisLoginTracker()
    return _tracker


def record_failed_login(email: str, ip_address: str = None) -> Tuple[int, bool]:
    """Record failed login attempt."""
    return get_login_tracker().record_failed_attempt(email, ip_address)


def record_successful_login(email: str, ip_address: str = None):
    """Record successful login and clear attempts."""
    get_login_tracker().clear_attempts(email, ip_address)


def is_account_locked(email: str, ip_address: str = None) -> Tuple[bool, Optional[int]]:
    """Check if account is locked."""
    return get_login_tracker().is_locked(email, ip_address)


def get_remaining_attempts(email: str) -> int:
    """Get remaining login attempts."""
    return get_login_tracker().get_remaining_attempts(email)

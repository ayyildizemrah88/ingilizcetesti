# -*- coding: utf-8 -*-
"""
AI Rate Limiter
Protects expensive AI API calls (Gemini, OpenAI) from abuse.
Uses Redis for distributed rate limiting.
"""
import os
import time
import logging
from functools import wraps
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Rate limit configurations for AI services
AI_RATE_LIMITS = {
    'speaking_evaluation': {
        'per_minute': 5,
        'per_hour': 30,
        'per_day': 100
    },
    'writing_evaluation': {
        'per_minute': 10,
        'per_hour': 60,
        'per_day': 200
    },
    'transcription': {
        'per_minute': 5,
        'per_hour': 50,
        'per_day': 200
    }
}


class AIRateLimiter:
    """
    Redis-based rate limiter for AI API calls.
    
    Usage:
        limiter = AIRateLimiter()
        if not limiter.check_limit('speaking_evaluation', user_id='user123'):
            raise RateLimitExceeded("Too many requests")
        
        # Make AI API call
        result = evaluate_speaking(...)
        limiter.record_usage('speaking_evaluation', user_id='user123')
    """
    
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self._redis = None
    
    @property
    def redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(self.redis_url)
            except ImportError:
                logger.warning("Redis not available for AI rate limiting")
                return None
        return self._redis
    
    def _get_keys(self, service: str, user_id: str) -> dict:
        """Generate Redis keys for different time windows."""
        return {
            'minute': f"ai_limit:{service}:{user_id}:minute",
            'hour': f"ai_limit:{service}:{user_id}:hour",
            'day': f"ai_limit:{service}:{user_id}:day"
        }
    
    def check_limit(self, service: str, user_id: str = 'global') -> Tuple[bool, Optional[str]]:
        """
        Check if rate limit is exceeded.
        
        Args:
            service: AI service name (speaking_evaluation, writing_evaluation, etc.)
            user_id: User identifier for per-user limiting
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        if not self.redis:
            # Redis not available, allow request (fail open)
            return True, None
        
        limits = AI_RATE_LIMITS.get(service, {})
        if not limits:
            return True, None
        
        keys = self._get_keys(service, user_id)
        
        try:
            # Check minute limit
            minute_count = self.redis.get(keys['minute'])
            if minute_count and int(minute_count) >= limits.get('per_minute', 999):
                return False, f"Rate limit exceeded. Maximum {limits['per_minute']} requests per minute."
            
            # Check hour limit
            hour_count = self.redis.get(keys['hour'])
            if hour_count and int(hour_count) >= limits.get('per_hour', 999):
                return False, f"Rate limit exceeded. Maximum {limits['per_hour']} requests per hour."
            
            # Check day limit
            day_count = self.redis.get(keys['day'])
            if day_count and int(day_count) >= limits.get('per_day', 999):
                return False, f"Daily limit exceeded. Maximum {limits['per_day']} requests per day."
            
            return True, None
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True, None  # Fail open
    
    def record_usage(self, service: str, user_id: str = 'global') -> None:
        """
        Record API usage for rate limiting.
        
        Args:
            service: AI service name
            user_id: User identifier
        """
        if not self.redis:
            return
        
        keys = self._get_keys(service, user_id)
        
        try:
            pipe = self.redis.pipeline()
            
            # Increment minute counter (expires in 60 seconds)
            pipe.incr(keys['minute'])
            pipe.expire(keys['minute'], 60)
            
            # Increment hour counter (expires in 3600 seconds)
            pipe.incr(keys['hour'])
            pipe.expire(keys['hour'], 3600)
            
            # Increment day counter (expires in 86400 seconds)
            pipe.incr(keys['day'])
            pipe.expire(keys['day'], 86400)
            
            pipe.execute()
            
        except Exception as e:
            logger.error(f"Failed to record AI usage: {e}")
    
    def get_remaining(self, service: str, user_id: str = 'global') -> dict:
        """
        Get remaining quota for a service.
        
        Returns:
            dict with remaining counts for each time window
        """
        if not self.redis:
            return {'minute': 999, 'hour': 999, 'day': 999}
        
        limits = AI_RATE_LIMITS.get(service, {})
        keys = self._get_keys(service, user_id)
        
        try:
            pipe = self.redis.pipeline()
            pipe.get(keys['minute'])
            pipe.get(keys['hour'])
            pipe.get(keys['day'])
            results = pipe.execute()
            
            return {
                'minute': limits.get('per_minute', 999) - int(results[0] or 0),
                'hour': limits.get('per_hour', 999) - int(results[1] or 0),
                'day': limits.get('per_day', 999) - int(results[2] or 0)
            }
            
        except Exception:
            return {'minute': 999, 'hour': 999, 'day': 999}
    
    def reset_limits(self, service: str, user_id: str = 'global') -> None:
        """Reset rate limits for a user (admin function)."""
        if not self.redis:
            return
        
        keys = self._get_keys(service, user_id)
        
        try:
            self.redis.delete(keys['minute'], keys['hour'], keys['day'])
        except Exception as e:
            logger.error(f"Failed to reset limits: {e}")


# Decorator for rate-limited AI tasks
def ai_rate_limited(service: str):
    """
    Decorator to add rate limiting to AI-powered functions.
    
    Usage:
        @ai_rate_limited('speaking_evaluation')
        def evaluate_speaking(user_id, recording_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user_id from kwargs or use global
            user_id = kwargs.get('user_id', kwargs.get('candidate_id', 'global'))
            
            limiter = AIRateLimiter()
            allowed, error_msg = limiter.check_limit(service, str(user_id))
            
            if not allowed:
                logger.warning(f"AI rate limit exceeded for {service}: {user_id}")
                raise Exception(error_msg)
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Record usage after successful call
            limiter.record_usage(service, str(user_id))
            
            return result
        
        return wrapper
    return decorator


# Global limiter instance
ai_limiter = AIRateLimiter()

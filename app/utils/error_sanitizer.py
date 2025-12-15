# -*- coding: utf-8 -*-
"""
Error Sanitizer
Ensures user-facing error messages don't contain sensitive technical details.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Patterns that indicate sensitive information
SENSITIVE_PATTERNS = [
    r'Traceback \(most recent call last\):',
    r'File ".*", line \d+',
    r'Exception:.*',
    r'Error:.*',
    r'api[_-]?key[s]?\s*[:=].*',
    r'secret[_-]?key\s*[:=].*',
    r'password\s*[:=].*',
    r'token\s*[:=].*',
    r'bearer\s+[a-zA-Z0-9._-]+',
    r'sk-[a-zA-Z0-9]+',  # OpenAI API keys
    r'AIza[a-zA-Z0-9_-]+',  # Google API keys
    r'/home/.*',
    r'C:\\\\.*',
    r'\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}',  # IP addresses
]

# User-friendly error messages
USER_FRIENDLY_MESSAGES = {
    'database': 'Bir veritabanı hatası oluştu. Lütfen daha sonra tekrar deneyin.',
    'api': 'Dış servis geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin.',
    'validation': 'Girdiğiniz bilgilerde bir hata var. Lütfen kontrol edin.',
    'permission': 'Bu işlemi gerçekleştirmek için yetkiniz yok.',
    'not_found': 'Aradığınız kaynak bulunamadı.',
    'rate_limit': 'Çok fazla istek gönderdiniz. Lütfen biraz bekleyin.',
    'timeout': 'İşlem zaman aşımına uğradı. Lütfen tekrar deneyin.',
    'default': 'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.'
}


def sanitize_error(error: Exception, context: str = 'default') -> str:
    """
    Sanitize an error message for user display.
    
    Args:
        error: The exception object
        context: Context hint for selecting appropriate message
        
    Returns:
        User-friendly error message
    """
    error_str = str(error).lower()
    
    # Determine error type and return appropriate message
    if 'connection' in error_str or 'database' in error_str or 'sql' in error_str:
        return USER_FRIENDLY_MESSAGES['database']
    
    if 'api' in error_str or 'request' in error_str or 'timeout' in error_str:
        return USER_FRIENDLY_MESSAGES['api']
    
    if 'permission' in error_str or 'forbidden' in error_str or 'unauthorized' in error_str:
        return USER_FRIENDLY_MESSAGES['permission']
    
    if 'not found' in error_str or '404' in error_str:
        return USER_FRIENDLY_MESSAGES['not_found']
    
    if 'rate' in error_str or 'limit' in error_str or 'quota' in error_str:
        return USER_FRIENDLY_MESSAGES['rate_limit']
    
    if 'timeout' in error_str:
        return USER_FRIENDLY_MESSAGES['timeout']
    
    # Return context-specific or default message
    return USER_FRIENDLY_MESSAGES.get(context, USER_FRIENDLY_MESSAGES['default'])


def sanitize_message(message: str) -> str:
    """
    Remove sensitive information from a message string.
    
    Args:
        message: The message to sanitize
        
    Returns:
        Sanitized message
    """
    if not message:
        return message
    
    result = message
    
    # Remove patterns that match sensitive info
    for pattern in SENSITIVE_PATTERNS:
        result = re.sub(pattern, '[REDACTED]', result, flags=re.IGNORECASE)
    
    return result


def log_and_sanitize(error: Exception, context: str = 'default', extra: dict = None) -> str:
    """
    Log the full error for debugging but return sanitized message for user.
    
    Args:
        error: The exception object
        context: Context hint for message selection
        extra: Additional context to log
        
    Returns:
        User-friendly error message
    """
    # Log full error for debugging
    logger.error(
        f"Error in {context}: {str(error)}",
        exc_info=True,
        extra=extra or {}
    )
    
    # Return sanitized message for user
    return sanitize_error(error, context)


def get_ai_error_message(error: Exception) -> str:
    """
    Get user-friendly message for AI-related errors.
    
    Args:
        error: The exception from AI service
        
    Returns:
        User-friendly message
    """
    error_str = str(error).lower()
    
    if 'quota' in error_str or 'limit' in error_str:
        return 'AI değerlendirme kotası doldu. Lütfen daha sonra tekrar deneyin.'
    
    if 'key' in error_str or 'auth' in error_str:
        return 'AI servisi geçici olarak kullanılamıyor.'
    
    if 'parse' in error_str or 'json' in error_str:
        return 'AI yanıtı işlenirken bir hata oluştu. Varsayılan değerler kullanılacak.'
    
    if 'timeout' in error_str:
        return 'AI değerlendirmesi zaman aşımına uğradı. Sonuç daha sonra güncellenecek.'
    
    return 'AI değerlendirmesi sırasında bir hata oluştu. Varsayılan değerler kullanılacak.'


class SafeResponse:
    """
    Context manager for safe API responses.
    
    Usage:
        with SafeResponse() as safe:
            result = risky_operation()
            safe.data = result
        
        return jsonify(safe.response)
    """
    
    def __init__(self, default_data: dict = None):
        self.data = default_data or {}
        self.error = None
        self.success = True
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.error = sanitize_error(exc_val)
            self.success = False
            logger.error(f"SafeResponse caught: {exc_val}", exc_info=True)
            return True  # Suppress exception
        return False
    
    @property
    def response(self) -> dict:
        if self.success:
            return {'success': True, 'data': self.data}
        return {'success': False, 'error': self.error}

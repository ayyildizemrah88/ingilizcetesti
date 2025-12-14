# -*- coding: utf-8 -*-
"""
Session and Config Extensions for Skills Test Center
Session timeout handling and extended config
"""
from datetime import timedelta


class ExtendedConfig:
    """Extended configuration with session safety for exams."""
    
    # Session settings - Extended for exam safety
    # Minimum 4 hours to cover longest possible exams (C1/C2 can be 3+ hours)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)
    
    # Remember me duration (for admin users)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    # Session refresh settings
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Security
    SESSION_COOKIE_SECURE = True  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


# Middleware for session timeout warning
SESSION_WARNING_MINUTES = 10  # Warn user 10 minutes before session expires


def session_timeout_check(session, app):
    """
    Check if session is about to expire.
    Returns minutes remaining, or -1 if expired.
    """
    from datetime import datetime
    
    if 'login_time' not in session:
        return -1
    
    try:
        login_time = datetime.fromisoformat(session['login_time'])
        lifetime = app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(hours=2))
        expiry_time = login_time + lifetime
        remaining = expiry_time - datetime.utcnow()
        
        return int(remaining.total_seconds() / 60)
    except:
        return -1


# Export config
EXTENDED_SESSION_CONFIG = {
    'PERMANENT_SESSION_LIFETIME': timedelta(hours=4),
    'REMEMBER_COOKIE_DURATION': timedelta(days=30),
    'REMEMBER_COOKIE_SECURE': True,
    'REMEMBER_COOKIE_HTTPONLY': True,
    'SESSION_REFRESH_EACH_REQUEST': True,
}

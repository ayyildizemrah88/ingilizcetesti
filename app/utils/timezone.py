# -*- coding: utf-8 -*-
"""
Timezone Utilities
Modern datetime handling with proper timezone awareness
Replaces deprecated datetime.utcnow() with timezone-aware alternatives
"""
from datetime import datetime, timezone, timedelta
from typing import Optional


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    This replaces the deprecated datetime.utcnow() method.
    Python 3.12+ will show deprecation warnings for utcnow().
    Python 3.14+ may remove it entirely.
    
    Returns:
        datetime: Current UTC time with timezone info
        
    Example:
        >>> from app.utils.timezone import utc_now
        >>> now = utc_now()
        >>> print(now.tzinfo)  # UTC
    """
    return datetime.now(timezone.utc)


def utc_now_naive() -> datetime:
    """
    Get current UTC time as naive datetime (no timezone info).
    
    Use this for compatibility with existing code that expects
    naive datetime objects (e.g., SQLAlchemy default columns).
    
    Returns:
        datetime: Current UTC time without timezone info
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC.
    
    Args:
        dt: datetime object (naive or aware)
        
    Returns:
        datetime: UTC datetime
    """
    if dt.tzinfo is None:
        # Assume naive datetime is already UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def from_timestamp(ts: float) -> datetime:
    """
    Create a UTC datetime from a Unix timestamp.
    
    Args:
        ts: Unix timestamp (seconds since epoch)
        
    Returns:
        datetime: UTC datetime
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def format_iso(dt: Optional[datetime] = None) -> str:
    """
    Format datetime as ISO 8601 string.
    
    Args:
        dt: datetime object (defaults to current UTC time)
        
    Returns:
        str: ISO formatted string
    """
    if dt is None:
        dt = utc_now()
    return dt.isoformat()


def time_ago(dt: datetime, now: Optional[datetime] = None) -> str:
    """
    Get human-readable time difference.
    
    Args:
        dt: datetime to compare
        now: reference time (defaults to current UTC)
        
    Returns:
        str: Human-readable time difference (e.g., "5 dakika önce")
    """
    if now is None:
        now = utc_now()
    
    # Make both timezone-aware for comparison
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "az önce"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} dakika önce"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} saat önce"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} gün önce"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} hafta önce"
    else:
        months = int(seconds / 2592000)
        return f"{months} ay önce"


# SQLAlchemy column defaults
def default_utc_now():
    """
    Default function for SQLAlchemy DateTime columns.
    
    Usage:
        created_at = db.Column(db.DateTime, default=default_utc_now)
    """
    return utc_now_naive()


# Backwards compatibility alias
get_utc_now = utc_now

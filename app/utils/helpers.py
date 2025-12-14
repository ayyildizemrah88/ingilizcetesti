# -*- coding: utf-8 -*-
"""
Helper Functions - Common utilities
"""
import string
import random
import hashlib
from datetime import datetime


def generate_code(length=8):
    """
    Generate a random alphanumeric code
    
    Args:
        length: Code length (default 8)
    
    Returns:
        Uppercase alphanumeric string
    """
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


def generate_hash(data):
    """
    Generate SHA-256 hash of data
    
    Args:
        data: String to hash
    
    Returns:
        16 character hex string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()[:16]


def format_duration(seconds):
    """
    Format seconds to MM:SS or HH:MM:SS
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string
    """
    if seconds < 0:
        seconds = 0
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def calculate_cefr_level(score):
    """
    Calculate CEFR level from score (0-100)
    
    Args:
        score: Numeric score
    
    Returns:
        CEFR level string (A1-C2)
    """
    if score >= 90:
        return 'C2'
    elif score >= 75:
        return 'C1'
    elif score >= 60:
        return 'B2'
    elif score >= 40:
        return 'B1'
    elif score >= 20:
        return 'A2'
    else:
        return 'A1'


def calculate_ielts_band(score):
    """
    Convert score (0-100) to IELTS band (0-9)
    
    Args:
        score: Numeric score
    
    Returns:
        IELTS band score
    """
    return min(9.0, max(0, score / 100 * 9))


def sanitize_filename(filename):
    """
    Sanitize filename to prevent directory traversal
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    import os
    import re
    
    # Remove path separators
    filename = os.path.basename(filename)
    
    # Remove special characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    return filename


def parse_tags(tags_string):
    """
    Parse comma-separated tags string to list
    
    Args:
        tags_string: Comma-separated tags
    
    Returns:
        List of tags
    """
    if not tags_string:
        return []
    
    tags = [t.strip() for t in tags_string.split(',')]
    return [t for t in tags if t]


def format_datetime(dt, format='%d.%m.%Y %H:%M'):
    """
    Format datetime for Turkish locale
    
    Args:
        dt: datetime object
        format: strftime format string
    
    Returns:
        Formatted string or empty string if dt is None
    """
    if not dt:
        return ''
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    
    return dt.strftime(format)


def truncate_text(text, max_length=100, suffix='...'):
    """
    Truncate text to max length with suffix
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if not text:
        return ''
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def is_valid_email(email):
    """
    Basic email validation
    
    Args:
        email: Email address
    
    Returns:
        Boolean
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_tc_kimlik(tc):
    """
    Validate Turkish ID number (TC Kimlik)
    
    Args:
        tc: 11 digit TC Kimlik number
    
    Returns:
        Boolean
    """
    if not tc or len(tc) != 11 or not tc.isdigit():
        return False
    
    if tc[0] == '0':
        return False
    
    # Checksum validation
    digits = [int(d) for d in tc]
    
    # 10th digit check
    sum_odd = sum(digits[0:9:2])
    sum_even = sum(digits[1:8:2])
    check_10 = (sum_odd * 7 - sum_even) % 10
    
    if check_10 != digits[9]:
        return False
    
    # 11th digit check
    check_11 = sum(digits[0:10]) % 10
    
    return check_11 == digits[10]

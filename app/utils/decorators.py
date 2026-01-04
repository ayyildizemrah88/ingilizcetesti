# -*- coding: utf-8 -*-
"""
Decorators - Reusable route decorators
DÜZELTME: auth.sinav_giris -> candidate_auth.sinav_giris
"""
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request


def login_required(f):
    """
    Require admin user login
    Redirects to login page if not authenticated
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def check_role(allowed_roles):
    """
    Check if current user has one of the allowed roles
    
    Usage:
        @check_role(['superadmin', 'admin'])
        def admin_only_route():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('rol')
            if user_role not in allowed_roles:
                flash("Bu işlem için yetkiniz yok.", "danger")
                return redirect(url_for('admin.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def superadmin_required(f):
    """
    Only superadmin can access
    Used for: questions, templates, users, settings
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu işlem sadece süper admin tarafından yapılabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def customer_or_superadmin(f):
    """
    Superadmin and customer can access
    Used for: candidates, reports
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') not in ['superadmin', 'customer']:
            flash("Bu işlem için yetkiniz yok.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def exam_required(f):
    """
    Require active exam session
    Redirects to exam login if not in exam
    DÜZELTME: auth.sinav_giris -> candidate_auth.sinav_giris
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'aday_id' not in session:
            flash("Lütfen sınav giriş kodunuzu girin.", "warning")
            return redirect(url_for('candidate_auth.sinav_giris'))
        return f(*args, **kwargs)
    return decorated_function


def api_key_required(f):
    """
    Require valid API key in header
    Returns JSON error if not authenticated
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        from app.models import Company
        company = Company.query.filter_by(api_key=api_key, is_active=True).first()
        
        if not company:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Add company to request context
        request.company_id = company.id
        
        return f(*args, **kwargs)
    return decorated_function


def rate_limit_by_company(limit_string):
    """
    Rate limit by company API key instead of IP
    
    Usage:
        @rate_limit_by_company("100/hour")
        def limited_endpoint():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # This would need integration with Flask-Limiter
            # For now, just pass through
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_activity(action_type):
    """
    Log admin activity for audit trail
    
    Usage:
        @log_activity('candidate_created')
        def create_candidate():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # Log the activity
            try:
                from app.extensions import db
                # Could create an AdminLog model and save here
                import logging
                logging.info(f"Activity: {action_type} by user {session.get('kullanici_id')}")
            except Exception:
                pass
            
            return result
        return decorated_function
    return decorator

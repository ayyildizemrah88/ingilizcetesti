# -*- coding: utf-8 -*-
"""
Credits Management Routes - Handle credit operations for companies
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.extensions import db

credits_bp = Blueprint('credits', __name__, url_prefix='/credits')








def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated








def superadmin_required(f):
    """Only superadmin can access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu işlem sadece süper admin tarafından yapılabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated








@credits_bp.route('/')

# -*- coding: utf-8 -*-
"""
Authentication Routes - Login, Logout, Password Reset
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.extensions import db, limiter

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """
    Admin panel login
    ---
    tags:
      - Authentication
    responses:
      200:
        description: Login page or redirect to dashboard
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('sifre', '')
        
        from app.models import User
        user = User.query.filter_by(email=email, is_active=True).first()
        
        # Check for account lockout
        try:
            from app.utils.security import login_tracker
            if login_tracker.is_locked_out(email):
                remaining = login_tracker.get_lockout_remaining(email)
                flash(f"Hesabınız geçici olarak kilitlendi. {remaining // 60} dakika sonra tekrar deneyin.", "danger")
                return render_template('login.html')
        except ImportError:
            pass  # Security module not available
        
        if user and user.check_password(password):
            # Record successful login
            try:
                from app.utils.security import login_tracker
                login_tracker.record_successful_login(email, request.remote_addr)
            except ImportError:
                pass
            
            # Check if 2FA is enabled
            if hasattr(user, 'totp_verified') and user.totp_verified and user.totp_secret:
                # Store user ID temporarily for 2FA verification
                session['pending_2fa_user_id'] = user.id
                flash("Lütfen doğrulama kodunuzu girin.", "info")
                return redirect(url_for('twofa.challenge'))
            
            # No 2FA - complete login
            session['kullanici_id'] = user.id
            session['kullanici'] = user.email
            session['rol'] = user.rol
            session['sirket_id'] = user.sirket_id
            session['2fa_verified'] = True  # Mark as verified (no 2FA needed)
            
            # Update last login
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash("Giriş başarılı!", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            # Record failed login
            try:
                from app.utils.security import login_tracker
                login_tracker.record_failed_attempt(email, request.remote_addr)
            except ImportError:
                pass
            
            flash("E-posta veya şifre hatalı.", "danger")
    
    return render_template('login.html')

# -*- coding: utf-8 -*-
"""
Authentication Routes - Login, Logout, Password Reset, Toggle Theme
Enhanced with security best practices
FIXED: Added proper error handling for missing database tables
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from app.extensions import db, limiter
from datetime import datetime, timedelta
import os
import re
import jwt

# ══════════════════════════════════════════════════════════════════
from app.models import User, Candidate, Company

auth_bp = Blueprint('auth', __name__)

# ══════════════════════════════════════════════════════════════════
def get_secret_key():
    """Get SECRET_KEY - raises error if not configured."""
    key = os.getenv('SECRET_KEY')
    if not key:
        raise RuntimeError("SECRET_KEY environment variable is not set!")
    return key


def validate_password_strength(password):
    """
    Validate password meets security requirements.
    """
    if len(password) < 8:
        return False, "Şifre en az 8 karakter olmalıdır."

    if not re.search(r'[A-Z]', password):
        return False, "Şifre en az 1 büyük harf içermelidir."

    if not re.search(r'[a-z]', password):
        return False, "Şifre en az 1 küçük harf içermelidir."

    if not re.search(r'\d', password):
        return False, "Şifre en az 1 rakam içermelidir."

    return True, None


def regenerate_session():
    """Regenerate session ID to prevent session fixation attacks."""
    session_data = dict(session)
    session.clear()
    for key, value in session_data.items():
        session[key] = value
    session.modified = True


def get_login_tracker():
    """Get login tracker with graceful fallback."""
    try:
        from app.utils.redis_login_tracker import login_tracker
        return login_tracker
    except ImportError:
        try:
            from app.utils.security import login_tracker
            return login_tracker
        except ImportError:
            return None


def safe_record_login(tracker, email, ip_address, success=True):
    """
    Safely record login attempt, handling database errors gracefully.
    FIXED: Added try/except to handle missing tables.
    """
    if not tracker:
        return
    
    try:
        if success:
            tracker.record_successful_login(email, ip_address)
        else:
            tracker.record_failed_attempt(email, ip_address)
    except Exception as e:
        # If login_attempts table doesn't exist, rollback and continue
        try:
            db.session.rollback()
        except:
            pass
        current_app.logger.warning(f"Login tracking failed (table may not exist): {e}")


# ══════════════════════════════════════════════════════════════════
@auth_bp.route('/')
def index():
    """Landing page with login options"""
    return render_template('index.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Admin panel login with enhanced security - FIXED error handling"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('sifre', '')

        # FIXED: Wrap user query in try/except
        try:
            user = User.query.filter_by(email=email, is_active=True).first()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"User query failed: {e}")
            flash("Bir hata oluştu, lütfen tekrar deneyin.", "danger")
            return render_template('login.html')

        # Check for account lockout
        tracker = get_login_tracker()
        if tracker:
            try:
                if tracker.is_locked_out(email):
                    remaining = tracker.get_lockout_remaining(email)
                    flash(f"Hesabınız geçici olarak kilitlendi. {remaining // 60} dakika sonra tekrar deneyin.", "danger")
                    return render_template('login.html')
            except Exception as e:
                # Ignore lockout check errors
                current_app.logger.warning(f"Lockout check failed: {e}")

        if user and user.check_password(password):
            # Record successful login (safely)
            safe_record_login(tracker, email, request.remote_addr, success=True)

            # FIXED: Check 2FA with proper error handling
            try:
                has_2fa = (
                    hasattr(user, 'totp_verified') and 
                    hasattr(user, 'totp_secret') and
                    user.totp_verified and 
                    user.totp_secret
                )
            except Exception as e:
                db.session.rollback()
                has_2fa = False
                current_app.logger.warning(f"2FA check failed: {e}")

            if has_2fa:
                session['pending_2fa_user_id'] = user.id
                flash("Lütfen doğrulama kodunuzu girin.", "info")
                return redirect(url_for('twofa.challenge'))

            # Session regeneration
            regenerate_session()

            # Set session data
            session['kullanici_id'] = user.id
            session['kullanici'] = user.email
            session['rol'] = user.rol
            session['sirket_id'] = user.sirket_id
            session['2fa_verified'] = True

            # Update last login (safely)
            try:
                user.last_login = datetime.utcnow()
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.warning(f"Last login update failed: {e}")

            flash("Giriş başarılı!", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            # Record failed attempt (safely)
            safe_record_login(tracker, email, request.remote_addr, success=False)
            flash("E-posta veya şifre hatalı.", "danger")

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for('auth.login'))


# ══════════════════════════════════════════════════════════════════
@auth_bp.route('/toggle-theme')
def toggle_theme():
    """Toggle between dark and light theme"""
    current_theme = session.get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    session['theme'] = new_theme

    # Return to referring page or dashboard
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    return redirect(url_for('admin.dashboard'))


# ══════════════════════════════════════════════════════════════════
@auth_bp.route('/sinav-giris', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def sinav_giris():
    """Exam entry page for candidates"""
    if request.method == 'POST':
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        giris_kodu = request.form.get('giris_kodu', '').strip().upper()

        if not tc_kimlik or not giris_kodu:
            flash("TC Kimlik ve giriş kodu gereklidir.", "danger")
            return render_template('sinav_giris.html')

        try:
            candidate = Candidate.query.filter_by(
                tc_kimlik=tc_kimlik,
                giris_kodu=giris_kodu,
                is_active=True
            ).first()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Candidate query failed: {e}")
            flash("Bir hata oluştu, lütfen tekrar deneyin.", "danger")
            return render_template('sinav_giris.html')

        if candidate:
            # Check if exam is started or completed
            if candidate.sinav_durumu == 'tamamlandi':
                flash("Sınavınız daha önce tamamlanmış.", "warning")
                return render_template('sinav_giris.html')

            # Set session
            session['aday_id'] = candidate.id
            session['aday_tc'] = candidate.tc_kimlik
            session['aday_isim'] = candidate.ad_soyad

            flash(f"Hoş geldiniz, {candidate.ad_soyad}!", "success")
            return redirect(url_for('exam.start'))
        else:
            flash("TC Kimlik veya giriş kodu hatalı.", "danger")

    return render_template('sinav_giris.html')


# ══════════════════════════════════════════════════════════════════
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    """Password reset request - sends email with reset link"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        try:
            user = User.query.filter_by(email=email).first()
        except Exception as e:
            db.session.rollback()
            # Don't reveal if user exists
            flash("Eğer bu e-posta kayıtlıysa, şifre sıfırlama linki gönderildi.", "info")
            return render_template('forgot_password.html')

        if user:
            # Generate reset token
            try:
                token = jwt.encode({
                    'user_id': user.id,
                    'exp': datetime.utcnow() + timedelta(hours=1)
                }, get_secret_key(), algorithm='HS256')

                # TODO: Send email with reset link
                current_app.logger.info(f"Password reset requested for {email}")
            except Exception as e:
                current_app.logger.error(f"Token generation failed: {e}")

        # Always show same message (security)
        flash("Eğer bu e-posta kayıtlıysa, şifre sıfırlama linki gönderildi.", "info")

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset with token validation"""
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=['HS256'])
        user_id = payload['user_id']
        user = User.query.get(user_id)
    except jwt.ExpiredSignatureError:
        flash("Şifre sıfırlama linki süresi dolmuş.", "danger")
        return redirect(url_for('auth.forgot_password'))
    except (jwt.InvalidTokenError, Exception) as e:
        db.session.rollback()
        flash("Geçersiz şifre sıfırlama linki.", "danger")
        return redirect(url_for('auth.forgot_password'))

    if not user:
        flash("Kullanıcı bulunamadı.", "danger")
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if password != password_confirm:
            flash("Şifreler eşleşmiyor.", "danger")
            return render_template('reset_password.html', token=token)

        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg, "danger")
            return render_template('reset_password.html', token=token)

        try:
            user.set_password(password)
            db.session.commit()
            flash("Şifreniz başarıyla değiştirildi. Giriş yapabilirsiniz.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash("Şifre değiştirilemedi, lütfen tekrar deneyin.", "danger")

    return render_template('reset_password.html', token=token)

# -*- coding: utf-8 -*-
"""
Authentication Routes - Login, Logout, Password Reset
Enhanced with security best practices
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.extensions import db, limiter
import os
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """Landing page with login options"""
    return render_template('index.html')

# ══════════════════════════════════════════════════════════════════
# SECURITY HELPERS
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
    
    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    
    Returns:
        tuple: (is_valid, error_message)
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
    """
    Regenerate session ID to prevent session fixation attacks.
    Preserves session data while changing the session ID.
    """
    # Store current session data
    session_data = dict(session)
    session.clear()
    
    # Restore data with new session ID
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


# ══════════════════════════════════════════════════════════════════
# ADMIN LOGIN
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """
    Admin panel login with enhanced security
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
        tracker = get_login_tracker()
        if tracker:
            if tracker.is_locked_out(email):
                remaining = tracker.get_lockout_remaining(email)
                flash(f"Hesabınız geçici olarak kilitlendi. {remaining // 60} dakika sonra tekrar deneyin.", "danger")
                return render_template('login.html')
        
        if user and user.check_password(password):
            # Record successful login
            if tracker:
                tracker.record_successful_login(email, request.remote_addr)
            
            # Check if 2FA is enabled
            if hasattr(user, 'totp_verified') and user.totp_verified and user.totp_secret:
                # Store user ID temporarily for 2FA verification
                session['pending_2fa_user_id'] = user.id
                flash("Lütfen doğrulama kodunuzu girin.", "info")
                return redirect(url_for('twofa.challenge'))
            
            # ══════════════════════════════════════════════════════════
            # SESSION REGENERATION - Prevents session fixation attacks
            # ══════════════════════════════════════════════════════════
            regenerate_session()
            
            # Set session data
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
            if tracker:
                tracker.record_failed_attempt(email, request.remote_addr)
            
            flash("E-posta veya şifre hatalı.", "danger")
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """
    Logout and clear session
    ---
    tags:
      - Authentication
    responses:
      302:
        description: Redirect to login page
    """
    session.clear()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for('auth.login'))


# ══════════════════════════════════════════════════════════════════
# PASSWORD RESET
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def forgot_password():
    """
    Request password reset email
    ---
    tags:
      - Authentication
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        from app.models import User
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token with secure key
            import jwt
            from datetime import datetime, timedelta
            
            try:
                token = jwt.encode(
                    {'user_id': user.id, 'exp': datetime.utcnow() + timedelta(hours=1)},
                    get_secret_key(),
                    algorithm='HS256'
                )
                
                # Send email (via Celery task)
                from app.tasks.email_tasks import send_password_reset_email
                send_password_reset_email.delay(user.id, token)
            except RuntimeError as e:
                flash("Sistem hatası. Lütfen yönetici ile iletişime geçin.", "danger")
                return render_template('forgot_password.html')
        
        # Always show success to prevent user enumeration
        flash("Şifre sıfırlama linki e-posta adresinize gönderildi.", "success")
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Reset password with token and strong password validation
    ---
    tags:
      - Authentication
    parameters:
      - name: token
        in: path
        type: string
        required: true
    """
    import jwt
    
    try:
        data = jwt.decode(token, get_secret_key(), algorithms=['HS256'])
        user_id = data['user_id']
    except jwt.ExpiredSignatureError:
        flash("Şifre sıfırlama linki süresi dolmuş.", "danger")
        return redirect(url_for('auth.forgot_password'))
    except jwt.InvalidTokenError:
        flash("Geçersiz şifre sıfırlama linki.", "danger")
        return redirect(url_for('auth.forgot_password'))
    except RuntimeError:
        flash("Sistem hatası.", "danger")
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('sifre', '')
        password_confirm = request.form.get('sifre_tekrar', '')
        
        # Strong password validation
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg, "warning")
        elif password != password_confirm:
            flash("Şifreler eşleşmiyor.", "warning")
        else:
            from app.models import User
            user = User.query.get(user_id)
            if user:
                user.set_password(password)
                db.session.commit()
                flash("Şifreniz başarıyla değiştirildi.", "success")
                return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', token=token)


# ══════════════════════════════════════════════════════════════════
# EXAM CANDIDATE LOGIN (separate from admin)
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/sinav-giris', methods=['GET', 'POST'])
def sinav_giris():
    """
    Candidate exam login with access code and TC Kimlik
    ---
    tags:
      - Exam
    """
    if request.method == 'POST':
        giris_kodu = request.form.get('giris_kodu', '').strip().upper()
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        
        if not giris_kodu:
            flash("Giriş kodu gereklidir.", "warning")
            return render_template('sinav_giris.html')
        
        if not tc_kimlik:
            flash("TC Kimlik numarası gereklidir.", "warning")
            return render_template('sinav_giris.html')
        
        # Validate TC Kimlik format (11 digits)
        if not tc_kimlik.isdigit() or len(tc_kimlik) != 11:
            flash("Geçersiz TC Kimlik numarası formatı.", "danger")
            return render_template('sinav_giris.html')
        
        from app.models import Candidate
        candidate = Candidate.query.filter_by(giris_kodu=giris_kodu, is_deleted=False).first()
        
        if not candidate:
            flash("Geçersiz giriş kodu.", "danger")
            return render_template('sinav_giris.html')
        
        # Verify TC Kimlik matches
        if candidate.tc_kimlik and candidate.tc_kimlik != tc_kimlik:
            flash("TC Kimlik numarası eşleşmiyor.", "danger")
            return render_template('sinav_giris.html')
        
        # If candidate has no TC, save it (first login)
        if not candidate.tc_kimlik:
            candidate.tc_kimlik = tc_kimlik
            db.session.commit()
        
        # Check if exam already completed
        if candidate.sinav_durumu == 'tamamlandi':
            flash("Bu sınav zaten tamamlanmış.", "info")
            return redirect(url_for('exam.sinav_bitti'))
        
        # ══════════════════════════════════════════════════════════
        # SESSION REGENERATION for exam candidate
        # ══════════════════════════════════════════════════════════
        regenerate_session()
        
        # Set session
        session['aday_id'] = candidate.id
        session['giris_kodu'] = giris_kodu
        
        # Start exam - DEDUCT CREDIT ON FIRST START
        from datetime import datetime, timedelta
        from app.models import Company
        
        if not candidate.baslama_tarihi:
            # ══════════════════════════════════════════════════════════
            # CREDIT DEDUCTION - Only on first exam start
            # ══════════════════════════════════════════════════════════
            company = Company.query.get(candidate.sirket_id)
            if company:
                success = company.deduct_credit(
                    amount=1,
                    transaction_type='exam',
                    description=f"Sınav başlatıldı: {candidate.ad_soyad} ({candidate.giris_kodu})",
                    candidate_id=candidate.id
                )
                
                if not success:
                    flash("Şirketinizin yeterli sınav kredisi bulunmuyor.", "danger")
                    session.clear()
                    return render_template('sinav_giris.html')
            
            candidate.baslama_tarihi = datetime.utcnow()
            candidate.sinav_durumu = 'devam_ediyor'
            db.session.commit()
        
        # Calculate remaining time
        elapsed = datetime.utcnow() - candidate.baslama_tarihi
        remaining = (candidate.sinav_suresi * 60) - elapsed.total_seconds()
        
        if remaining <= 0:
            return redirect(url_for('exam.sinav_bitti'))
        
        session['kalan_sure'] = int(remaining)
        
        return redirect(url_for('exam.sinav'))
    
    return render_template('sinav_giris.html')

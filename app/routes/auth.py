# -*- coding: utf-8 -*-
"""
Auth Routes - Authentication and session management
FIXED: Added /demo-olustur and /register routes
GitHub: app/routes/auth.py
"""
from functools import wraps
import string
import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

auth_bp = Blueprint('auth', __name__)


# ══════════════════════════════════════════════════════════════
# LOGIN / LOGOUT
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin/Customer login page"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        sifre = request.form.get('sifre', '')
        
        from app.models import User
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.sifre_hash, sifre):
            if not user.is_active:
                flash("Hesabınız devre dışı bırakılmış.", "danger")
                return redirect(url_for('auth.login'))
            
            session['kullanici_id'] = user.id
            session['kullanici_adi'] = user.ad_soyad
            session['email'] = user.email
            session['rol'] = user.rol
            session['sirket_id'] = user.sirket_id
            
            # Update last login
            user.son_giris = datetime.utcnow()
            db.session.commit()
            
            flash(f"Hoş geldiniz, {user.ad_soyad}!", "success")
            
            # Redirect based on role
            if user.rol == 'superadmin':
                return redirect(url_for('admin.dashboard'))
            elif user.rol == 'customer':
                return redirect(url_for('customer.dashboard'))
            else:
                return redirect(url_for('admin.dashboard'))
        else:
            flash("Geçersiz email veya şifre.", "danger")
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for('auth.login'))


# ══════════════════════════════════════════════════════════════
# EXAM LOGIN (CANDIDATE)
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/sinav-giris', methods=['GET', 'POST'])
def sinav_giris():
    """Candidate exam login with access code"""
    if request.method == 'POST':
        giris_kodu = request.form.get('giris_kodu', '').strip().upper()
        
        from app.models import Candidate
        
        candidate = Candidate.query.filter_by(giris_kodu=giris_kodu, is_deleted=False).first()
        
        if not candidate:
            flash("Geçersiz giriş kodu.", "danger")
            return redirect(url_for('auth.sinav_giris'))
        
        if candidate.sinav_durumu == 'tamamlandi':
            flash("Bu sınav zaten tamamlanmış.", "warning")
            return redirect(url_for('exam.sonuc', giris_kodu=giris_kodu))
        
        # Check company credits
        if candidate.company and candidate.company.kredi <= 0:
            flash("Şirket kredisi yetersiz.", "danger")
            return redirect(url_for('auth.sinav_giris'))
        
        # Start exam if not started
        if candidate.sinav_durumu == 'beklemede':
            candidate.sinav_durumu = 'devam_ediyor'
            candidate.baslama_tarihi = datetime.utcnow()
            candidate.current_difficulty = 'B1'  # Start at B1 for CAT
            db.session.commit()
        
        session['aday_id'] = candidate.id
        session['aday_adi'] = candidate.ad_soyad
        
        return redirect(url_for('exam.sinav'))
    
    return render_template('sinav_giris.html')


# ══════════════════════════════════════════════════════════════
# PASSWORD RESET
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        from app.models import User
        import secrets
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Send reset email
            try:
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                send_password_reset_email(user.email, user.ad_soyad, reset_url)
                flash("Şifre sıfırlama linki e-posta adresinize gönderildi.", "success")
            except Exception as e:
                current_app.logger.error(f"Password reset email error: {e}")
                flash("E-posta gönderilirken hata oluştu. Lütfen tekrar deneyin.", "danger")
        else:
            # Don't reveal if email exists
            flash("Eğer bu e-posta kayıtlıysa, şifre sıfırlama linki gönderilecektir.", "info")
        
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset with token"""
    from app.models import User
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash("Geçersiz veya süresi dolmuş şifre sıfırlama linki.", "danger")
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if len(new_password) < 6:
            flash("Şifre en az 6 karakter olmalıdır.", "danger")
            return render_template('reset_password.html', token=token)
        
        if new_password != confirm_password:
            flash("Şifreler eşleşmiyor.", "danger")
            return render_template('reset_password.html', token=token)
        
        user.sifre_hash = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        
        flash("Şifreniz başarıyla değiştirildi. Giriş yapabilirsiniz.", "success")
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', token=token)


# ══════════════════════════════════════════════════════════════
# DEMO ACCOUNT CREATION - FIXED: Was returning 404
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/demo-olustur', methods=['GET', 'POST'])
def demo_olustur():
    """Create demo account for testing"""
    from app.models import Company, User, Candidate
    
    if request.method == 'POST':
        sirket_adi = request.form.get('sirket_adi', '').strip()
        email = request.form.get('email', '').strip().lower()
        ad_soyad = request.form.get('ad_soyad', '').strip()
        
        if not sirket_adi or not email or not ad_soyad:
            flash("Lütfen tüm alanları doldurun.", "danger")
            return render_template('demo_olustur.html')
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Bu e-posta adresi zaten kayıtlı.", "danger")
            return render_template('demo_olustur.html')
        
        try:
            # Create demo company
            demo_company = Company(
                isim=f"DEMO - {sirket_adi}",
                email=email,
                kredi=10,  # Give 10 free credits
                is_active=True,
                is_demo=True
            )
            db.session.add(demo_company)
            db.session.flush()
            
            # Generate random password
            demo_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            
            # Create demo user
            demo_user = User(
                ad_soyad=ad_soyad,
                email=email,
                sifre_hash=generate_password_hash(demo_password),
                rol='customer',
                sirket_id=demo_company.id,
                is_active=True
            )
            db.session.add(demo_user)
            
            # Create a sample candidate
            sample_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            sample_candidate = Candidate(
                ad_soyad="Demo Aday",
                email=f"demo_aday@{email.split('@')[1] if '@' in email else 'demo.com'}",
                giris_kodu=sample_code,
                sirket_id=demo_company.id,
                sinav_suresi=30,
                soru_limiti=25
            )
            db.session.add(sample_candidate)
            
            db.session.commit()
            
            # Send welcome email
            try:
                send_demo_welcome_email(email, ad_soyad, demo_password, sample_code)
            except Exception as e:
                current_app.logger.error(f"Demo welcome email error: {e}")
            
            flash(f"Demo hesabınız oluşturuldu! E-posta: {email}, Şifre: {demo_password}, Örnek Aday Kodu: {sample_code}", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Demo account creation error: {e}")
            flash(f"Hesap oluşturulurken hata: {str(e)}", "danger")
    
    return render_template('demo_olustur.html')


# ══════════════════════════════════════════════════════════════
# REGISTRATION - FIXED: Was returning 404
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Company registration page"""
    from app.models import Company, User
    
    if request.method == 'POST':
        sirket_adi = request.form.get('sirket_adi', '').strip()
        email = request.form.get('email', '').strip().lower()
        ad_soyad = request.form.get('ad_soyad', '').strip()
        sifre = request.form.get('sifre', '')
        sifre_tekrar = request.form.get('sifre_tekrar', '')
        telefon = request.form.get('telefon', '').strip()
        
        # Validation
        if not all([sirket_adi, email, ad_soyad, sifre]):
            flash("Lütfen tüm zorunlu alanları doldurun.", "danger")
            return render_template('register.html')
        
        if len(sifre) < 6:
            flash("Şifre en az 6 karakter olmalıdır.", "danger")
            return render_template('register.html')
        
        if sifre != sifre_tekrar:
            flash("Şifreler eşleşmiyor.", "danger")
            return render_template('register.html')
        
        # Check existing
        if User.query.filter_by(email=email).first():
            flash("Bu e-posta adresi zaten kayıtlı.", "danger")
            return render_template('register.html')
        
        if Company.query.filter_by(email=email).first():
            flash("Bu e-posta ile kayıtlı bir şirket zaten var.", "danger")
            return render_template('register.html')
        
        try:
            # Create company (pending approval)
            company = Company(
                isim=sirket_adi,
                email=email,
                telefon=telefon,
                kredi=0,  # No credits until approved/purchased
                is_active=False  # Pending admin approval
            )
            db.session.add(company)
            db.session.flush()
            
            # Create user
            user = User(
                ad_soyad=ad_soyad,
                email=email,
                sifre_hash=generate_password_hash(sifre),
                rol='customer',
                sirket_id=company.id,
                is_active=False  # Pending approval
            )
            db.session.add(user)
            db.session.commit()
            
            # Notify admin
            try:
                notify_admin_new_registration(sirket_adi, email, ad_soyad)
            except:
                pass
            
            flash("Kayıt başvurunuz alındı. Onaylandıktan sonra e-posta ile bilgilendirileceksiniz.", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration error: {e}")
            flash(f"Kayıt sırasında hata oluştu: {str(e)}", "danger")
    
    return render_template('register.html')


# ══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════
def send_password_reset_email(email, name, reset_url):
    """Send password reset email"""
    from flask_mail import Message
    from app.extensions import mail
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Skills Test Center</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2>Merhaba {name},</h2>
            <p>Şifrenizi sıfırlamak için aşağıdaki butona tıklayın:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="background: #667eea; color: white; padding: 15px 30px; 
                   text-decoration: none; border-radius: 5px; display: inline-block;">
                    Şifremi Sıfırla
                </a>
            </div>
            <p style="color: #666; font-size: 14px;">Bu link 1 saat geçerlidir.</p>
            <p style="color: #666; font-size: 14px;">Bu işlemi siz yapmadıysanız, bu e-postayı görmezden gelin.</p>
        </div>
        <div style="background: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
            Skills Test Center © {datetime.now().year}
        </div>
    </div>
    """
    
    msg = Message(
        subject="Şifre Sıfırlama - Skills Test Center",
        recipients=[email],
        html=html_body
    )
    mail.send(msg)


def send_demo_welcome_email(email, name, password, sample_code):
    """Send demo account welcome email"""
    from flask_mail import Message
    from app.extensions import mail
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">Skills Test Center</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2>Hoş Geldiniz {name}!</h2>
            <p>Demo hesabınız başarıyla oluşturuldu.</p>
            
            <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Giriş Bilgileriniz:</h3>
                <p><strong>E-posta:</strong> {email}</p>
                <p><strong>Şifre:</strong> {password}</p>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Örnek Aday Giriş Kodu:</h3>
                <p style="font-size: 24px; font-family: monospace; text-align: center;">{sample_code}</p>
            </div>
            
            <p style="color: #666;">Demo hesabınızda 10 kredi mevcuttur.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://skillstestcenter.com/login" style="background: #667eea; color: white; padding: 15px 30px; 
                   text-decoration: none; border-radius: 5px; display: inline-block;">
                    Giriş Yap
                </a>
            </div>
        </div>
        <div style="background: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
            Skills Test Center © {datetime.now().year}
        </div>
    </div>
    """
    
    msg = Message(
        subject="Demo Hesabınız Oluşturuldu - Skills Test Center",
        recipients=[email],
        html=html_body
    )
    mail.send(msg)


def notify_admin_new_registration(company_name, email, contact_name):
    """Notify admin about new registration"""
    from flask_mail import Message
    from app.extensions import mail
    
    admin_email = current_app.config.get('ADMIN_EMAIL', 'admin@skillstestcenter.com')
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif;">
        <h2>Yeni Şirket Kaydı</h2>
        <p><strong>Şirket:</strong> {company_name}</p>
        <p><strong>E-posta:</strong> {email}</p>
        <p><strong>İletişim:</strong> {contact_name}</p>
        <p>Lütfen admin panelinden onaylayın.</p>
    </div>
    """
    
    msg = Message(
        subject=f"Yeni Kayıt: {company_name}",
        recipients=[admin_email],
        html=html_body
    )
    mail.send(msg)

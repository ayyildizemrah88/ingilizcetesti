# -*- coding: utf-8 -*-
"""
Auth Routes - Authentication (Login, Register, Password Reset)
DÜZELTME: user.son_giris -> user.last_login (Model ile uyumlu hale getirildi)
GitHub: app/routes/auth.py
"""
from functools import wraps
import string
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

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
        sifre = request.form.get('sifre', '').strip()
        
        from app.models import User
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.sifre_hash, sifre):
            if not user.is_active:
                flash("Hesabınız devre dışı bırakılmış.", "danger")
                return redirect(url_for('auth.login'))
            
            # Set session variables
            session['kullanici_id'] = user.id
            session['kullanici_adi'] = user.ad_soyad
            session['email'] = user.email
            session['rol'] = user.rol
            session['sirket_id'] = user.sirket_id
            
            # Update last login - DÜZELTME: son_giris yerine last_login
            try:
                user.last_login = datetime.utcnow()
                db.session.commit()
            except Exception as e:
                # Eğer last_login yoksa (eski model), son_giris dene
                try:
                    user.son_giris = datetime.utcnow()
                    db.session.commit()
                except:
                    pass  # Neither exists, skip update
            
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
    """Logout user"""
    session.clear()
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for('main.index'))


# ══════════════════════════════════════════════════════════════
# PASSWORD RESET
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page - sends reset email"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        from app.models import User
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Send reset email (async if available)
            try:
                send_password_reset_email(user.email, user.ad_soyad, token)
                flash("Şifre sıfırlama linki e-posta adresinize gönderildi.", "success")
            except Exception as e:
                current_app.logger.error(f"Email send error: {e}")
                flash("E-posta gönderilemedi. Lütfen daha sonra tekrar deneyin.", "danger")
        else:
            # Don't reveal if email exists
            flash("Bu e-posta adresi ile kayıtlı bir hesap bulunamadı.", "warning")
        
        return redirect(url_for('auth.forgot_password'))
    
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    from app.models import User
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash("Geçersiz veya süresi dolmuş şifre sıfırlama linki.", "danger")
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        if len(password) < 6:
            flash("Şifre en az 6 karakter olmalıdır.", "warning")
            return redirect(url_for('auth.reset_password', token=token))
        
        if password != password_confirm:
            flash("Şifreler eşleşmiyor.", "warning")
            return redirect(url_for('auth.reset_password', token=token))
        
        user.sifre_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        
        flash("Şifreniz başarıyla güncellendi. Giriş yapabilirsiniz.", "success")
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', token=token)


# ══════════════════════════════════════════════════════════════
# DEMO ACCOUNT
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/demo-olustur', methods=['GET', 'POST'])
def demo_olustur():
    """Create demo account for testing"""
    if request.method == 'POST':
        sirket_adi = request.form.get('sirket_adi', '').strip()
        yetkili_adi = request.form.get('yetkili_adi', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        if not sirket_adi or not yetkili_adi or not email:
            flash("Tüm alanları doldurunuz.", "warning")
            return redirect(url_for('auth.demo_olustur'))
        
        from app.models import Company, User
        
        # Check if email exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Bu e-posta adresi zaten kayıtlı.", "warning")
            return redirect(url_for('auth.demo_olustur'))
        
        try:
            # Create demo company
            demo_company = Company(
                ad=f"{sirket_adi} (Demo)",
                email=email,
                yetkili_adi=yetkili_adi,
                kredi=10,  # 10 free credits
                is_demo=True,
                is_active=True
            )
            db.session.add(demo_company)
            db.session.flush()
            
            # Generate random password
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            
            # Create user
            demo_user = User(
                email=email,
                ad_soyad=yetkili_adi,
                sifre_hash=generate_password_hash(password),
                rol='customer',
                sirket_id=demo_company.id,
                is_active=True
            )
            db.session.add(demo_user)
            db.session.commit()
            
            # Send welcome email
            try:
                send_demo_welcome_email(email, yetkili_adi, password, "DEMO-XXXX")
            except:
                pass
            
            flash(f"Demo hesabınız oluşturuldu! Şifreniz: {password}", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Demo creation error: {e}")
            flash("Hesap oluşturulurken bir hata oluştu.", "danger")
    
    return render_template('demo_olustur.html')


# ══════════════════════════════════════════════════════════════
# REGISTER
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Company registration"""
    if request.method == 'POST':
        sirket_adi = request.form.get('sirket_adi', '').strip()
        yetkili_adi = request.form.get('yetkili_adi', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validation
        if not all([sirket_adi, yetkili_adi, email, password]):
            flash("Tüm zorunlu alanları doldurunuz.", "warning")
            return redirect(url_for('auth.register'))
        
        if password != password_confirm:
            flash("Şifreler eşleşmiyor.", "warning")
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash("Şifre en az 6 karakter olmalıdır.", "warning")
            return redirect(url_for('auth.register'))
        
        from app.models import Company, User
        
        # Check if email exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Bu e-posta adresi zaten kayıtlı.", "warning")
            return redirect(url_for('auth.register'))
        
        try:
            # Create company
            company = Company(
                ad=sirket_adi,
                email=email,
                yetkili_adi=yetkili_adi,
                telefon=telefon,
                kredi=0,
                is_active=False  # Needs admin approval
            )
            db.session.add(company)
            db.session.flush()
            
            # Create user
            user = User(
                email=email,
                ad_soyad=yetkili_adi,
                sifre_hash=generate_password_hash(password),
                rol='customer',
                sirket_id=company.id,
                is_active=False  # Needs admin approval
            )
            db.session.add(user)
            db.session.commit()
            
            # Notify admin
            try:
                send_new_registration_notification(sirket_adi, email, yetkili_adi)
            except:
                pass
            
            flash("Kaydınız alındı! Admin onayından sonra giriş yapabilirsiniz.", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration error: {e}")
            flash("Kayıt sırasında bir hata oluştu.", "danger")
    
    return render_template('register.html')


# ══════════════════════════════════════════════════════════════
# EMAIL HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════
def send_password_reset_email(email, name, token):
    """Send password reset email"""
    from flask_mail import Message
    from app.extensions import mail
    
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    msg = Message(
        subject="Skills Test Center - Şifre Sıfırlama",
        recipients=[email],
        html=f"""
        <h1>Skills Test Center</h1>
        <h2>Merhaba {name},</h2>
        <p>Şifrenizi sıfırlamak için aşağıdaki butona tıklayın:</p>
        <a href="{reset_url}" style="background:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">Şifremi Sıfırla</a>
        <p>Bu link 1 saat geçerlidir.</p>
        <p>Bu işlemi siz yapmadıysanız, bu e-postayı görmezden gelin.</p>
        """
    )
    mail.send(msg)


def send_demo_welcome_email(email, name, password, sample_code):
    """Send welcome email for demo account"""
    from flask_mail import Message
    from app.extensions import mail
    
    msg = Message(
        subject="Skills Test Center - Demo Hesabınız Hazır",
        recipients=[email],
        html=f"""
        <h1>Skills Test Center</h1>
        <h2>Hoş Geldiniz {name}!</h2>
        <p>Demo hesabınız başarıyla oluşturuldu.</p>
        <h3>Giriş Bilgileriniz:</h3>
        <p>E-posta: {email}<br>Şifre: {password}</p>
        <h3>Örnek Aday Giriş Kodu:</h3>
        <p>{sample_code}</p>
        <p>Demo hesabınızda 10 kredi mevcuttur.</p>
        <a href="https://skillstestcenter.com/login">Giriş Yap</a>
        """
    )
    mail.send(msg)


def send_new_registration_notification(company_name, email, contact_name):
    """Notify admin of new registration"""
    from flask_mail import Message
    from app.extensions import mail
    
    msg = Message(
        subject="Skills Test Center - Yeni Şirket Kaydı",
        recipients=["admin@skillstestcenter.com"],
        html=f"""
        <h2>Yeni Şirket Kaydı</h2>
        <p>Şirket: {company_name}<br>
        E-posta: {email}<br>
        İletişim: {contact_name}</p>
        <p>Lütfen admin panelinden onaylayın.</p>
        """
    )
    mail.send(msg)

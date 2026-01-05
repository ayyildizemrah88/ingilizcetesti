# -*- coding: utf-8 -*-
"""
Auth Routes - Kimlik Doğrulama ve Oturum Yönetimi
GitHub: app/routes/auth.py

DÜZELTME: Dosya bozuktu, tamamen yeniden oluşturuldu.
Eklenen yeni rotalar: /giris, /kayit, /iletisim
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from datetime import datetime, timedelta
import secrets

auth_bp = Blueprint('auth', __name__)


# ══════════════════════════════════════════════════════════════
# Decorators
# ══════════════════════════════════════════════════════════════
def login_required(f):
    """Require user login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Require admin or superadmin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') not in ['admin', 'superadmin']:
            flash("Bu sayfaya erişim yetkiniz yok.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════
# Login / Logout
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash("E-posta ve şifre gereklidir.", "warning")
            return render_template('login.html')
        
        from app.models import User
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.sifre_hash, password):
            if not user.aktif:
                flash("Hesabınız henüz aktif değil. Lütfen admin onayını bekleyin.", "warning")
                return render_template('login.html')
            
            # Set session
            session['kullanici_id'] = user.id
            session['kullanici'] = user.ad
            session['email'] = user.email
            session['rol'] = user.rol
            session['sirket_id'] = user.sirket_id
            
            # Update last login
            user.son_giris = datetime.utcnow()
            db.session.commit()
            
            flash(f"Hoş geldiniz, {user.ad}!", "success")
            
            # Redirect based on role
            if user.rol == 'superadmin':
                return redirect(url_for('admin.dashboard'))
            elif user.rol == 'customer':
                return redirect(url_for('customer.dashboard'))
            else:
                return redirect(url_for('admin.dashboard'))
        else:
            flash("Geçersiz e-posta veya şifre.", "danger")
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for('auth.login'))


# ══════════════════════════════════════════════════════════════
# Türkçe URL - Giriş
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/giris')
def giris():
    """Türkçe giriş URL'i - /login'e yönlendir"""
    return redirect(url_for('auth.login'))


# ══════════════════════════════════════════════════════════════
# Kayıt (Registration)
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/kayit', methods=['GET', 'POST'])
def kayit():
    """Kurumsal kayıt sayfası"""
    if request.method == 'POST':
        firma_adi = request.form.get('firma_adi', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        yetkili_adi = request.form.get('yetkili_adi', '').strip()
        sifre = request.form.get('sifre', '')
        sifre_tekrar = request.form.get('sifre_tekrar', '')
        
        # Validation
        errors = []
        if not firma_adi:
            errors.append("Firma adı gereklidir.")
        if not email:
            errors.append("E-posta adresi gereklidir.")
        if not yetkili_adi:
            errors.append("Yetkili adı gereklidir.")
        if len(sifre) < 6:
            errors.append("Şifre en az 6 karakter olmalıdır.")
        if sifre != sifre_tekrar:
            errors.append("Şifreler eşleşmiyor.")
            
        # Check existing email
        from app.models import User, Company
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            errors.append("Bu e-posta adresi zaten kayıtlı.")
            
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template('kayit.html')
        
        try:
            # Create company
            company = Company(
                ad=firma_adi,
                email=email,
                telefon=telefon,
                yetkili_adi=yetkili_adi,
                kredi=0,
                aktif=False  # Admin onayı gerekli
            )
            db.session.add(company)
            db.session.flush()  # Get company ID
            
            # Create user
            user = User(
                ad=yetkili_adi,
                email=email,
                sifre_hash=generate_password_hash(sifre),
                rol='customer',
                sirket_id=company.id,
                aktif=False  # Admin onayı gerekli
            )
            db.session.add(user)
            db.session.commit()
            
            flash("Kayıt başarılı! Hesabınız admin onayından sonra aktif olacaktır.", "success")
            
            # Send notification to admin (optional)
            try:
                from app.tasks.email_tasks import send_admin_notification
                send_admin_notification.delay(
                    subject="Yeni Şirket Kaydı",
                    message=f"Yeni şirket kaydı: {firma_adi} - {email}"
                )
            except:
                pass
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash("Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.", "danger")
            import logging
            logging.error(f"Registration error: {e}")
            return render_template('kayit.html')
    
    return render_template('kayit.html')


# ══════════════════════════════════════════════════════════════
# İletişim (Contact)
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/iletisim', methods=['GET', 'POST'])
def iletisim():
    """İletişim sayfası"""
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        email = request.form.get('email', '').strip()
        konu = request.form.get('konu', '').strip()
        mesaj = request.form.get('mesaj', '').strip()
        
        if not all([ad_soyad, email, konu, mesaj]):
            flash("Lütfen tüm alanları doldurun.", "warning")
            return render_template('iletisim.html')
        
        # Send email or save to database
        try:
            from app.tasks.email_tasks import send_contact_email
            send_contact_email.delay(
                name=ad_soyad,
                email=email,
                subject=konu,
                message=mesaj
            )
            flash("Mesajınız başarıyla gönderildi. En kısa sürede size dönüş yapacağız.", "success")
        except:
            # Fallback: just show success (log the message)
            import logging
            logging.info(f"Contact form: {ad_soyad} - {email} - {konu}: {mesaj}")
            flash("Mesajınız alındı. En kısa sürede size dönüş yapacağız.", "success")
        
        return redirect(url_for('auth.iletisim'))
    
    return render_template('iletisim.html')


# ══════════════════════════════════════════════════════════════
# Şifre Sıfırlama (Password Reset)
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Şifremi unuttum sayfası"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash("Lütfen e-posta adresinizi girin.", "warning")
            return render_template('forgot_password.html')
        
        from app.models import User
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Send reset email
            try:
                from app.tasks.email_tasks import send_password_reset_email
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                send_password_reset_email.delay(user.id, reset_url)
            except Exception as e:
                import logging
                logging.error(f"Password reset email error: {e}")
        
        # Always show success to prevent email enumeration
        flash("E-posta adresinize şifre sıfırlama bağlantısı gönderildi.", "success")
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Şifre sıfırlama sayfası"""
    from app.models import User
    
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash("Geçersiz veya süresi dolmuş bağlantı.", "danger")
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        if len(password) < 6:
            flash("Şifre en az 6 karakter olmalıdır.", "warning")
            return render_template('reset_password.html', token=token)
        
        if password != password_confirm:
            flash("Şifreler eşleşmiyor.", "warning")
            return render_template('reset_password.html', token=token)
        
        # Update password
        user.sifre_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        
        flash("Şifreniz başarıyla güncellendi. Giriş yapabilirsiniz.", "success")
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', token=token)


# ══════════════════════════════════════════════════════════════
# Aday/Sınav Girişi (Candidate Exam Entry)
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/sinav-giris', methods=['GET', 'POST'])
def sinav_giris():
    """Aday sınav giriş sayfası"""
    if request.method == 'POST':
        giris_kodu = request.form.get('giris_kodu', '').strip().upper()
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        
        if not giris_kodu:
            flash("Giriş kodu gereklidir.", "warning")
            return render_template('sinav_giris.html')
        
        from app.models import Candidate
        candidate = Candidate.query.filter_by(giris_kodu=giris_kodu).first()
        
        if not candidate:
            flash("Geçersiz giriş kodu.", "danger")
            return render_template('sinav_giris.html')
        
        # Optional TC verification
        if tc_kimlik and candidate.tc_kimlik and tc_kimlik != candidate.tc_kimlik:
            flash("TC Kimlik numarası eşleşmiyor.", "danger")
            return render_template('sinav_giris.html')
        
        # Check if exam already completed
        if candidate.sinav_durumu == 'tamamlandi':
            flash("Bu sınav zaten tamamlanmış.", "info")
            return redirect(url_for('exam.result', giris_kodu=giris_kodu))
        
        # Set session
        session['candidate_id'] = candidate.id
        session['aday_id'] = candidate.id
        session['candidate_email'] = candidate.email
        session['giris_kodu'] = giris_kodu
        
        # Redirect to exam or tutorial
        if candidate.sinav_durumu == 'beklemede':
            return redirect(url_for('candidate.tutorial'))
        else:
            return redirect(url_for('exam.start', giris_kodu=giris_kodu))
    
    return render_template('sinav_giris.html')


# ══════════════════════════════════════════════════════════════
# Demo Hesap Oluşturma
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/demo-olustur', methods=['GET', 'POST'])
def demo_olustur():
    """Demo hesabı oluşturma"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        firma_adi = request.form.get('firma_adi', '').strip()
        
        if not email or not firma_adi:
            flash("E-posta ve firma adı gereklidir.", "warning")
            return render_template('demo_olustur.html')
        
        from app.models import User, Company
        
        # Check existing
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Bu e-posta adresi zaten kayıtlı.", "warning")
            return render_template('demo_olustur.html')
        
        try:
            import string
            import random
            
            # Generate random password
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            
            # Create demo company
            company = Company(
                ad=firma_adi,
                email=email,
                kredi=10,  # Demo credits
                aktif=True,
                is_demo=True
            )
            db.session.add(company)
            db.session.flush()
            
            # Create demo user
            user = User(
                ad=firma_adi,
                email=email,
                sifre_hash=generate_password_hash(password),
                rol='customer',
                sirket_id=company.id,
                aktif=True
            )
            db.session.add(user)
            
            # Create sample candidate
            from app.models import Candidate
            sample_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            candidate = Candidate(
                ad_soyad="Demo Aday",
                email=email,
                giris_kodu=sample_code,
                sirket_id=company.id,
                sinav_suresi=30,
                soru_limiti=25
            )
            db.session.add(candidate)
            
            db.session.commit()
            
            # Send credentials email
            try:
                from app.tasks.email_tasks import send_demo_credentials
                send_demo_credentials.delay(user.id, password, sample_code)
            except:
                pass
            
            flash(f"Demo hesabınız oluşturuldu! E-posta: {email}, Şifre: {password}", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            import logging
            logging.error(f"Demo creation error: {e}")
            flash("Demo hesabı oluşturulurken bir hata oluştu.", "danger")
    
    return render_template('demo_olustur.html')


# ══════════════════════════════════════════════════════════════
# Profile
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    from app.models import User
    
    user = User.query.get(session['kullanici_id'])
    
    if request.method == 'POST':
        user.ad = request.form.get('ad', user.ad).strip()
        
        new_password = request.form.get('new_password', '')
        if new_password:
            if len(new_password) < 6:
                flash("Şifre en az 6 karakter olmalıdır.", "warning")
                return render_template('profile.html', user=user)
            user.sifre_hash = generate_password_hash(new_password)
        
        db.session.commit()
        session['kullanici'] = user.ad
        flash("Profil güncellendi.", "success")
    
    return render_template('profile.html', user=user)

# ══════════════════════════════════════════════════════════════
# SUPER ADMIN OLUŞTURMA ROUTE - Sabit kullanıcı
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/setup-admin')
def setup_admin():
    """Super admin oluşturma - Eğer yoksa oluşturur"""
    from app.models import User
    from werkzeug.security import generate_password_hash
    
    # Super admin var mı kontrol et
    existing = User.query.filter_by(email='emrahayyildiz88@yahoo.com').first()
    if existing:
        # Varsa rolünü superadmin yap ve aktifleştir
        existing.rol = 'superadmin'
        existing.aktif = True
        existing.is_active = True
        db.session.commit()
        return """
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>✅ Super Admin Güncellendi</h1>
            <p><strong>Email:</strong> emrahayyildiz88@yahoo.com</p>
            <p>Hesap aktifleştirildi ve superadmin rolü verildi.</p>
            <a href="/login" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Giriş Yap</a>
        </body>
        </html>
        """
    
    # Yoksa yeni oluştur
    admin = User(
        email='emrahayyildiz88@yahoo.com',
        sifre_hash=generate_password_hash('Gamberetto88!'),
        ad='Emrah',
        ad_soyad='Emrah Ayyıldız',
        rol='superadmin',
        aktif=True,
        is_active=True
    )
    db.session.add(admin)
    db.session.commit()
    
    return """
    <html>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>✅ Super Admin Oluşturuldu!</h1>
        <p><strong>Email:</strong> emrahayyildiz88@yahoo.com</p>
        <p><strong>Şifre:</strong> Gamberetto88!</p>
        <a href="/login" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Giriş Yap</a>
    </body>
    </html>
    """

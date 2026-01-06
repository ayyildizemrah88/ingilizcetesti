# -*- coding: utf-8 -*-
"""
Auth Routes - Kimlik Doğrulama ve Kullanıcı Yönetimi
GitHub: app/routes/auth.py
Skills Test Center - Authentication System
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import secrets
import os

auth_bp = Blueprint('auth', __name__)

# ============================================
# DECORATORS
# ============================================

def login_required(f):
    """Giriş zorunluluğu decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# GİRİŞ / LOGIN
# ============================================

@auth_bp.route('/giris', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Kullanıcı giriş sayfası"""
    from app.extensions import db
    from app.models import User
    
    # Zaten giriş yapmışsa yönlendir
    if 'kullanici_id' in session:
        if session.get('rol') == 'superadmin':
            return redirect(url_for('admin.dashboard'))
        elif session.get('rol') == 'customer':
            return redirect(url_for('customer.dashboard'))
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('sifre', '') or request.form.get('password', '')
        
        if not email or not password:
            flash('Lütfen email ve şifre giriniz.', 'warning')
            return render_template('giris.html')
        
        try:
            user = User.query.filter_by(email=email).first()
            
            if user:
                # Şifre kontrolü
                password_valid = False
                
                # check_password_hash ile kontrol
                if hasattr(user, 'sifre_hash') and user.sifre_hash:
                    try:
                        password_valid = check_password_hash(user.sifre_hash, password)
                    except:
                        pass
                
                # check_password metodu ile kontrol
                if not password_valid and hasattr(user, 'check_password'):
                    try:
                        password_valid = user.check_password(password)
                    except:
                        pass
                
                if password_valid:
                    # Hesap aktif mi kontrol
                    if hasattr(user, 'is_active') and not user.is_active:
                        flash('Hesabınız deaktif edilmiş. Lütfen yönetici ile iletişime geçin.', 'danger')
                        return render_template('giris.html')
                    
                    # Session'a kullanıcı bilgilerini kaydet
                    session['kullanici_id'] = user.id
                    session['kullanici'] = user.email
                    session['rol'] = user.rol
                    session['ad_soyad'] = getattr(user, 'ad_soyad', None) or user.email
                    
                    if hasattr(user, 'sirket_id') and user.sirket_id:
                        session['sirket_id'] = user.sirket_id
                    
                    # Son giriş zamanını güncelle
                    try:
                        user.son_giris = datetime.now()
                        db.session.commit()
                    except Exception as e:
                        current_app.logger.warning(f"Son giriş güncellenemedi: {e}")
                        db.session.rollback()
                    
                    flash(f"Hoş geldiniz, {session.get('ad_soyad', 'Kullanıcı')}!", 'success')
                    
                    # Role göre yönlendirme
                    if user.rol == 'superadmin':
                        return redirect(url_for('admin.dashboard'))
                    elif user.rol == 'customer':
                        return redirect(url_for('customer.dashboard'))
                    else:
                        return redirect(url_for('main.index'))
                else:
                    flash('Geçersiz e-posta veya şifre.', 'danger')
            else:
                flash('Geçersiz e-posta veya şifre.', 'danger')
                
        except Exception as e:
            current_app.logger.error(f"Login error: {e}")
            flash('Giriş sırasında bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
    
    return render_template('giris.html')


# ============================================
# ÇIKIŞ / LOGOUT
# ============================================

@auth_bp.route('/cikis')
@auth_bp.route('/logout')
def logout():
    """Kullanıcı çıkışı"""
    session.clear()
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('main.index'))


# ============================================
# KAYIT / REGISTER
# ============================================

@auth_bp.route('/kayit', methods=['GET', 'POST'])
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Kurumsal kayıt sayfası"""
    from app.extensions import db
    from app.models import User, Company
    
    if request.method == 'POST':
        # Form verileri
        sirket_adi = request.form.get('sirket_adi', '').strip()
        sirket_email = request.form.get('sirket_email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        adres = request.form.get('adres', '').strip()
        
        ad_soyad = request.form.get('ad_soyad', '').strip()
        email = request.form.get('email', '').strip().lower()
        sifre = request.form.get('sifre', '')
        sifre_tekrar = request.form.get('sifre_tekrar', '')
        
        kvkk = request.form.get('kvkk')
        
        # Validasyonlar
        errors = []
        
        if not sirket_adi:
            errors.append('Şirket adı gereklidir.')
        if not email:
            errors.append('E-posta adresi gereklidir.')
        if not sifre:
            errors.append('Şifre gereklidir.')
        if len(sifre) < 8:
            errors.append('Şifre en az 8 karakter olmalıdır.')
        if sifre != sifre_tekrar:
            errors.append('Şifreler eşleşmiyor.')
        if not kvkk:
            errors.append('KVKK onayı gereklidir.')
        
        # Email zaten kayıtlı mı?
        if User.query.filter_by(email=email).first():
            errors.append('Bu e-posta adresi zaten kayıtlı.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('kayit.html')
        
        try:
            # Şirket oluştur
            company = Company(
                isim=sirket_adi,
                email=sirket_email or email,
                telefon=telefon,
                adres=adres,
                kredi=0,
                is_active=True
            )
            db.session.add(company)
            db.session.flush()  # ID almak için
            
            # Kullanıcı oluştur
            user = User(
                email=email,
                ad_soyad=ad_soyad,
                rol='customer',
                sirket_id=company.id,
                is_active=True
            )
            user.set_password(sifre)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Register error: {e}")
            flash('Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
    
    return render_template('kayit.html')


# ============================================
# ŞİFREMİ UNUTTUM / FORGOT PASSWORD
# ============================================

@auth_bp.route('/sifremi-unuttum', methods=['GET', 'POST'])
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Şifre sıfırlama talebi"""
    from app.extensions import db
    from app.models import User
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Lütfen e-posta adresinizi girin.', 'warning')
            return render_template('forgot_password.html')
        
        try:
            user = User.query.filter_by(email=email).first()
            
            if user:
                # Token oluştur
                token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(hours=1)
                
                # Token'ı kaydet (PasswordResetToken modeli varsa)
                try:
                    from app.models import PasswordResetToken
                    
                    # Eski tokenları sil
                    PasswordResetToken.query.filter_by(user_id=user.id).delete()
                    
                    # Yeni token oluştur
                    reset_token = PasswordResetToken(
                        user_id=user.id,
                        token=token,
                        expires_at=expires_at
                    )
                    db.session.add(reset_token)
                    db.session.commit()
                    
                    # Email gönder
                    reset_url = url_for('auth.reset_password', token=token, _external=True)
                    send_password_reset_email(email, token, reset_url)
                    
                except Exception as e:
                    current_app.logger.warning(f"Token kaydetme hatası: {e}")
                    db.session.rollback()
            
            # Güvenlik için her durumda aynı mesajı göster
            flash('Eğer bu e-posta adresi sistemimizde kayıtlıysa, şifre sıfırlama linki gönderildi.', 'info')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"Forgot password error: {e}")
            flash('Bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
    
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Token ile şifre sıfırlama"""
    from app.extensions import db
    from app.models import User
    
    try:
        from app.models import PasswordResetToken
        
        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        
        if not reset_token:
            flash('Geçersiz veya süresi dolmuş bağlantı.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        if reset_token.expires_at < datetime.now():
            db.session.delete(reset_token)
            db.session.commit()
            flash('Bu bağlantının süresi dolmuş. Lütfen yeni bir talep oluşturun.', 'warning')
            return redirect(url_for('auth.forgot_password'))
        
        user = User.query.get(reset_token.user_id)
        
        if not user:
            flash('Kullanıcı bulunamadı.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        if request.method == 'POST':
            sifre = request.form.get('sifre', '')
            sifre_tekrar = request.form.get('sifre_tekrar', '')
            
            if not sifre:
                flash('Lütfen yeni şifrenizi girin.', 'warning')
                return render_template('reset_password.html', token=token)
            
            if len(sifre) < 8:
                flash('Şifre en az 8 karakter olmalıdır.', 'warning')
                return render_template('reset_password.html', token=token)
            
            if sifre != sifre_tekrar:
                flash('Şifreler eşleşmiyor.', 'warning')
                return render_template('reset_password.html', token=token)
            
            try:
                user.set_password(sifre)
                db.session.delete(reset_token)
                db.session.commit()
                
                flash('Şifreniz başarıyla güncellendi. Şimdi giriş yapabilirsiniz.', 'success')
                return redirect(url_for('auth.login'))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Reset password error: {e}")
                flash('Şifre güncellenirken bir hata oluştu.', 'danger')
        
        return render_template('reset_password.html', token=token)
        
    except ImportError:
        # PasswordResetToken modeli yoksa
        flash('Şifre sıfırlama özelliği şu an kullanılamıyor.', 'warning')
        return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"Reset password error: {e}")
        flash('Bir hata oluştu.', 'danger')
        return redirect(url_for('auth.forgot_password'))


# ============================================
# SINAV GİRİŞİ
# ============================================

@auth_bp.route('/sinav-giris', methods=['GET', 'POST'])
def sinav_giris():
    """Aday sınav girişi"""
    from app.extensions import db
    from app.models import Candidate
    
    if request.method == 'POST':
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        giris_kodu = request.form.get('giris_kodu', '').strip().upper()
        
        if not tc_kimlik or not giris_kodu:
            flash('Lütfen TC Kimlik No ve Giriş Kodu giriniz.', 'warning')
            return render_template('sinav_giris.html')
        
        try:
            candidate = Candidate.query.filter_by(
                tc_kimlik=tc_kimlik,
                giris_kodu=giris_kodu
            ).first()
            
            if candidate:
                # Sınav durumu kontrolü
                if candidate.sinav_durumu == 'tamamlandi':
                    flash('Bu sınav zaten tamamlanmış.', 'warning')
                    return render_template('sinav_giris.html')
                
                if hasattr(candidate, 'is_deleted') and candidate.is_deleted:
                    flash('Bu aday kaydı silinmiş.', 'danger')
                    return render_template('sinav_giris.html')
                
                # Session'a aday bilgilerini kaydet
                session['aday_id'] = candidate.id
                session['aday_ad'] = candidate.ad_soyad
                session['sinav_modu'] = 'gercek'
                
                # Sınav başlamadıysa başlat
                if candidate.sinav_durumu == 'beklemede':
                    candidate.sinav_durumu = 'devam_ediyor'
                    candidate.baslangic_tarihi = datetime.now()
                    db.session.commit()
                
                flash(f'Hoş geldiniz, {candidate.ad_soyad}!', 'success')
                return redirect(url_for('exam.sinav'))
            else:
                flash('Geçersiz TC Kimlik No veya Giriş Kodu.', 'danger')
                
        except Exception as e:
            current_app.logger.error(f"Sinav giris error: {e}")
            flash('Giriş sırasında bir hata oluştu.', 'danger')
    
    return render_template('sinav_giris.html')


@auth_bp.route('/demo-giris', methods=['GET', 'POST'])
@auth_bp.route('/demo-login', methods=['GET', 'POST'])
def demo_login():
    """Demo sınav girişi"""
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', 'Demo Kullanıcı').strip()
        email = request.form.get('email', '').strip()
        
        # Demo session oluştur
        session['aday_id'] = 'demo'
        session['aday_ad'] = ad_soyad or 'Demo Kullanıcı'
        session['sinav_modu'] = 'demo'
        
        flash('Demo sınava hoş geldiniz!', 'success')
        return redirect(url_for('exam.sinav'))
    
    return render_template('demo_giris.html')


# ============================================
# İLETİŞİM
# ============================================

@auth_bp.route('/iletisim', methods=['GET', 'POST'])
@auth_bp.route('/contact', methods=['GET', 'POST'])
def iletisim():
    """İletişim formu"""
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        email = request.form.get('email', '').strip()
        konu = request.form.get('konu', '').strip()
        mesaj = request.form.get('mesaj', '').strip()
        
        if not ad_soyad or not email or not mesaj:
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return render_template('iletisim.html')
        
        try:
            # Admin'e email gönder
            send_contact_email(ad_soyad, email, konu, mesaj)
            flash('Mesajınız başarıyla gönderildi. En kısa sürede dönüş yapacağız.', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            current_app.logger.error(f"Contact email error: {e}")
            flash('Mesaj gönderilirken bir hata oluştu.', 'danger')
    
    return render_template('iletisim.html')


# ============================================
# PROFİL
# ============================================

@auth_bp.route('/profil', methods=['GET', 'POST'])
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Kullanıcı profili"""
    from app.extensions import db
    from app.models import User
    
    user = User.query.get(session.get('kullanici_id'))
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        new_password_confirm = request.form.get('new_password_confirm', '')
        
        try:
            # Ad soyad güncelle
            if ad_soyad:
                user.ad_soyad = ad_soyad
                session['ad_soyad'] = ad_soyad
            
            # Şifre değişikliği
            if new_password:
                if not current_password:
                    flash('Mevcut şifrenizi girin.', 'warning')
                    return render_template('profile.html', user=user)
                
                if not user.check_password(current_password):
                    flash('Mevcut şifre yanlış.', 'danger')
                    return render_template('profile.html', user=user)
                
                if len(new_password) < 8:
                    flash('Yeni şifre en az 8 karakter olmalıdır.', 'warning')
                    return render_template('profile.html', user=user)
                
                if new_password != new_password_confirm:
                    flash('Yeni şifreler eşleşmiyor.', 'warning')
                    return render_template('profile.html', user=user)
                
                user.set_password(new_password)
            
            db.session.commit()
            flash('Profil bilgileriniz güncellendi.', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Profile update error: {e}")
            flash('Profil güncellenirken bir hata oluştu.', 'danger')
    
    return render_template('profile.html', user=user)


# ============================================
# EMAIL FONKSİYONLARI
# ============================================

def send_email(to_email, subject, html_content, text_content=None):
    """SMTP üzerinden email gönder"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = os.getenv('SMTP_PASS', '')
    
    if not smtp_user or not smtp_pass:
        current_app.logger.warning("SMTP ayarları yapılandırılmamış!")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Skills Test Center <{smtp_user}>"
        msg['To'] = to_email
        
        if text_content:
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(part1)
        
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part2)
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        
        current_app.logger.info(f"✅ Email gönderildi: {to_email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"❌ Email gönderilemedi: {e}")
        return False


def send_password_reset_email(email, token, reset_url):
    """Şifre sıfırlama emaili gönder"""
    subject = "Skills Test Center - Şifre Sıfırlama"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #888; margin-top: 20px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Şifre Sıfırlama</h1>
            </div>
            <div class="content">
                <p>Merhaba,</p>
                <p>Skills Test Center hesabınız için şifre sıfırlama talebinde bulundunuz.</p>
                <p>Şifrenizi sıfırlamak için aşağıdaki butona tıklayın:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Şifremi Sıfırla</a>
                </p>
                <p>Veya bu bağlantıyı tarayıcınıza yapıştırın:</p>
                <p style="word-break: break-all; color: #667eea;">{reset_url}</p>
                <p><strong>Not:</strong> Bu bağlantı 1 saat içinde geçerliliğini yitirecektir.</p>
                <p>Eğer bu talebi siz yapmadıysanız, bu emaili görmezden gelebilirsiniz.</p>
            </div>
            <div class="footer">
                <p>© 2026 Skills Test Center - Tüm Hakları Saklıdır</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Şifre Sıfırlama - Skills Test Center
    
    Merhaba,
    
    Skills Test Center hesabınız için şifre sıfırlama talebinde bulundunuz.
    
    Şifrenizi sıfırlamak için bu bağlantıyı ziyaret edin:
    {reset_url}
    
    Bu bağlantı 1 saat içinde geçerliliğini yitirecektir.
    
    Eğer bu talebi siz yapmadıysanız, bu emaili görmezden gelebilirsiniz.
    
    © 2026 Skills Test Center
    """
    
    return send_email(email, subject, html_content, text_content)


def send_contact_email(ad_soyad, email, konu, mesaj):
    """İletişim formu emaili gönder"""
    admin_email = os.getenv('ADMIN_EMAIL', os.getenv('SMTP_USER', ''))
    
    if not admin_email:
        current_app.logger.warning("Admin email ayarlanmamış!")
        return False
    
    subject = f"İletişim Formu: {konu or 'Yeni Mesaj'}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .info {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📧 Yeni İletişim Formu Mesajı</h2>
            </div>
            <div class="content">
                <div class="info">
                    <p><strong>Gönderen:</strong> {ad_soyad}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Konu:</strong> {konu or 'Belirtilmemiş'}</p>
                </div>
                <div class="info">
                    <p><strong>Mesaj:</strong></p>
                    <p>{mesaj}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(admin_email, subject, html_content)


def send_candidate_invitation_email(candidate):
    """Aday davet emaili gönder"""
    subject = "Skills Test Center - Sınav Davetiyesi"
    
    sinav_url = "https://skillstestcenter.com/sinav-giris"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .code-box {{ background: #2d3748; color: #38ef7d; padding: 20px; border-radius: 10px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 5px; margin: 20px 0; }}
            .info {{ background: white; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .button {{ display: inline-block; background: #11998e; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #888; margin-top: 20px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📝 Sınav Davetiyesi</h1>
            </div>
            <div class="content">
                <p>Sayın <strong>{candidate.ad_soyad}</strong>,</p>
                <p>İngilizce yeterlilik sınavına davet edildiniz.</p>
                
                <h3>Giriş Kodunuz:</h3>
                <div class="code-box">{candidate.giris_kodu}</div>
                
                <div class="info">
                    <p><strong>📧 Email:</strong> {candidate.email}</p>
                    <p><strong>⏱️ Sınav Süresi:</strong> {candidate.sinav_suresi or 30} dakika</p>
                    <p><strong>❓ Soru Sayısı:</strong> {candidate.soru_limiti or 25} soru</p>
                </div>
                
                <p style="text-align: center;">
                    <a href="{sinav_url}" class="button">Sınava Başla</a>
                </p>
                
                <h3>Sınav Kuralları:</h3>
                <ul>
                    <li>Sınav süresi başladıktan sonra durmayacaktır</li>
                    <li>Her soru için sadece bir cevap hakkınız vardır</li>
                    <li>Sınav sırasında başka sekmelere geçmeyiniz</li>
                    <li>Stabil bir internet bağlantınız olduğundan emin olun</li>
                </ul>
                
                <p>Başarılar dileriz! 🍀</p>
            </div>
            <div class="footer">
                <p>© 2026 Skills Test Center - Tüm Hakları Saklıdır</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Sınav Davetiyesi - Skills Test Center
    
    Sayın {candidate.ad_soyad},
    
    İngilizce yeterlilik sınavına davet edildiniz.
    
    Giriş Kodunuz: {candidate.giris_kodu}
    
    Sınava giriş yapmak için: {sinav_url}
    
    Sınav Süresi: {candidate.sinav_suresi or 30} dakika
    Soru Sayısı: {candidate.soru_limiti or 25} soru
    
    Başarılar dileriz!
    
    © 2026 Skills Test Center
    """
    
    return send_email(candidate.email, subject, html_content, text_content)


def send_exam_result_email(candidate):
    """Sınav sonuç emaili gönder"""
    subject = "Skills Test Center - Sınav Sonucunuz"
    
    level_colors = {
        'A1': '#e74c3c',
        'A2': '#e67e22', 
        'B1': '#f1c40f',
        'B2': '#2ecc71',
        'C1': '#3498db',
        'C2': '#9b59b6'
    }
    level_color = level_colors.get(candidate.seviye_sonuc, '#667eea')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .result-box {{ background: white; padding: 30px; border-radius: 15px; text-align: center; margin: 20px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
            .level {{ font-size: 72px; font-weight: bold; color: {level_color}; }}
            .score {{ font-size: 24px; color: #666; margin-top: 10px; }}
            .footer {{ text-align: center; color: #888; margin-top: 20px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎓 Sınav Sonucunuz</h1>
            </div>
            <div class="content">
                <p>Sayın <strong>{candidate.ad_soyad}</strong>,</p>
                <p>İngilizce yeterlilik sınavınız başarıyla tamamlanmıştır.</p>
                
                <div class="result-box">
                    <div class="level">{candidate.seviye_sonuc or 'N/A'}</div>
                    <div class="score">Puan: {candidate.puan or 0}/100</div>
                </div>
                
                <p>Sınav sonuçlarınızı detaylı olarak görüntülemek için platformumuzu ziyaret edebilirsiniz.</p>
                
                <p>Tebrikler ve başarılarınızın devamını dileriz! 🎉</p>
            </div>
            <div class="footer">
                <p>© 2026 Skills Test Center - Tüm Hakları Saklıdır</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(candidate.email, subject, html_content)
 

# -*- coding: utf-8 -*-
"""
Auth Routes - Kimlik Doğrulama ve Kullanıcı Yönetimi
GitHub: app/routes/auth.py
Skills Test Center - Authentication System
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, csrf, limiter
from datetime import datetime, timedelta
import secrets
import re
import logging

auth_bp = Blueprint('auth', __name__)

# ══════════════════════════════════════════════════════════════════
# EMAIL GÖNDERME FONKSİYONLARI
# ══════════════════════════════════════════════════════════════════

def send_email(to_email, subject, html_content, text_content=None):
    """
    Email gönderme fonksiyonu - SMTP kullanarak
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import os
    
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
        
        # Text version
        if text_content:
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(part1)
        
        # HTML version
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part2)
        
        # SMTP bağlantısı
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        
        current_app.logger.info(f"✅ Email gönderildi: {to_email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"❌ Email gönderilemedi: {e}")
        return False


def send_password_reset_email(email, reset_token, reset_url):
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


def send_candidate_invitation_email(candidate):
    """Aday davet emaili gönder"""
    subject = "Skills Test Center - Sınav Davetiyesi"
    
    sinav_url = f"https://skillstestcenter.com/sinav-giris"
    
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
    
    # Seviyeye göre renk
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


# ══════════════════════════════════════════════════════════════════
# DECORATOR'LAR
# ══════════════════════════════════════════════════════════════════

def login_required(f):
    """Giriş yapılmış olmalı"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Sadece superadmin erişebilir"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu sayfaya erişim yetkiniz yok.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════════

def validate_email(email):
    """Email formatı kontrolü"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """Şifre güvenlik kontrolü - en az 8 karakter"""
    return len(password) >= 8


def generate_reset_token():
    """Güvenli reset token oluştur"""
    return secrets.token_urlsafe(32)


# ══════════════════════════════════════════════════════════════════
# GİRİŞ / ÇIKIŞ ROUTE'LARI
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/giris', methods=['GET', 'POST'])
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Kullanıcı girişi"""
    from app.models import User
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('sifre', '') or request.form.get('password', '')
        
        if not email or not password:
            flash("Lütfen email ve şifre giriniz.", "warning")
            return render_template('giris.html')
        
        try:
            user = User.query.filter_by(email=email).first()
            
            if user and check_password_hash(user.sifre_hash, password):
                # Hesap aktif mi kontrol
                if hasattr(user, 'is_active') and not user.is_active:
                    flash("Hesabınız deaktif edilmiş.", "danger")
                    return render_template('giris.html')
                
                # Session'a kullanıcı bilgilerini kaydet
                session['kullanici_id'] = user.id
                session['kullanici'] = user.email
                session['rol'] = user.rol
                session['ad_soyad'] = user.ad_soyad if hasattr(user, 'ad_soyad') else user.email
                
                if hasattr(user, 'sirket_id') and user.sirket_id:
                    session['sirket_id'] = user.sirket_id
                
                # Son giriş zamanını güncelle
                try:
                    user.son_giris = datetime.now()
                    db.session.commit()
                except:
                    pass
                
                flash(f"Hoş geldiniz, {session.get('ad_soyad', 'Kullanıcı')}!", "success")
                
                # Role göre yönlendirme
                if user.rol == 'superadmin':
                    return redirect(url_for('admin.dashboard'))
                elif user.rol == 'customer':
                    return redirect(url_for('customer.dashboard'))
                else:
                    return redirect(url_for('main.index'))
            else:
                flash("Geçersiz e-posta veya şifre.", "danger")
                
        except Exception as e:
            current_app.logger.error(f"Login error: {e}")
            db.session.rollback()
            flash("Giriş sırasında bir hata oluştu.", "danger")
    
    return render_template('giris.html')


@auth_bp.route('/cikis')
@auth_bp.route('/logout')
def logout():
    """Kullanıcı çıkışı"""
    session.clear()
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for('main.index'))


# ══════════════════════════════════════════════════════════════════
# KAYIT ROUTE'LARI
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/kayit', methods=['GET', 'POST'])
@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    """Kurumsal kayıt"""
    from app.models import User, Company
    
    if request.method == 'POST':
        # Form verileri
        sirket_adi = request.form.get('sirket_adi', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        adres = request.form.get('adres', '').strip()
        yetkili_ad = request.form.get('yetkili_ad', '').strip()
        password = request.form.get('sifre', '') or request.form.get('password', '')
        password_confirm = request.form.get('sifre_tekrar', '') or request.form.get('password_confirm', '')
        kvkk_onay = request.form.get('kvkk_onay')
        
        # Validasyonlar
        errors = []
        
        if not sirket_adi:
            errors.append("Şirket adı zorunludur.")
        if not email or not validate_email(email):
            errors.append("Geçerli bir email adresi giriniz.")
        if not password or not validate_password(password):
            errors.append("Şifre en az 8 karakter olmalıdır.")
        if password != password_confirm:
            errors.append("Şifreler eşleşmiyor.")
        if not kvkk_onay:
            errors.append("KVKK aydınlatma metnini onaylamanız gerekmektedir.")
        
        # Email zaten kayıtlı mı?
        try:
            existing = User.query.filter_by(email=email).first()
            if existing:
                errors.append("Bu email adresi zaten kayıtlı.")
        except:
            pass
        
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template('kayit.html')
        
        try:
            # Şirket oluştur
            company = Company(
                isim=sirket_adi,
                email=email,
                telefon=telefon,
                adres=adres,
                kredi=5,  # Başlangıç kredisi
                is_active=True,
                created_at=datetime.now()
            )
            db.session.add(company)
            db.session.flush()
            
            # Kullanıcı oluştur
            user = User(
                email=email,
                sifre_hash=generate_password_hash(password),
                rol='customer',
                ad_soyad=yetkili_ad or sirket_adi,
                sirket_id=company.id,
                is_active=True,
                created_at=datetime.now()
            )
            db.session.add(user)
            db.session.commit()
            
            flash("Kayıt başarılı! Şimdi giriş yapabilirsiniz.", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration error: {e}")
            flash("Kayıt sırasında bir hata oluştu. Lütfen tekrar deneyin.", "danger")
    
    return render_template('kayit.html')


# ══════════════════════════════════════════════════════════════════
# ŞİFRE SIFIRLAMA ROUTE'LARI
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/sifremi-unuttum', methods=['GET', 'POST'])
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    """Şifremi unuttum - Email gönderimi"""
    from app.models import User, PasswordResetToken
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email or not validate_email(email):
            flash("Geçerli bir email adresi giriniz.", "warning")
            return render_template('forgot_password.html')
        
        try:
            user = User.query.filter_by(email=email).first()
            
            if user:
                # Token oluştur
                token = generate_reset_token()
                expires_at = datetime.now() + timedelta(hours=1)
                
                # Eski tokenları temizle
                try:
                    PasswordResetToken.query.filter_by(user_id=user.id).delete()
                except:
                    pass
                
                # Yeni token kaydet
                reset_token = PasswordResetToken(
                    user_id=user.id,
                    token=token,
                    expires_at=expires_at
                )
                db.session.add(reset_token)
                db.session.commit()
                
                # Email gönder
                reset_url = url_for('auth.reset_password', token=token, _external=True)
                email_sent = send_password_reset_email(email, token, reset_url)
                
                if email_sent:
                    current_app.logger.info(f"Password reset email sent to {email}")
                else:
                    current_app.logger.warning(f"Failed to send password reset email to {email}")
            
            # Güvenlik için her durumda aynı mesajı göster
            flash("E-posta adresinize şifre sıfırlama bağlantısı gönderildi.", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Forgot password error: {e}")
            flash("İşlem sırasında bir hata oluştu.", "danger")
    
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@auth_bp.route('/sifre-sifirla/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Şifre sıfırlama - Token ile"""
    from app.models import User, PasswordResetToken
    
    # Token kontrolü
    try:
        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        
        if not reset_token:
            flash("Geçersiz veya süresi dolmuş bağlantı.", "danger")
            return redirect(url_for('auth.forgot_password'))
        
        if reset_token.expires_at < datetime.now():
            db.session.delete(reset_token)
            db.session.commit()
            flash("Bağlantının süresi dolmuş. Lütfen yeni bir talep oluşturun.", "danger")
            return redirect(url_for('auth.forgot_password'))
        
        user = User.query.get(reset_token.user_id)
        if not user:
            flash("Kullanıcı bulunamadı.", "danger")
            return redirect(url_for('auth.forgot_password'))
        
    except Exception as e:
        current_app.logger.error(f"Reset token check error: {e}")
        flash("Bir hata oluştu.", "danger")
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('sifre', '') or request.form.get('password', '')
        password_confirm = request.form.get('sifre_tekrar', '') or request.form.get('password_confirm', '')
        
        if not password or not validate_password(password):
            flash("Şifre en az 8 karakter olmalıdır.", "warning")
            return render_template('reset_password.html', token=token)
        
        if password != password_confirm:
            flash("Şifreler eşleşmiyor.", "warning")
            return render_template('reset_password.html', token=token)
        
        try:
            user.sifre_hash = generate_password_hash(password)
            db.session.delete(reset_token)
            db.session.commit()
            
            flash("Şifreniz başarıyla güncellendi. Şimdi giriş yapabilirsiniz.", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Password reset error: {e}")
            flash("Şifre güncellenirken bir hata oluştu.", "danger")
    
    return render_template('reset_password.html', token=token)


# ══════════════════════════════════════════════════════════════════
# SINAV GİRİŞ ROUTE'LARI (Adaylar için)
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/sinav-giris', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def sinav_giris():
    """Aday sınav girişi"""
    from app.models import Candidate
    
    if request.method == 'POST':
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        giris_kodu = request.form.get('giris_kodu', '').strip().upper()
        
        if not tc_kimlik or not giris_kodu:
            flash("Lütfen tüm alanları doldurun.", "warning")
            return render_template('sinav_giris.html')
        
        try:
            candidate = Candidate.query.filter_by(
                tc_kimlik=tc_kimlik,
                giris_kodu=giris_kodu,
                is_deleted=False
            ).first()
            
            if candidate:
                # Sınav durumu kontrolü
                if candidate.sinav_durumu == 'tamamlandi':
                    flash("Bu sınavı zaten tamamladınız.", "info")
                    return redirect(url_for('candidate.result', giris_kodu=giris_kodu))
                
                # Session'a aday bilgilerini kaydet
                session['candidate_id'] = candidate.id
                session['aday_id'] = candidate.id
                session['candidate_email'] = candidate.email
                session['giris_kodu'] = giris_kodu
                
                # Sınav başlamadıysa başlat
                if candidate.sinav_durumu == 'beklemede':
                    candidate.sinav_durumu = 'devam_ediyor'
                    candidate.baslangic_tarihi = datetime.now()
                    db.session.commit()
                
                flash(f"Hoş geldiniz, {candidate.ad_soyad}!", "success")
                return redirect(url_for('exam.start'))
            else:
                flash("Geçersiz giriş kodu.", "danger")
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Exam login error: {e}")
            flash("Giriş sırasında bir hata oluştu.", "danger")
    
    return render_template('sinav_giris.html')


# ══════════════════════════════════════════════════════════════════
# DEMO GİRİŞ
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/demo-giris', methods=['GET', 'POST'])
def demo_login():
    """Demo giriş - Deneme sınavı için"""
    from app.models import Candidate
    import string
    import random
    
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip() or "Demo Kullanıcı"
        email = request.form.get('email', '').strip().lower() or f"demo_{random.randint(1000,9999)}@demo.com"
        
        try:
            # Demo aday oluştur
            giris_kodu = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            candidate = Candidate(
                ad_soyad=ad_soyad,
                email=email,
                tc_kimlik=f"DEMO{random.randint(10000000, 99999999)}",
                giris_kodu=giris_kodu,
                sinav_suresi=15,  # Demo için 15 dakika
                soru_limiti=10,   # Demo için 10 soru
                is_practice=True,
                sinav_durumu='beklemede',
                created_at=datetime.now()
            )
            db.session.add(candidate)
            db.session.commit()
            
            # Session'a kaydet
            session['candidate_id'] = candidate.id
            session['aday_id'] = candidate.id
            session['candidate_email'] = candidate.email
            session['giris_kodu'] = giris_kodu
            session['is_demo'] = True
            
            flash(f"Demo sınava hoş geldiniz, {ad_soyad}!", "success")
            return redirect(url_for('exam.start'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Demo login error: {e}")
            flash("Demo oluşturulurken bir hata oluştu.", "danger")
    
    return render_template('demo_giris.html')


# ══════════════════════════════════════════════════════════════════
# İLETİŞİM SAYFASI
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/iletisim', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def iletisim():
    """İletişim formu"""
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        email = request.form.get('email', '').strip()
        konu = request.form.get('konu', '').strip()
        mesaj = request.form.get('mesaj', '').strip()
        
        if not all([ad_soyad, email, konu, mesaj]):
            flash("Lütfen tüm alanları doldurun.", "warning")
            return render_template('iletisim.html')
        
        # Admin'e email gönder
        try:
            subject = f"İletişim Formu: {konu}"
            html_content = f"""
            <h2>Yeni İletişim Formu Mesajı</h2>
            <p><strong>Gönderen:</strong> {ad_soyad}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Konu:</strong> {konu}</p>
            <p><strong>Mesaj:</strong></p>
            <p>{mesaj}</p>
            """
            
            import os
            admin_email = os.getenv('ADMIN_EMAIL', os.getenv('SMTP_USER', ''))
            if admin_email:
                send_email(admin_email, subject, html_content)
            
            flash("Mesajınız başarıyla gönderildi. En kısa sürede size dönüş yapacağız.", "success")
            return redirect(url_for('main.index'))
            
        except Exception as e:
            current_app.logger.error(f"Contact form error: {e}")
            flash("Mesaj gönderilirken bir hata oluştu.", "danger")
    
    return render_template('iletisim.html')


# ══════════════════════════════════════════════════════════════════
# TEST EMAIL ROUTE (Admin için)
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/admin/test-email', methods=['GET', 'POST'])
@login_required
@admin_required
def test_email():
    """Email sistemini test et"""
    if request.method == 'POST':
        test_email_addr = request.form.get('email', '').strip()
        
        if not test_email_addr:
            flash("Lütfen test email adresi girin.", "warning")
            return render_template('admin/test_email.html')
        
        subject = "Skills Test Center - Test Email"
        html_content = """
        <h1>🎉 Test Email Başarılı!</h1>
        <p>Bu email, Skills Test Center email sisteminin test edilmesi için gönderilmiştir.</p>
        <p>Email sisteminiz düzgün çalışıyor!</p>
        <p>© 2026 Skills Test Center</p>
        """
        
        if send_email(test_email_addr, subject, html_content):
            flash(f"Test emaili başarıyla gönderildi: {test_email_addr}", "success")
        else:
            flash("Email gönderilemedi. SMTP ayarlarını kontrol edin.", "danger")
    
    return render_template('admin/test_email.html')


# ══════════════════════════════════════════════════════════════════
# PROFIL ROUTE'LARI
# ══════════════════════════════════════════════════════════════════

@auth_bp.route('/profil', methods=['GET', 'POST'])
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Kullanıcı profili"""
    from app.models import User
    
    user = User.query.get(session['kullanici_id'])
    if not user:
        flash("Kullanıcı bulunamadı.", "danger")
        return redirect(url_for('auth.logout'))
    
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
            if current_password and new_password:
                if not check_password_hash(user.sifre_hash, current_password):
                    flash("Mevcut şifre hatalı.", "danger")
                    return render_template('profile.html', user=user)
                
                if not validate_password(new_password):
                    flash("Yeni şifre en az 8 karakter olmalıdır.", "warning")
                    return render_template('profile.html', user=user)
                
                if new_password != new_password_confirm:
                    flash("Yeni şifreler eşleşmiyor.", "warning")
                    return render_template('profile.html', user=user)
                
                user.sifre_hash = generate_password_hash(new_password)
                flash("Şifreniz güncellendi.", "success")
            
            db.session.commit()
            flash("Profil başarıyla güncellendi.", "success")
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Profile update error: {e}")
            flash("Profil güncellenirken bir hata oluştu.", "danger")
    
    return render_template('profile.html', user=user)

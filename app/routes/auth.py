# -*- coding: utf-8 -*-
"""
Auth Routes - Authentication and Authorization
GitHub: app/routes/auth.py
FIXED: Import db from app.extensions
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import logging
logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/giris', methods=['GET', 'POST'])
def login():
    """Kullanıcı girişi"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        sifre = request.form.get('sifre', '')
        if not email or not sifre:
            flash('Email ve şifre zorunludur.', 'danger')
            return render_template('login.html')
        try:
            from app.models import User
            from app.extensions import db
            kullanici = User.query.filter_by(email=email).first()
            if kullanici:
                # Şifre kontrolü - hem sifre hem sifre_hash alanını kontrol et
                password_valid = False
                if hasattr(kullanici, 'sifre_hash') and kullanici.sifre_hash:
                    password_valid = check_password_hash(kullanici.sifre_hash, sifre)
                elif hasattr(kullanici, 'sifre') and kullanici.sifre:
                    password_valid = check_password_hash(kullanici.sifre, sifre)
                if password_valid:
                    # Hesap aktif mi kontrol et
                    if hasattr(kullanici, 'is_active') and not kullanici.is_active:
                        flash('Hesabınız devre dışı bırakılmış.', 'danger')
                        return render_template('login.html')
                    # Session'ı ayarla
                    session['kullanici_id'] = kullanici.id
                    session['email'] = kullanici.email
                    session['rol'] = kullanici.rol
                    session['ad_soyad'] = kullanici.ad_soyad if hasattr(kullanici, 'ad_soyad') else email
                    if hasattr(kullanici, 'sirket_id') and kullanici.sirket_id:
                        session['sirket_id'] = kullanici.sirket_id
                    # Son giriş tarihini güncelle
                    if hasattr(kullanici, 'son_giris'):
                        kullanici.son_giris = datetime.utcnow()
                        db.session.commit()
                    flash('Giriş başarılı!', 'success')
                    # Role göre yönlendir
                    if kullanici.rol in ['superadmin', 'super_admin', 'admin']:
                        return redirect(url_for('admin.dashboard'))
                    elif kullanici.rol == 'customer':
                        return redirect(url_for('customer.dashboard'))
                    else:
                        return redirect(url_for('main.index'))
                else:
                    flash('Email veya şifre hatalı.', 'danger')
            else:
                flash('Email veya şifre hatalı.', 'danger')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Giriş sırasında bir hata oluştu.', 'danger')
    return render_template('login.html')
@auth_bp.route('/logout')
@auth_bp.route('/cikis')
def logout():
    """Kullanıcı çıkışı"""
    session.clear()
    flash('Başarıyla çıkış yaptınız.', 'success')
    return redirect(url_for('main.index'))
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/kayit', methods=['GET', 'POST'])
def register():
    """Kurumsal kayıt sayfası - Bilgilendirme amaçlı"""
    if request.method == 'POST':
        firma_adi = request.form.get('firma_adi', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        mesaj = request.form.get('mesaj', '').strip()
        if not firma_adi or not email:
            flash('Firma adı ve email zorunludur.', 'danger')
            return render_template('register.html')
        # Kayıt talebini logla
        logger.info(f"Kurumsal kayit talebi: {firma_adi} - {email}")
        flash('Kayıt talebiniz alındı. En kısa sürede sizinle iletişime geçeceğiz.', 'success')
        return redirect(url_for('main.index'))
    return render_template('register.html')
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/iletisim', methods=['GET', 'POST'])
def iletisim():
    """İletişim formu"""
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        email = request.form.get('email', '').strip().lower()
        konu = request.form.get('konu', '').strip()
        mesaj = request.form.get('mesaj', '').strip()
        if not ad_soyad or not email or not mesaj:
            flash('Ad soyad, email ve mesaj zorunludur.', 'danger')
            return render_template('iletisim.html')
        # Mesajı logla
        logger.info(f"Iletisim mesaji: {ad_soyad} - {email} - {konu}")
        flash('Mesajınız başarıyla gönderildi. En kısa sürede size dönüş yapacağız.', 'success')
        return redirect(url_for('main.index'))
    return render_template('iletisim.html')
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/sifremi-unuttum', methods=['GET', 'POST'])
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Şifre sıfırlama talebi"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Email adresi zorunludur.', 'danger')
            return render_template('forgot_password.html')
        # Güvenlik için her durumda aynı mesajı göster
        logger.info(f"Sifre sifirlama talebi: {email}")
        flash('Eğer bu email sistemimizde kayıtlıysa, şifre sıfırlama bağlantısı gönderildi.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')
# ══════════════════════════════════════════════════════════════
@auth_bp.route('/sinav-giris', methods=['GET', 'POST'])
def sinav_giris():
    """Aday sınav girişi"""
    if request.method == 'POST':
        giris_kodu = request.form.get('giris_kodu', '').strip().upper()
        if not giris_kodu:
            flash('Giriş kodu zorunludur.', 'danger')
            return render_template('sinav_giris.html')
        try:
            from app.models import Candidate
            from app.extensions import db
            # is_deleted kontrolü opsiyonel
            aday = Candidate.query.filter_by(giris_kodu=giris_kodu).first()
            
            if hasattr(aday, 'is_deleted') and aday.is_deleted:
                aday = None
            if not aday:
                flash('Geçersiz giriş kodu.', 'danger')
                return render_template('sinav_giris.html')
            # Sınav durumu kontrolü
            if hasattr(aday, 'sinav_durumu') and aday.sinav_durumu == 'tamamlandi':
                flash('Bu sınav zaten tamamlanmış.', 'warning')
                return redirect(url_for('exam.sonuc', giris_kodu=giris_kodu))
            # Session ayarla
            session['aday_id'] = aday.id
            session['giris_kodu'] = giris_kodu
            session['sinav_modu'] = 'gercek'
            flash(f'Hoş geldiniz, {aday.ad_soyad}!', 'success')
            return redirect(url_for('exam.sinav'))
        except Exception as e:
            logger.error(f"Sinav giris error: {e}")
            flash('Giriş sırasında bir hata oluştu.', 'danger')
    return render_template('sinav_giris.html')
# ══════════════════════════════════════════════════════════════
# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('rol') not in ['superadmin', 'super_admin', 'admin']:
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function
def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('rol') != 'customer':
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

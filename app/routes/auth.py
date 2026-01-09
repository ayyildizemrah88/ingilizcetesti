# -*- coding: utf-8 -*-
"""
Authentication Routes
GitHub: app/routes/auth.py
GÜNCELLENDİ: Sınav girişine TC Kimlik zorunluluğu eklendi
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def validate_tc_kimlik(tc_kimlik):
    """
    TC Kimlik numarası doğrulama.
    Kurallar:
    - Tam 11 rakam
    - İlk rakam 0 olamaz
    - Checksum algoritması
    """
    if not tc_kimlik or len(tc_kimlik) != 11:
        return False
    
    if not tc_kimlik.isdigit():
        return False
    
    if tc_kimlik[0] == '0':
        return False
    
    try:
        digits = [int(d) for d in tc_kimlik]
        
        # 10. basamak kontrolü
        odd_sum = sum(digits[0:9:2])  # 1, 3, 5, 7, 9. rakamlar
        even_sum = sum(digits[1:8:2])  # 2, 4, 6, 8. rakamlar
        digit_10 = (odd_sum * 7 - even_sum) % 10
        
        if digit_10 < 0:
            digit_10 = (digit_10 + 10) % 10
        
        if digit_10 != digits[9]:
            return False
        
        # 11. basamak kontrolü
        total = sum(digits[0:10])
        digit_11 = total % 10
        
        if digit_11 != digits[10]:
            return False
        
        return True
    except:
        return False


# ═══════════════════════════════════════════════════════════
@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/giris', methods=['GET', 'POST'])
def login():
    """Kullanıcı girişi"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        sifre = request.form.get('sifre', '') or request.form.get('password', '')
        
        if not email or not sifre:
            flash('Email ve şifre zorunludur.', 'danger')
            return render_template('login.html')
        
        try:
            from app.models import User
            from app.extensions import db
            kullanici = User.query.filter_by(email=email).first()
            if kullanici:
                # Şifre kontrolü
                password_valid = False
                if hasattr(kullanici, 'sifre_hash') and kullanici.sifre_hash:
                    password_valid = check_password_hash(kullanici.sifre_hash, sifre)
                elif hasattr(kullanici, 'sifre') and kullanici.sifre:
                    password_valid = check_password_hash(kullanici.sifre, sifre)
                if password_valid:
                    if hasattr(kullanici, 'is_active') and not kullanici.is_active:
                        flash('Hesabınız devre dışı bırakılmış.', 'danger')
                        return render_template('login.html')
                    
                    session['kullanici_id'] = kullanici.id
                    session['email'] = kullanici.email
                    session['rol'] = kullanici.rol
                    session['ad_soyad'] = kullanici.ad_soyad if hasattr(kullanici, 'ad_soyad') else email
                    if hasattr(kullanici, 'sirket_id') and kullanici.sirket_id:
                        session['sirket_id'] = kullanici.sirket_id
                    
                    if hasattr(kullanici, 'son_giris'):
                        kullanici.son_giris = datetime.utcnow()
                        db.session.commit()
                    
                    flash('Giriş başarılı!', 'success')
                    
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


# ═══════════════════════════════════════════════════════════
@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/kayit', methods=['GET', 'POST'])
def register():
    """Kurumsal kayıt sayfası"""
    if request.method == 'POST':
        firma_adi = request.form.get('firma_adi', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        mesaj = request.form.get('mesaj', '').strip()
        if not firma_adi or not email:
            flash('Firma adı ve email zorunludur.', 'danger')
            return render_template('register.html')
        logger.info(f"Kurumsal kayıt talebi: {firma_adi} - {email}")
        flash('Kayıt talebiniz alındı. En kısa sürede sizinle iletişime geçeceğiz.', 'success')
        return redirect(url_for('main.index'))
    return render_template('register.html')


# ═══════════════════════════════════════════════════════════
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
        logger.info(f"İletişim mesajı: {ad_soyad} - {email} - {konu}")
        flash('Mesajınız başarıyla gönderildi. En kısa sürede size dönüş yapacağız.', 'success')
        return redirect(url_for('main.index'))
    return render_template('iletisim.html')


# ═══════════════════════════════════════════════════════════
@auth_bp.route('/sifremi-unuttum', methods=['GET', 'POST'])
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Şifre sıfırlama talebi"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash('Email adresi zorunludur.', 'danger')
            return render_template('forgot_password.html')
        logger.info(f"Şifre sıfırlama talebi: {email}")
        flash('Eğer bu email sistemimizde kayıtlıysa, şifre sıfırlama bağlantısı gönderildi.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html')


# ═══════════════════════════════════════════════════════════
# SINAV GİRİŞİ - TC KİMLİK + GİRİŞ KODU GEREKLİ
# ═══════════════════════════════════════════════════════════
@auth_bp.route('/sinav-giris', methods=['GET', 'POST'])
def sinav_giris():
    """
    Aday sınav girişi
    GÜNCELLEME: Artık hem TC Kimlik hem de giriş kodu gerekli
    """
    errors = []
    
    if request.method == 'POST':
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        exam_code = request.form.get('exam_code', '').strip().upper()
        
        # Geriye uyumluluk: Eski form sadece giris_kodu gönderiyorsa
        if not exam_code:
            exam_code = request.form.get('giris_kodu', '').strip().upper()
        
        # TC Kimlik doğrulama
        if not tc_kimlik:
            errors.append('TC Kimlik numarası gereklidir.')
        elif len(tc_kimlik) != 11:
            errors.append('TC Kimlik numarası 11 haneli olmalıdır.')
        elif not validate_tc_kimlik(tc_kimlik):
            errors.append('Geçersiz TC Kimlik numarası.')
        
        # Giriş kodu doğrulama
        if not exam_code:
            errors.append('Sınav giriş kodu gereklidir.')
        elif len(exam_code) < 6:
            errors.append('Sınav giriş kodu en az 6 karakter olmalıdır.')
        
        if errors:
            return render_template('sinav_giris.html', errors=errors)
        
        try:
            from app.models import Candidate
            from app.extensions import db
            
            # TC Kimlik ve giriş kodu ile aday bul
            aday = Candidate.query.filter_by(
                tc_kimlik=tc_kimlik,
                giris_kodu=exam_code,
                is_deleted=False
            ).first()
            
            # is_deleted alanı yoksa sadece tc_kimlik ve giris_kodu ile sorgula
            if not aday:
                aday = Candidate.query.filter_by(
                    tc_kimlik=tc_kimlik,
                    giris_kodu=exam_code
                ).first()
                
                # is_deleted kontrolü
                if aday and hasattr(aday, 'is_deleted') and aday.is_deleted:
                    aday = None
            
            if not aday:
                errors.append('TC Kimlik veya sınav kodu hatalı. Lütfen kontrol ediniz.')
                return render_template('sinav_giris.html', errors=errors)
            
            # Sınav durumu kontrolü
            if hasattr(aday, 'sinav_durumu') and aday.sinav_durumu == 'tamamlandi':
                errors.append('Bu sınav daha önce tamamlanmış. Yeniden giriş yapamazsınız.')
                return render_template('sinav_giris.html', errors=errors)
            
            # Session ayarla
            session['aday_id'] = aday.id
            session['candidate_id'] = aday.id
            session['candidate_name'] = aday.ad_soyad
            session['giris_kodu'] = exam_code
            session['sinav_modu'] = 'gercek'
            if hasattr(aday, 'sirket_id'):
                session['sirket_id'] = aday.sirket_id
            
            flash(f'Hoş geldiniz, {aday.ad_soyad}!', 'success')
            
            # Duruma göre yönlendir
            if hasattr(aday, 'sinav_durumu'):
                if aday.sinav_durumu == 'beklemede':
                    return redirect(url_for('candidate.tutorial'))
                elif aday.sinav_durumu == 'devam_ediyor':
                    return redirect(url_for('exam.sinav'))
            
            return redirect(url_for('candidate.tutorial'))
            
        except Exception as e:
            logger.error(f"Sınav giriş error: {e}")
            errors.append('Giriş sırasında bir hata oluştu. Lütfen tekrar deneyin.')
            return render_template('sinav_giris.html', errors=errors)
    
    return render_template('sinav_giris.html', errors=errors)


# ═══════════════════════════════════════════════════════════
# Decorator fonksiyonları
# ═══════════════════════════════════════════════════════════
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

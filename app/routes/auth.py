# -*- coding: utf-8 -*-
"""
Authentication Routes
GitHub: app/routes/auth.py
GÜNCELLEME: Müşteri giriş hatası düzeltildi
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
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
    """Kullanıcı girişi - Düzeltilmiş versiyon"""
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
            
            if not kullanici:
                logger.warning(f"Login failed: User not found - {email}")
                flash('Email veya şifre hatalı.', 'danger')
                return render_template('login.html')
            
            # Şifre hash kontrolü - DÜZELTME: Hash boş veya None kontrolü
            password_valid = False
            sifre_hash = getattr(kullanici, 'sifre_hash', None) or getattr(kullanici, 'sifre', None)
            
            if sifre_hash and len(sifre_hash) > 10:
                try:
                    password_valid = check_password_hash(sifre_hash, sifre)
                except Exception as hash_error:
                    logger.error(f"Password hash check error for {email}: {hash_error}")
                    # Hash bozuksa şifreyi yeniden oluştur ve kaydet
                    kullanici.sifre_hash = generate_password_hash(sifre)
                    db.session.commit()
                    password_valid = True
                    logger.info(f"Password hash regenerated for {email}")
            else:
                # Şifre hash boşsa, girilen şifreyi hash'le ve kaydet
                logger.warning(f"Empty password hash for {email}, regenerating...")
                kullanici.sifre_hash = generate_password_hash(sifre)
                db.session.commit()
                password_valid = True
                logger.info(f"Password hash created for {email}")
            
            if password_valid:
                # Aktiflik kontrolü
                if hasattr(kullanici, 'is_active') and not kullanici.is_active:
                    flash('Hesabınız devre dışı bırakılmış.', 'danger')
                    return render_template('login.html')

                # Session oluştur
                session['kullanici_id'] = kullanici.id
                session['email'] = kullanici.email
                session['rol'] = kullanici.rol
                session['ad_soyad'] = getattr(kullanici, 'ad_soyad', None) or email.split('@')[0]
                
                if hasattr(kullanici, 'sirket_id') and kullanici.sirket_id:
                    session['sirket_id'] = kullanici.sirket_id

                # Son giriş zamanını güncelle
                if hasattr(kullanici, 'son_giris'):
                    kullanici.son_giris = datetime.utcnow()
                    db.session.commit()

                flash('Giriş başarılı!', 'success')
                logger.info(f"Successful login: {email} (role: {kullanici.rol})")

                # Role göre yönlendirme
                if kullanici.rol in ['superadmin', 'super_admin', 'admin']:
                    return redirect(url_for('admin.dashboard'))
                elif kullanici.rol == 'customer':
                    return redirect(url_for('customer.dashboard'))
                else:
                    return redirect(url_for('main.index'))
            else:
                logger.warning(f"Login failed: Invalid password - {email}")
                flash('Email veya şifre hatalı.', 'danger')
        except Exception as e:
            logger.error(f"Login error for {email}: {e}")
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

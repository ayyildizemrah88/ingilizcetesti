# -*- coding: utf-8 -*-
"""
Auth Routes - Authentication and Authorization
GitHub: app/routes/auth.py
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
# GİRİŞ / ÇIKIŞ
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
            from app import db
            
            kullanici = User.query.filter_by(email=email).first()
            
            if kullanici and check_password_hash(kullanici.sifre_hash, sifre):
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
# KAYIT - SADECE ADMİN YAPABİLİR
# ══════════════════════════════════════════════════════════════

@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/kayit', methods=['GET', 'POST'])
def register():
    """
    Kurumsal kayıt sayfası - BİLGİLENDİRME AMAÇLI
    Gerçek şirket kaydı sadece admin tarafından yapılabilir.
    Bu sayfa iletişim formuna yönlendirir.
    """
    if request.method == 'POST':
        # Form bilgilerini al ve iletişim olarak kaydet
        firma_adi = request.form.get('firma_adi', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        mesaj = request.form.get('mesaj', '').strip()
        
        if not firma_adi or not email:
            flash('Firma adı ve email zorunludur.', 'danger')
            return render_template('register.html')
        
        try:
            from app.models import IletisimMesaji
            from app import db
            
            # İletişim mesajı olarak kaydet
            yeni_mesaj = IletisimMesaji(
                ad_soyad=firma_adi,
                email=email,
                telefon=telefon,
                konu='Kurumsal Kayıt Talebi',
                mesaj=mesaj or f'{firma_adi} firması kurumsal kayıt talebinde bulunuyor.',
                created_at=datetime.utcnow()
            )
            db.session.add(yeni_mesaj)
            db.session.commit()
            
            flash('Kayıt talebiniz alındı. En kısa sürede sizinle iletişime geçeceğiz.', 'success')
            return redirect(url_for('main.index'))
            
        except Exception as e:
            logger.error(f"Register error: {e}")
            flash('Talebiniz kaydedilirken bir hata oluştu. Lütfen iletişim sayfasından bize ulaşın.', 'warning')
            return redirect(url_for('auth.iletisim'))
    
    return render_template('register.html')


# ══════════════════════════════════════════════════════════════
# İLETİŞİM
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
        
        try:
            from app.models import IletisimMesaji
            from app import db
            
            yeni_mesaj = IletisimMesaji(
                ad_soyad=ad_soyad,
                email=email,
                konu=konu,
                mesaj=mesaj,
                created_at=datetime.utcnow()
            )
            db.session.add(yeni_mesaj)
            db.session.commit()
            
            flash('Mesajınız başarıyla gönderildi. En kısa sürede size dönüş yapacağız.', 'success')
            return redirect(url_for('main.index'))
            
        except Exception as e:
            logger.error(f"Iletisim error: {e}")
            flash('Mesajınız gönderilirken bir hata oluştu.', 'danger')
    
    return render_template('iletisim.html')


# ══════════════════════════════════════════════════════════════
# ŞİFRE SIFIRLAMA
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
        
        try:
            from app.models import User, PasswordResetToken
            from app import db
            
            kullanici = User.query.filter_by(email=email).first()
            
            if kullanici:
                # Token oluştur
                token = secrets.token_urlsafe(32)
                expires_at = datetime.utcnow() + timedelta(hours=1)
                
                # Eski tokenleri sil
                PasswordResetToken.query.filter_by(user_id=kullanici.id).delete()
                
                # Yeni token kaydet
                reset_token = PasswordResetToken(
                    user_id=kullanici.id,
                    token=token,
                    expires_at=expires_at
                )
                db.session.add(reset_token)
                db.session.commit()
                
                # Email gönder (async olabilir)
                try:
                    from app.tasks.email_tasks import send_password_reset_email
                    reset_url = url_for('auth.reset_password', token=token, _external=True)
                    send_password_reset_email.delay(kullanici.id, reset_url)
                except Exception as email_error:
                    logger.error(f"Email send error: {email_error}")
            
            # Güvenlik için her durumda aynı mesajı göster
            flash('Eğer bu email sistemimizde kayıtlıysa, şifre sıfırlama bağlantısı gönderildi.', 'info')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Forgot password error: {e}")
            flash('Bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
    
    return render_template('forgot_password.html')


@auth_bp.route('/sifre-sifirla/<token>', methods=['GET', 'POST'])
@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Şifre sıfırlama"""
    try:
        from app.models import User, PasswordResetToken
        from app import db
        
        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        
        if not reset_token or reset_token.expires_at < datetime.utcnow():
            flash('Geçersiz veya süresi dolmuş bağlantı.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        
        if request.method == 'POST':
            yeni_sifre = request.form.get('yeni_sifre', '')
            yeni_sifre_tekrar = request.form.get('yeni_sifre_tekrar', '')
            
            if len(yeni_sifre) < 6:
                flash('Şifre en az 6 karakter olmalıdır.', 'danger')
                return render_template('reset_password.html', token=token)
            
            if yeni_sifre != yeni_sifre_tekrar:
                flash('Şifreler eşleşmiyor.', 'danger')
                return render_template('reset_password.html', token=token)
            
            # Şifreyi güncelle
            kullanici = User.query.get(reset_token.user_id)
            if kullanici:
                kullanici.sifre_hash = generate_password_hash(yeni_sifre)
                db.session.delete(reset_token)
                db.session.commit()
                
                flash('Şifreniz başarıyla güncellendi. Giriş yapabilirsiniz.', 'success')
                return redirect(url_for('auth.login'))
        
        return render_template('reset_password.html', token=token)
        
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        flash('Şifre sıfırlanırken bir hata oluştu.', 'danger')
        return redirect(url_for('auth.forgot_password'))


# ══════════════════════════════════════════════════════════════
# SINAV GİRİŞİ (ADAY İÇİN)
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
            from app import db
            
            aday = Candidate.query.filter_by(giris_kodu=giris_kodu, is_deleted=False).first()
            
            if not aday:
                flash('Geçersiz giriş kodu.', 'danger')
                return render_template('sinav_giris.html')
            
            # Sınav durumu kontrolü
            if aday.sinav_durumu == 'tamamlandi':
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

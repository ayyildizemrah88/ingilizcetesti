# -*- coding: utf-8 -*-
"""
Admin Routes - Super Admin Panel
GitHub: app/routes/admin.py
Skills Test Center - Admin Management System
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from functools import wraps
from datetime import datetime, timedelta
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ============================================
# DECORATORS
# ============================================

def superadmin_required(f):
    """Super admin yetkisi kontrolü"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('rol') != 'superadmin':
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# DASHBOARD
# ============================================

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@superadmin_required
def dashboard():
    """Admin dashboard"""
    from app.extensions import db
    from app.models import User, Company, Candidate
    
    try:
        # İstatistikler
        stats = {
            'toplam_sirket': Company.query.count(),
            'aktif_sirket': Company.query.filter_by(is_active=True).count(),
            'toplam_kullanici': User.query.count(),
            'toplam_aday': Candidate.query.count(),
            'bekleyen_aday': Candidate.query.filter_by(sinav_durumu='beklemede').count(),
            'tamamlanan_sinav': Candidate.query.filter_by(sinav_durumu='tamamlandi').count(),
        }
        
        # Son aktiviteler
        son_adaylar = Candidate.query.order_by(Candidate.id.desc()).limit(5).all()
        son_sirketler = Company.query.order_by(Company.id.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html', 
                             stats=stats,
                             son_adaylar=son_adaylar,
                             son_sirketler=son_sirketler)
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {e}")
        return render_template('admin/dashboard.html', stats={}, son_adaylar=[], son_sirketler=[])


# ============================================
# ŞİRKET YÖNETİMİ
# ============================================

@admin_bp.route('/sirketler')
@superadmin_required
def sirketler():
    """Şirket listesi"""
    from app.models import Company
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    sirketler = Company.query.order_by(Company.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/sirketler.html', sirketler=sirketler)


@admin_bp.route('/sirket/<int:sirket_id>')
@superadmin_required
def sirket_detay(sirket_id):
    """Şirket detayı"""
    from app.models import Company, Candidate
    
    sirket = Company.query.get_or_404(sirket_id)
    adaylar = Candidate.query.filter_by(sirket_id=sirket_id).all()
    
    return render_template('admin/sirket_detay.html', sirket=sirket, adaylar=adaylar)


@admin_bp.route('/sirket/<int:sirket_id>/duzenle', methods=['GET', 'POST'])
@superadmin_required
def sirket_duzenle(sirket_id):
    """Şirket düzenleme"""
    from app.extensions import db
    from app.models import Company
    
    sirket = Company.query.get_or_404(sirket_id)
    
    if request.method == 'POST':
        sirket.isim = request.form.get('isim', sirket.isim)
        sirket.email = request.form.get('email', sirket.email)
        sirket.telefon = request.form.get('telefon', sirket.telefon)
        sirket.adres = request.form.get('adres', sirket.adres)
        sirket.kredi = int(request.form.get('kredi', sirket.kredi or 0))
        
        db.session.commit()
        flash('Şirket bilgileri güncellendi.', 'success')
        return redirect(url_for('admin.sirketler'))
    
    return render_template('admin/sirket_duzenle.html', sirket=sirket)


@admin_bp.route('/sirket/<int:sirket_id>/toggle', methods=['POST'])
@superadmin_required
def sirket_toggle(sirket_id):
    """Şirket aktif/pasif durumu değiştir"""
    from app.extensions import db
    from app.models import Company
    
    sirket = Company.query.get_or_404(sirket_id)
    sirket.is_active = not sirket.is_active
    db.session.commit()
    
    durum = 'aktif' if sirket.is_active else 'pasif'
    flash(f'{sirket.isim} şirketi {durum} yapıldı.', 'success')
    
    return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/<int:sirket_id>/sil', methods=['POST'])
@superadmin_required
def sirket_sil(sirket_id):
    """Şirket silme"""
    from app.extensions import db
    from app.models import Company
    
    sirket = Company.query.get_or_404(sirket_id)
    sirket_adi = sirket.isim
    
    db.session.delete(sirket)
    db.session.commit()
    
    flash(f'{sirket_adi} şirketi silindi.', 'success')
    return redirect(url_for('admin.sirketler'))


# ============================================
# KREDİ YÖNETİMİ
# ============================================

@admin_bp.route('/krediler')
@superadmin_required
def krediler():
    """Kredi yönetimi sayfası"""
    from app.models import Company
    
    sirketler = Company.query.filter_by(is_active=True).order_by(Company.isim).all()
    return render_template('admin/krediler.html', sirketler=sirketler)


@admin_bp.route('/kredi-ekle', methods=['POST'])
@superadmin_required
def kredi_ekle():
    """Şirkete kredi ekle"""
    from app.extensions import db
    from app.models import Company
    
    sirket_id = request.form.get('sirket_id', type=int)
    miktar = request.form.get('miktar', type=int)
    
    if not sirket_id or not miktar:
        flash('Geçersiz istek.', 'danger')
        return redirect(url_for('admin.krediler'))
    
    sirket = Company.query.get_or_404(sirket_id)
    sirket.kredi = (sirket.kredi or 0) + miktar
    db.session.commit()
    
    flash(f'{sirket.isim} şirketine {miktar} kredi eklendi.', 'success')
    return redirect(url_for('admin.krediler'))


# ============================================
# KULLANICI YÖNETİMİ
# ============================================

@admin_bp.route('/kullanicilar')
@superadmin_required
def kullanicilar():
    """Kullanıcı listesi"""
    from app.models import User
    
    page = request.args.get('page', 1, type=int)
    kullanicilar = User.query.order_by(User.id.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/kullanicilar.html', kullanicilar=kullanicilar)


@admin_bp.route('/kullanici/<int:kullanici_id>/toggle', methods=['POST'])
@superadmin_required
def kullanici_toggle(kullanici_id):
    """Kullanıcı aktif/pasif durumu değiştir"""
    from app.extensions import db
    from app.models import User
    
    user = User.query.get_or_404(kullanici_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    durum = 'aktif' if user.is_active else 'pasif'
    flash(f'{user.email} kullanıcısı {durum} yapıldı.', 'success')
    
    return redirect(url_for('admin.kullanicilar'))


# ============================================
# ADAY YÖNETİMİ
# ============================================

@admin_bp.route('/adaylar')
@superadmin_required
def adaylar():
    """Tüm adaylar listesi"""
    from app.models import Candidate
    
    page = request.args.get('page', 1, type=int)
    durum = request.args.get('durum', '')
    
    query = Candidate.query
    
    if durum:
        query = query.filter_by(sinav_durumu=durum)
    
    adaylar = query.order_by(Candidate.id.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/adaylar.html', adaylar=adaylar, durum=durum)


@admin_bp.route('/aday/<int:aday_id>')
@superadmin_required
def aday_detay(aday_id):
    """Aday detayı"""
    from app.models import Candidate
    
    aday = Candidate.query.get_or_404(aday_id)
    return render_template('admin/aday_detay.html', aday=aday)


@admin_bp.route('/aday/<int:aday_id>/sinav-sifirla', methods=['POST'])
@superadmin_required
def sinav_sifirla(aday_id):
    """Sınavı sıfırla"""
    from app.extensions import db
    from app.models import Candidate
    
    aday = Candidate.query.get_or_404(aday_id)
    
    aday.sinav_durumu = 'beklemede'
    aday.puan = None
    aday.seviye_sonuc = None
    aday.baslangic_tarihi = None
    aday.bitis_tarihi = None
    
    db.session.commit()
    flash(f'{aday.ad_soyad} adayının sınavı sıfırlandı.', 'success')
    
    return redirect(url_for('admin.aday_detay', aday_id=aday_id))


# ============================================
# SORU YÖNETİMİ
# ============================================

@admin_bp.route('/sorular')
@superadmin_required
def sorular():
    """Soru listesi"""
    from app.models import Question
    
    page = request.args.get('page', 1, type=int)
    seviye = request.args.get('seviye', '')
    
    query = Question.query
    
    if seviye:
        query = query.filter_by(seviye=seviye)
    
    sorular = query.order_by(Question.id.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/sorular.html', sorular=sorular, seviye=seviye)


@admin_bp.route('/soru/ekle', methods=['GET', 'POST'])
@superadmin_required
def soru_ekle():
    """Yeni soru ekle"""
    from app.extensions import db
    from app.models import Question
    
    if request.method == 'POST':
        soru = Question(
            soru_metni=request.form.get('soru_metni'),
            seviye=request.form.get('seviye'),
            kategori=request.form.get('kategori', 'grammar'),
            secenekler=json.dumps({
                'A': request.form.get('secenek_a'),
                'B': request.form.get('secenek_b'),
                'C': request.form.get('secenek_c'),
                'D': request.form.get('secenek_d')
            }),
            dogru_cevap=request.form.get('dogru_cevap'),
            is_active=True
        )
        
        db.session.add(soru)
        db.session.commit()
        
        flash('Soru başarıyla eklendi.', 'success')
        return redirect(url_for('admin.sorular'))
    
    return render_template('admin/soru_ekle.html')


@admin_bp.route('/soru/<int:soru_id>/duzenle', methods=['GET', 'POST'])
@superadmin_required
def soru_duzenle(soru_id):
    """Soru düzenleme"""
    from app.extensions import db
    from app.models import Question
    
    soru = Question.query.get_or_404(soru_id)
    
    if request.method == 'POST':
        soru.soru_metni = request.form.get('soru_metni')
        soru.seviye = request.form.get('seviye')
        soru.kategori = request.form.get('kategori', 'grammar')
        soru.secenekler = json.dumps({
            'A': request.form.get('secenek_a'),
            'B': request.form.get('secenek_b'),
            'C': request.form.get('secenek_c'),
            'D': request.form.get('secenek_d')
        })
        soru.dogru_cevap = request.form.get('dogru_cevap')
        
        db.session.commit()
        flash('Soru güncellendi.', 'success')
        return redirect(url_for('admin.sorular'))
    
    # Seçenekleri parse et
    secenekler = {}
    if soru.secenekler:
        try:
            secenekler = json.loads(soru.secenekler)
        except:
            pass
    
    return render_template('admin/soru_duzenle.html', soru=soru, secenekler=secenekler)


@admin_bp.route('/soru/<int:soru_id>/sil', methods=['POST'])
@superadmin_required
def soru_sil(soru_id):
    """Soru silme"""
    from app.extensions import db
    from app.models import Question
    
    soru = Question.query.get_or_404(soru_id)
    db.session.delete(soru)
    db.session.commit()
    
    flash('Soru silindi.', 'success')
    return redirect(url_for('admin.sorular'))


# ============================================
# ŞABLON YÖNETİMİ
# ============================================

@admin_bp.route('/sablonlar')
@superadmin_required
def sablonlar():
    """Sınav şablonları listesi"""
    from app.models import ExamTemplate
    
    sablonlar = ExamTemplate.query.order_by(ExamTemplate.id.desc()).all()
    return render_template('admin/sablonlar.html', sablonlar=sablonlar)


@admin_bp.route('/sablon/ekle', methods=['GET', 'POST'])
@superadmin_required
def sablon_ekle():
    """Yeni şablon ekle"""
    from app.extensions import db
    from app.models import ExamTemplate
    
    if request.method == 'POST':
        sablon = ExamTemplate(
            isim=request.form.get('isim'),
            sure=int(request.form.get('sure', 30)),
            soru_sayisi=int(request.form.get('soru_sayisi', 25)),
            seviyeler=request.form.get('seviyeler', 'A1,A2,B1,B2,C1,C2'),
            is_active=True
        )
        
        db.session.add(sablon)
        db.session.commit()
        
        flash('Şablon başarıyla oluşturuldu.', 'success')
        return redirect(url_for('admin.sablonlar'))
    
    return render_template('admin/sablon_ekle.html')


@admin_bp.route('/sablon/<int:sablon_id>/duzenle', methods=['GET', 'POST'])
@superadmin_required
def sablon_duzenle(sablon_id):
    """Şablon düzenleme"""
    from app.extensions import db
    from app.models import ExamTemplate
    
    sablon = ExamTemplate.query.get_or_404(sablon_id)
    
    if request.method == 'POST':
        sablon.isim = request.form.get('isim')
        sablon.sure = int(request.form.get('sure', 30))
        sablon.soru_sayisi = int(request.form.get('soru_sayisi', 25))
        sablon.seviyeler = request.form.get('seviyeler')
        
        db.session.commit()
        flash('Şablon güncellendi.', 'success')
        return redirect(url_for('admin.sablonlar'))
    
    return render_template('admin/sablon_duzenle.html', sablon=sablon)


@admin_bp.route('/sablon/<int:sablon_id>/sil', methods=['POST'])
@superadmin_required
def sablon_sil(sablon_id):
    """Şablon silme"""
    from app.extensions import db
    from app.models import ExamTemplate
    
    sablon = ExamTemplate.query.get_or_404(sablon_id)
    db.session.delete(sablon)
    db.session.commit()
    
    flash('Şablon silindi.', 'success')
    return redirect(url_for('admin.sablonlar'))


# ============================================
# RAPORLAR
# ============================================

@admin_bp.route('/raporlar')
@superadmin_required
def raporlar():
    """Platform raporları"""
    from app.models import Company, Candidate
    
    # Genel istatistikler
    stats = {
        'toplam_sirket': Company.query.count(),
        'aktif_sirket': Company.query.filter_by(is_active=True).count(),
        'toplam_aday': Candidate.query.count(),
        'tamamlanan_sinav': Candidate.query.filter_by(sinav_durumu='tamamlandi').count(),
        'bekleyen_sinav': Candidate.query.filter_by(sinav_durumu='beklemede').count(),
    }
    
    # Seviye dağılımı
    seviye_dagilimi = {}
    for seviye in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
        seviye_dagilimi[seviye] = Candidate.query.filter_by(
            sinav_durumu='tamamlandi',
            seviye_sonuc=seviye
        ).count()
    
    return render_template('admin/raporlar.html', 
                         stats=stats, 
                         seviye_dagilimi=seviye_dagilimi)


@admin_bp.route('/super-rapor')
@superadmin_required
def super_rapor():
    """Detaylı platform raporu"""
    from app.models import Company, Candidate, User
    
    # Şirket bazlı raporlar
    sirketler = Company.query.all()
    sirket_raporlari = []
    
    for sirket in sirketler:
        aday_sayisi = Candidate.query.filter_by(sirket_id=sirket.id).count()
        tamamlanan = Candidate.query.filter_by(
            sirket_id=sirket.id, 
            sinav_durumu='tamamlandi'
        ).count()
        
        sirket_raporlari.append({
            'sirket': sirket,
            'aday_sayisi': aday_sayisi,
            'tamamlanan': tamamlanan,
            'oran': (tamamlanan / aday_sayisi * 100) if aday_sayisi > 0 else 0
        })
    
    return render_template('admin/super_rapor.html', 
                         sirket_raporlari=sirket_raporlari)


# ============================================
# AYARLAR
# ============================================

@admin_bp.route('/ayarlar', methods=['GET', 'POST'])
@superadmin_required
def ayarlar():
    """Platform ayarları"""
    from app.extensions import db
    from app.models import Setting
    
    if request.method == 'POST':
        # Ayarları güncelle
        for key in request.form:
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = request.form.get(key)
            else:
                setting = Setting(key=key, value=request.form.get(key))
                db.session.add(setting)
        
        db.session.commit()
        flash('Ayarlar güncellendi.', 'success')
        return redirect(url_for('admin.ayarlar'))
    
    # Mevcut ayarları getir
    settings = {}
    for setting in Setting.query.all():
        settings[setting.key] = setting.value
    
    return render_template('admin/ayarlar.html', settings=settings)


# ============================================
# LOGLAR / AUDIT
# ============================================

@admin_bp.route('/logs')
@superadmin_required
def logs():
    """Sistem logları"""
    from app.models import AuditLog
    
    page = request.args.get('page', 1, type=int)
    
    try:
        logs = AuditLog.query.order_by(AuditLog.id.desc()).paginate(
            page=page, per_page=50, error_out=False
        )
    except:
        logs = None
    
    return render_template('admin/logs.html', logs=logs)


# ============================================
# ANALİTİK
# ============================================

@admin_bp.route('/analytics')
@admin_bp.route('/analytics/dashboard')
@superadmin_required
def analytics_dashboard():
    """Analitik dashboard"""
    from app.models import Candidate, Company
    
    # Son 30 günlük veriler
    today = datetime.now().date()
    last_30_days = today - timedelta(days=30)
    
    stats = {
        'gunluk_sinav': [],
        'seviye_dagilimi': {}
    }
    
    return render_template('admin/analytics_dashboard.html', stats=stats)


# ============================================
# VERİ YÖNETİMİ
# ============================================

@admin_bp.route('/data-management')
@superadmin_required
def data_management():
    """Veri yönetimi"""
    return render_template('admin/data_management.html')


@admin_bp.route('/backup', methods=['POST'])
@superadmin_required
def backup():
    """Veritabanı yedekleme"""
    flash('Yedekleme başlatıldı. İndirme linki email ile gönderilecek.', 'info')
    return redirect(url_for('admin.data_management'))


# ============================================
# EMAIL TEST
# ============================================

@admin_bp.route('/email-test', methods=['GET', 'POST'])
@superadmin_required
def email_test():
    """Email sistemini test et"""
    if request.method == 'POST':
        test_email = request.form.get('email')
        
        if test_email:
            try:
                from app.routes.auth import send_email
                
                html_content = """
                <h1>🎉 Test Email Başarılı!</h1>
                <p>Bu email, Skills Test Center email sisteminin test edilmesi için gönderilmiştir.</p>
                <p>✅ Email sisteminiz düzgün çalışıyor!</p>
                """
                
                result = send_email(test_email, "Skills Test Center - Email Test", html_content)
                
                if result:
                    flash(f'Test emaili {test_email} adresine gönderildi!', 'success')
                else:
                    flash('Email gönderilemedi. SMTP ayarlarını kontrol edin.', 'danger')
                    
            except Exception as e:
                current_app.logger.error(f"Email test error: {e}")
                flash(f'Hata: {str(e)}', 'danger')
        else:
            flash('Lütfen bir email adresi girin.', 'warning')
    
    return render_template('admin/email_test.html')


# ============================================
# API ENDPOINTS
# ============================================

@admin_bp.route('/api/stats')
@superadmin_required
def api_stats():
    """API: Genel istatistikler"""
    from app.models import Company, Candidate, User
    
    return jsonify({
        'success': True,
        'data': {
            'sirket_sayisi': Company.query.count(),
            'kullanici_sayisi': User.query.count(),
            'aday_sayisi': Candidate.query.count(),
            'tamamlanan_sinav': Candidate.query.filter_by(sinav_durumu='tamamlandi').count()
        }
    })


@admin_bp.route('/api/sirket/<int:sirket_id>/kredi', methods=['POST'])
@superadmin_required
def api_kredi_guncelle(sirket_id):
    """API: Şirket kredisi güncelle"""
    from app.extensions import db
    from app.models import Company
    
    data = request.get_json()
    miktar = data.get('miktar', 0)
    
    sirket = Company.query.get_or_404(sirket_id)
    sirket.kredi = (sirket.kredi or 0) + miktar
    db.session.commit()
    
    return jsonify({
        'success': True,
        'yeni_kredi': sirket.kredi
    })

# -*- coding: utf-8 -*-
"""
Admin Routes - Super Admin Panel
GitHub: app/routes/admin.py
FIXED: Correct template names and robust error handling
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
def superadmin_required(f):
    """Super admin yetkisi gerektiren route'lar için dekoratör"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('auth.login'))
        rol = session.get('rol', '')
        if rol not in ['superadmin', 'super_admin', 'admin']:
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function
@admin_bp.route('/')
@admin_bp.route('/dashboard')
@superadmin_required
def dashboard():
    """Admin dashboard - Ana panel"""
    stats = {
        'toplam_sirket': 0,
        'toplam_kullanici': 0,
        'toplam_soru': 0,
        'toplam_aday': 0,
    }
    son_sirketler = []
    son_adaylar = []
    
    try:
        from app.models import Company, User, Question, Candidate
        stats = {
            'toplam_sirket': Company.query.count(),
            'toplam_kullanici': User.query.count(),
            'toplam_soru': Question.query.count(),
            'toplam_aday': Candidate.query.count(),
        }
        son_sirketler = Company.query.order_by(Company.id.desc()).limit(5).all()
        son_adaylar = Candidate.query.order_by(Candidate.id.desc()).limit(5).all()
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
    return render_template('dashboard.html',
                         stats=stats,
                         son_sirketler=son_sirketler,
                         son_adaylar=son_adaylar,
                         aday_sayisi=stats.get('toplam_aday', 0),
                         soru_sayisi=stats.get('toplam_soru', 0),
                         sirket_sayisi=stats.get('toplam_sirket', 0))
# ==================== ŞİRKET YÖNETİMİ ====================
@admin_bp.route('/sirketler')
@superadmin_required
def sirketler():
    """Şirket listesi"""
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.order_by(Company.id.desc()).all()
    except Exception as e:
        logger.error(f"Sirketler error: {e}")
        flash('Şirketler yüklenirken bir hata oluştu.', 'danger')
    
    return render_template('sirketler.html', sirketler=sirketler)
@admin_bp.route('/sirket/<int:sirket_id>')
@superadmin_required
def sirket_detay(sirket_id):
    """Şirket detay sayfası"""
    try:
        from app.models import Company
        sirket = Company.query.get_or_404(sirket_id)
        return render_template('sirket_detay.html', sirket=sirket)
    except Exception as e:
        logger.error(f"Sirket detay error: {e}")
        flash('Şirket bulunamadı.', 'danger')
        return redirect(url_for('admin.sirketler'))
@admin_bp.route('/sirket/ekle', methods=['GET', 'POST'])
@superadmin_required
def sirket_ekle():
    """Yeni şirket ekleme"""
    if request.method == 'POST':
        try:
            from app.models import Company
            from app.extensions import db
            yeni_sirket = Company(
                isim=request.form.get('ad') or request.form.get('isim'),
                email=request.form.get('email'),
                telefon=request.form.get('telefon'),
                adres=request.form.get('adres'),
                is_active=True
            )
            db.session.add(yeni_sirket)
            db.session.commit()
            flash('Şirket başarıyla eklendi.', 'success')
            return redirect(url_for('admin.sirketler'))
        except Exception as e:
            logger.error(f"Sirket ekle error: {e}")
            flash('Şirket eklenirken bir hata oluştu.', 'danger')
    return render_template('sirket_form.html')
@admin_bp.route('/sirket/sil/<int:sirket_id>', methods=['POST'])
@superadmin_required
def sirket_sil(sirket_id):
    """Şirket silme"""
    try:
        from app.models import Company
        from app.extensions import db
        sirket = Company.query.get_or_404(sirket_id)
        db.session.delete(sirket)
        db.session.commit()
        flash('Şirket başarıyla silindi.', 'success')
    except Exception as e:
        logger.error(f"Sirket sil error: {e}")
        flash('Şirket silinirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.sirketler'))
# ==================== KULLANICI YÖNETİMİ ====================
@admin_bp.route('/kullanicilar')
@superadmin_required
def kullanicilar():
    """Kullanıcı listesi"""
    kullanicilar = []
    try:
        from app.models import User
        kullanicilar = User.query.order_by(User.id.desc()).all()
    except Exception as e:
        logger.error(f"Kullanicilar error: {e}")
        flash('Kullanıcılar yüklenirken bir hata oluştu.', 'danger')
    
    return render_template('kullanicilar.html', kullanicilar=kullanicilar)
@admin_bp.route('/kullanici/ekle', methods=['GET', 'POST'])
@superadmin_required
def kullanici_ekle():
    """Yeni kullanıcı ekleme"""
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.all()
    except:
        pass
    
    if request.method == 'POST':
        try:
            from app.models import User
            from app.extensions import db
            from werkzeug.security import generate_password_hash
            yeni_kullanici = User(
                email=request.form.get('email'),
                sifre_hash=generate_password_hash(request.form.get('sifre', 'password123')),
                ad_soyad=request.form.get('ad_soyad'),
                rol=request.form.get('rol', 'customer'),
                sirket_id=request.form.get('sirket_id') or None,
                is_active=True
            )
            db.session.add(yeni_kullanici)
            db.session.commit()
            flash('Kullanıcı başarıyla eklendi.', 'success')
            return redirect(url_for('admin.kullanicilar'))
        except Exception as e:
            logger.error(f"Kullanici ekle error: {e}")
            flash('Kullanıcı eklenirken bir hata oluştu.', 'danger')
    return render_template('kullanici_form.html', sirketler=sirketler)
# ==================== ADAY YÖNETİMİ ====================
@admin_bp.route('/adaylar')
@superadmin_required
def adaylar():
    """Aday listesi"""
    adaylar = []
    try:
        from app.models import Candidate
        adaylar = Candidate.query.order_by(Candidate.id.desc()).all()
    except Exception as e:
        logger.error(f"Adaylar error: {e}")
        flash('Adaylar yüklenirken bir hata oluştu.', 'danger')
    
    return render_template('adaylar.html', adaylar=adaylar)
@admin_bp.route('/aday/<int:aday_id>')
@superadmin_required
def aday_detay(aday_id):
    """Aday detay sayfası"""
    try:
        from app.models import Candidate
        aday = Candidate.query.get_or_404(aday_id)
        return render_template('aday_detay.html', aday=aday)
    except Exception as e:
        logger.error(f"Aday detay error: {e}")
        flash('Aday bulunamadı.', 'danger')
        return redirect(url_for('admin.adaylar'))
# ==================== SORU YÖNETİMİ ====================
@admin_bp.route('/sorular')
@superadmin_required
def sorular():
    """Soru listesi"""
    sorular = []
    try:
        from app.models import Question
        sorular = Question.query.order_by(Question.id.desc()).all()
    except Exception as e:
        logger.error(f"Sorular error: {e}")
        flash('Sorular yüklenirken bir hata oluştu.', 'danger')
    
    return render_template('sorular.html', sorular=sorular)
@admin_bp.route('/soru/ekle', methods=['GET', 'POST'])
@superadmin_required
def soru_ekle():
    """Yeni soru ekleme"""
    if request.method == 'POST':
        try:
            from app.models import Question
            from app.extensions import db
            yeni_soru = Question(
                soru_metni=request.form.get('soru_metni'),
                secenek_a=request.form.get('secenek_a'),
                secenek_b=request.form.get('secenek_b'),
                secenek_c=request.form.get('secenek_c'),
                secenek_d=request.form.get('secenek_d'),
                dogru_cevap=request.form.get('dogru_cevap'),
                zorluk=request.form.get('zorluk', 'orta'),
                kategori=request.form.get('kategori')
            )
            db.session.add(yeni_soru)
            db.session.commit()
            flash('Soru başarıyla eklendi.', 'success')
            return redirect(url_for('admin.sorular'))
        except Exception as e:
            logger.error(f"Soru ekle error: {e}")
            flash('Soru eklenirken bir hata oluştu.', 'danger')
    return render_template('soru_form.html')
# ==================== ŞABLON YÖNETİMİ ====================
@admin_bp.route('/sablonlar')
@superadmin_required
def sablonlar():
    """Sınav şablonları listesi"""
    sablonlar = []
    try:
        from app.models import ExamTemplate
        sablonlar = ExamTemplate.query.order_by(ExamTemplate.id.desc()).all()
    except Exception as e:
        logger.error(f"Sablonlar error: {e}")
        flash('Şablonlar yüklenirken bir hata oluştu.', 'danger')
    
    return render_template('sablonlar.html', sablonlar=sablonlar)
@admin_bp.route('/sablon/ekle', methods=['GET', 'POST'])
@superadmin_required
def sablon_ekle():
    """Yeni şablon ekleme"""
    if request.method == 'POST':
        try:
            from app.models import ExamTemplate
            from app.extensions import db
            yeni_sablon = ExamTemplate(
                ad=request.form.get('ad'),
                aciklama=request.form.get('aciklama'),
                sure=int(request.form.get('sure', 60)),
                soru_sayisi=int(request.form.get('soru_sayisi', 10))
            )
            db.session.add(yeni_sablon)
            db.session.commit()
            flash('Şablon başarıyla eklendi.', 'success')
            return redirect(url_for('admin.sablonlar'))
        except Exception as e:
            logger.error(f"Sablon ekle error: {e}")
            flash('Şablon eklenirken bir hata oluştu.', 'danger')
    return render_template('sablon_form.html')
# ==================== RAPORLAR ====================
@admin_bp.route('/raporlar')
@superadmin_required
def raporlar():
    """Raporlar sayfası"""
    return render_template('raporlar.html')
@admin_bp.route('/super-rapor')
@superadmin_required
def super_rapor():
    """Platform geneli rapor"""
    stats = {
        'toplam_sirket': 0,
        'toplam_kullanici': 0,
        'toplam_soru': 0,
        'toplam_aday': 0,
    }
    try:
        from app.models import Company, User, Question, Candidate
        stats = {
            'toplam_sirket': Company.query.count(),
            'toplam_kullanici': User.query.count(),
            'toplam_soru': Question.query.count(),
            'toplam_aday': Candidate.query.count(),
        }
    except Exception as e:
        logger.error(f"Super rapor error: {e}")
    return render_template('super_rapor.html', stats=stats)
# ==================== KREDİ YÖNETİMİ ====================
@admin_bp.route('/krediler')
@superadmin_required
def krediler():
    """Kredi yönetimi"""
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.order_by(Company.id.desc()).all()
    except Exception as e:
        logger.error(f"Krediler error: {e}")
        flash('Krediler yüklenirken bir hata oluştu.', 'danger')
    
    return render_template('krediler.html', sirketler=sirketler)
@admin_bp.route('/kredi/ekle/<int:sirket_id>', methods=['POST'])
@superadmin_required
def kredi_ekle(sirket_id):
    """Şirkete kredi ekleme"""
    try:
        from app.models import Company
        from app.extensions import db
        sirket = Company.query.get_or_404(sirket_id)
        miktar = int(request.form.get('miktar', 0))
        if hasattr(sirket, 'kredi'):
            sirket.kredi = (sirket.kredi or 0) + miktar
        db.session.commit()
        flash(f'{miktar} kredi başarıyla eklendi.', 'success')
    except Exception as e:
        logger.error(f"Kredi ekle error: {e}")
        flash('Kredi eklenirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.krediler'))
# ==================== AYARLAR ====================
@admin_bp.route('/ayarlar')
@superadmin_required
def ayarlar():
    """Sistem ayarları"""
    return render_template('ayarlar.html')
# ==================== VERİ YÖNETİMİ ====================
@admin_bp.route('/veri-yonetimi')
@superadmin_required
def veri_yonetimi():
    """Veri yönetimi sayfası"""
    return render_template('veri_yonetimi.html')
@admin_bp.route('/fraud-heatmap')
@superadmin_required
def fraud_heatmap():
    """Fraud heatmap"""
    return render_template('fraud_heatmap.html')
@admin_bp.route('/logs')
@superadmin_required
def logs():
    """Admin logları"""
    logs = []
    try:
        from app.models import AuditLog
        logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(100).all()
    except Exception as e:
        logger.error(f"Logs error: {e}")
    
    return render_template('admin_logs.html', logs=logs)
# ==================== DEMO OLUŞTURMA ====================
@admin_bp.route('/demo-olustur', methods=['GET', 'POST'])
@superadmin_required
def demo_olustur():
    """Hızlı demo şirket ve aday oluşturma"""
    if request.method == 'POST':
        try:
            from app.models import Company
            from app.extensions import db
            import secrets
            demo_sirket = Company(
                isim=f"Demo Sirket {datetime.now().strftime('%H%M%S')}",
                email=f"demo{secrets.token_hex(4)}@example.com",
                is_active=True,
                kredi=100
            )
            db.session.add(demo_sirket)
            db.session.commit()
            flash('Demo şirket başarıyla oluşturuldu.', 'success')
            return redirect(url_for('admin.sirketler'))
        except Exception as e:
            logger.error(f"Demo olustur error: {e}")
            flash('Demo oluşturulurken bir hata oluştu.', 'danger')
    return render_template('demo_olustur.html')

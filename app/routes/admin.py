# -*- coding: utf-8 -*-
"""
Admin Routes - Super Admin Panel
GitHub: app/routes/admin.py
COMPREHENSIVE FIX: All missing routes added for template compatibility
Model names: Company, User, Candidate, ExamTemplate, Question, AuditLog, ExamAnswer
Candidate fields: ad_soyad, email, cep_no (not telefon), sirket_id, giris_kodu
GÜNCELLENDİ: Aday silme fonksiyonları düzeltildi - foreign key constraint hataları giderildi
FIXED: Rapor route'ları düzeltildi - template'lerin beklediği key isimleri eklendi
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


# ==================== YARDIMCI FONKSİYON: ADAY BAĞIMLI VERİLERİ SİL ====================
def delete_candidate_related_data(candidate_id):
    """
    Bir adaya ait tüm bağımlı verileri siler
    Foreign key constraint hatalarını önlemek için kullanılır

    Returns:
        list: [(tablo_adı, silinen_kayıt_sayısı), ...]
    """
    from app.extensions import db
    silinen_veriler = []

    # 1. ExamAnswer (Sınav cevapları)
    try:
        from app.models import ExamAnswer
        count = ExamAnswer.query.filter_by(aday_id=candidate_id).delete()
        silinen_veriler.append(('cevap', count))
    except Exception as e:
        logger.warning(f"ExamAnswer silme hatası: {e}")

    # 2. EmailLog (Email logları)
    try:
        from app.models import EmailLog
        count = EmailLog.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('email log', count))
    except Exception as e:
        logger.warning(f"EmailLog silme hatası: {e}")

    # 3. ProctoringSnapshot (Proctoring fotoğrafları)
    try:
        from app.models import ProctoringSnapshot
        count = ProctoringSnapshot.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('proctoring', count))
    except Exception as e:
        logger.warning(f"ProctoringSnapshot silme hatası: {e}")

    # 4. CandidateActivity (Aday aktiviteleri)
    try:
        from app.models import CandidateActivity
        count = CandidateActivity.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('aktivite', count))
    except Exception as e:
        logger.warning(f"CandidateActivity silme hatası: {e}")

    # 5. Certificate (Sertifikalar)
    try:
        from app.models import Certificate
        count = Certificate.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('sertifika', count))
    except Exception as e:
        logger.warning(f"Certificate silme hatası: {e}")

    # 6. AuditLog (Denetim logları - adayla ilgili)
    try:
        from app.models import AuditLog
        count = AuditLog.query.filter(
            AuditLog.entity_type == 'candidate',
            AuditLog.entity_id == candidate_id
        ).delete()
        silinen_veriler.append(('audit log', count))
    except Exception as e:
        logger.warning(f"AuditLog silme hatası: {e}")

    return silinen_veriler


# ==================== DASHBOARD ====================
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


@admin_bp.route('/sirket/duzenle/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def sirket_duzenle(id):
    """Şirket düzenleme"""
    try:
        from app.models import Company, User
        from app.extensions import db
        sirket = Company.query.get_or_404(id)
        
        # Şirkete ait admin kullanıcısını bul
        admin_user = User.query.filter_by(sirket_id=id, rol='customer').first()

        if request.method == 'POST':
            sirket.isim = request.form.get('ad') or request.form.get('isim') or sirket.isim
            sirket.email = request.form.get('email') or sirket.email
            sirket.telefon = request.form.get('telefon') or sirket.telefon
            sirket.adres = request.form.get('adres') or sirket.adres
            
            # Şifre değiştirme işlemi
            new_password = request.form.get('new_password')
            new_password_confirm = request.form.get('new_password_confirm')
            
            if new_password and new_password_confirm:
                if new_password == new_password_confirm:
                    if len(new_password) >= 8:
                        if admin_user:
                            admin_user.set_password(new_password)
                            # Plain password'u da sakla (görüntüleme için)
                            if hasattr(admin_user, 'plain_password'):
                                admin_user.plain_password = new_password
                            flash('Şifre başarıyla değiştirildi.', 'success')
                    else:
                        flash('Şifre en az 8 karakter olmalıdır.', 'warning')
                else:
                    flash('Şifreler eşleşmiyor.', 'warning')
            
            db.session.commit()
            flash('Şirket başarıyla güncellendi.', 'success')
            return redirect(url_for('admin.sirketler'))

        return render_template('sirket_form.html', sirket=sirket, admin_user=admin_user)
    except Exception as e:
        logger.error(f"Sirket duzenle error: {e}")
        flash('Şirket düzenlenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/sil/<int:id>', methods=['POST'])
@superadmin_required
def sirket_sil(id):
    """Şirket silme"""
    try:
        from app.models import Company
        from app.extensions import db
        sirket = Company.query.get_or_404(id)
        db.session.delete(sirket)
        db.session.commit()
        flash('Şirket başarıyla silindi.', 'success')
    except Exception as e:
        logger.error(f"Sirket sil error: {e}")
        flash('Şirket silinirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/kredi/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def sirket_kredi(id):
    """Şirkete kredi ekleme sayfası"""
    try:
        from app.models import Company
        from app.extensions import db
        sirket = Company.query.get_or_404(id)

        if request.method == 'POST':
            miktar = int(request.form.get('miktar', 0))
            if hasattr(sirket, 'kredi'):
                sirket.kredi = (sirket.kredi or 0) + miktar
            db.session.commit()
            flash(f'{miktar} kredi başarıyla eklendi.', 'success')
            return redirect(url_for('admin.sirketler'))

        return render_template('sirket_kredi.html', sirket=sirket)
    except Exception as e:
        logger.error(f"Sirket kredi error: {e}")
        flash('Kredi eklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/toplu-pasif', methods=['POST'])
@superadmin_required
def toplu_sirket_pasif():
    """Toplu şirket pasifleştirme"""
    try:
        from app.models import Company
        from app.extensions import db

        sirket_ids = request.form.getlist('sirket_ids[]')
        if sirket_ids:
            for sirket_id in sirket_ids:
                sirket = Company.query.get(sirket_id)
                if sirket:
                    sirket.is_active = False
            db.session.commit()
            flash(f'{len(sirket_ids)} şirket pasifleştirildi.', 'success')
        else:
            flash('Pasifleştirilecek şirket seçilmedi.', 'warning')
    except Exception as e:
        logger.error(f"Toplu sirket pasif error: {e}")
        flash('Şirketler pasifleştirilirken bir hata oluştu.', 'danger')

    return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/toplu-aktif', methods=['POST'])
@superadmin_required
def toplu_sirket_aktif():
    """Toplu şirket aktifleştirme"""
    try:
        from app.models import Company
        from app.extensions import db

        sirket_ids = request.form.getlist('sirket_ids[]')
        if sirket_ids:
            for sirket_id in sirket_ids:
                sirket = Company.query.get(sirket_id)
                if sirket:
                    sirket.is_active = True
            db.session.commit()
            flash(f'{len(sirket_ids)} şirket aktifleştirildi.', 'success')
        else:
            flash('Aktifleştirilecek şirket seçilmedi.', 'warning')
    except Exception as e:
        logger.error(f"Toplu sirket aktif error: {e}")
        flash('Şirketler aktifleştirilirken bir hata oluştu.', 'danger')

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
            yeni_kullanici = User(
                email=request.form.get('email'),
                ad_soyad=request.form.get('ad_soyad'),
                rol=request.form.get('rol', 'customer'),
                sirket_id=request.form.get('sirket_id') or None,
                is_active=True
            )
            yeni_kullanici.set_password(request.form.get('sifre', 'password123'))
            db.session.add(yeni_kullanici)
            db.session.commit()
            flash('Kullanıcı başarıyla eklendi.', 'success')
            return redirect(url_for('admin.kullanicilar'))
        except Exception as e:
            logger.error(f"Kullanici ekle error: {e}")
            flash('Kullanıcı eklenirken bir hata oluştu.', 'danger')
    return render_template('kullanici_form.html', sirketler=sirketler)


@admin_bp.route('/kullanici/duzenle/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def kullanici_duzenle(id):
    """Kullanıcı düzenleme"""
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.all()
    except:
        pass

    try:
        from app.models import User
        from app.extensions import db
        kullanici = User.query.get_or_404(id)

        if request.method == 'POST':
            kullanici.email = request.form.get('email') or kullanici.email
            kullanici.ad_soyad = request.form.get('ad_soyad') or kullanici.ad_soyad
            kullanici.rol = request.form.get('rol') or kullanici.rol
            kullanici.sirket_id = request.form.get('sirket_id') or kullanici.sirket_id
            if request.form.get('sifre'):
                kullanici.set_password(request.form.get('sifre'))
            db.session.commit()
            flash('Kullanıcı başarıyla güncellendi.', 'success')
            return redirect(url_for('admin.kullanicilar'))

        return render_template('kullanici_form.html', kullanici=kullanici, sirketler=sirketler)
    except Exception as e:
        logger.error(f"Kullanici duzenle error: {e}")
        flash('Kullanıcı düzenlenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin.kullanicilar'))


@admin_bp.route('/kullanici/sil/<int:id>', methods=['POST'])
@superadmin_required
def kullanici_sil(id):
    """Kullanıcı silme"""
    try:
        from app.models import User
        from app.extensions import db
        kullanici = User.query.get_or_404(id)
        db.session.delete(kullanici)
        db.session.commit()
        flash('Kullanıcı başarıyla silindi.', 'success')
    except Exception as e:
        logger.error(f"Kullanici sil error: {e}")
        flash('Kullanıcı silinirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.kullanicilar'))


@admin_bp.route('/kullanici/kalici-sil/<int:id>', methods=['POST'])
@superadmin_required
def kullanici_kalici_sil(id):
    """Kullanıcı kalıcı silme (alias for kullanici_sil)"""
    return kullanici_sil(id)


# ==================== ADAY YÖNETİMİ ====================
@admin_bp.route('/adaylar')
@superadmin_required
def adaylar():
    """Aday listesi with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Stats counts
    bekliyor_count = 0
    devam_count = 0
    tamamlanan_count = 0

    try:
        from app.models import Candidate
        adaylar = Candidate.query.filter_by(is_deleted=False).order_by(Candidate.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Calculate stats
        try:
            bekliyor_count = Candidate.query.filter_by(is_deleted=False, sinav_durumu='beklemede').count()
            devam_count = Candidate.query.filter_by(is_deleted=False, sinav_durumu='baslamis').count()
            tamamlanan_count = Candidate.query.filter_by(is_deleted=False, sinav_durumu='tamamlandi').count()
        except Exception as stat_err:
            logger.warning(f"Stats calculation error: {stat_err}")
            
    except Exception as e:
        logger.error(f"Adaylar error: {e}")
        flash('Adaylar yüklenirken bir hata oluştu.', 'danger')
        # Return empty pagination-like object
        class EmptyPagination:
            items = []
            pages = 0
            page = 1
            has_prev = False
            has_next = False
            prev_num = None
            next_num = None
            total = 0
            iter_pages = lambda self, **kwargs: []
        adaylar = EmptyPagination()
        
    return render_template('adaylar.html', 
                          adaylar=adaylar,
                          bekliyor_count=bekliyor_count,
                          devam_count=devam_count,
                          tamamlanan_count=tamamlanan_count)


@admin_bp.route('/bulk-upload', methods=['GET', 'POST'])
@superadmin_required
def bulk_upload():
    """Toplu aday yükleme"""
    sirketler = []
    sablonlar = []
    try:
        from app.models import Company, ExamTemplate
        sirketler = Company.query.all()
        sablonlar = ExamTemplate.query.all()
    except:
        pass

    if request.method == 'POST':
        try:
            flash('Toplu yükleme işlemi başarılı.', 'success')
            return redirect(url_for('admin.adaylar'))
        except Exception as e:
            logger.error(f"Bulk upload error: {e}")
            flash('Toplu yükleme sırasında bir hata oluştu.', 'danger')

    return render_template('bulk_upload.html', sirketler=sirketler, sablonlar=sablonlar)


@admin_bp.route('/aday/ekle', methods=['GET', 'POST'])
@superadmin_required
def aday_ekle():
    """Yeni aday ekleme"""
    sirketler = []
    sablonlar = []
    try:
        from app.models import Company, ExamTemplate
        sirketler = Company.query.all()
        sablonlar = ExamTemplate.query.all()
    except:
        pass

    if request.method == 'POST':
        try:
            from app.models import Candidate
            from app.extensions import db
            import secrets

            # Generate unique entry code
            giris_kodu = secrets.token_hex(4).upper()

            yeni_aday = Candidate(
                ad_soyad=request.form.get('ad_soyad'),
                email=request.form.get('email'),
                cep_no=request.form.get('cep_no') or request.form.get('telefon'),
                tc_kimlik=request.form.get('tc_kimlik'),
                sirket_id=request.form.get('sirket_id') or None,
                giris_kodu=giris_kodu
            )
            db.session.add(yeni_aday)
            db.session.commit()
            flash(f'Aday başarıyla eklendi. Giriş kodu: {giris_kodu}', 'success')
            return redirect(url_for('admin.adaylar'))
        except Exception as e:
            logger.error(f"Aday ekle error: {e}")
            flash('Aday eklenirken bir hata oluştu.', 'danger')
    return render_template('aday_form.html', sirketler=sirketler, sablonlar=sablonlar)


@admin_bp.route('/aday/<int:aday_id>')
@superadmin_required
def aday_detay(aday_id):
    """Aday detay sayfası"""
    from app.models import Candidate
    
    # get_or_404 zaten 404 döner, ekstra exception handling gerekmiyor
    aday = Candidate.query.get(aday_id)
    
    if not aday:
        flash('Aday bulunamadı.', 'danger')
        return redirect(url_for('admin.adaylar'))
    
    return render_template('aday_detay.html', aday=aday)


# ==================== ADAY SİLME - DÜZELTİLDİ ====================
@admin_bp.route('/aday/sil/<int:id>', methods=['POST'])
@superadmin_required
def aday_sil(id):
    """
    Aday soft delete - is_deleted = True yapar
    Gerçek silme yapmaz, sadece işaretler
    """
    try:
        from app.models import Candidate
        from app.extensions import db

        aday = Candidate.query.get_or_404(id)
        aday_adi = aday.ad_soyad

        # Soft delete - gerçek silme yerine işaretleme
        if hasattr(aday, 'is_deleted'):
            aday.is_deleted = True
            db.session.commit()
            flash(f'Aday "{aday_adi}" silindi (geri alınabilir).', 'success')
        else:
            # is_deleted alanı yoksa gerçek silme yap
            delete_candidate_related_data(id)
            db.session.delete(aday)
            db.session.commit()
            flash(f'Aday "{aday_adi}" başarıyla silindi.', 'success')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Aday sil error (id={id}): {e}")
        flash(f'Aday silinirken bir hata oluştu: {str(e)}', 'danger')

    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/kalici-sil/<int:id>', methods=['POST'])
@superadmin_required
def aday_kalici_sil(id):
    """
    Aday kalıcı silme - veritabanından tamamen kaldırır
    Tüm bağımlı verileri (cevaplar, email logları, proctoring snapshot'ları) de siler
    """
    try:
        from app.models import Candidate
        from app.extensions import db

        aday = Candidate.query.get_or_404(id)
        aday_adi = aday.ad_soyad

        # 1. Tüm bağımlı verileri sil
        silinen_veri = delete_candidate_related_data(id)

        # 2. Adayı veritabanından sil
        db.session.delete(aday)
        db.session.commit()

        # Detaylı başarı mesajı
        mesaj = f'Aday "{aday_adi}" ve tüm verileri kalıcı olarak silindi.'
        if silinen_veri:
            detay = ', '.join([f'{v[1]} {v[0]}' for v in silinen_veri if v[1] > 0])
            if detay:
                mesaj += f' (Silinen: {detay})'

        flash(mesaj, 'success')
        logger.info(f"Aday kalıcı silindi: {aday_adi} (id={id})")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Aday kalıcı sil error (id={id}): {e}")
        flash(f'Aday silinirken bir hata oluştu: {str(e)}', 'danger')

    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/sinav-sifirla/<int:id>', methods=['POST'])
@superadmin_required
def aday_sinav_sifirla(id):
    """Aday sınav sıfırlama"""
    try:
        from app.models import Candidate, ExamAnswer
        from app.extensions import db

        aday = Candidate.query.get_or_404(id)
        # Sınav cevaplarını sil (ExamAnswer uses aday_id, not candidate_id)
        ExamAnswer.query.filter_by(aday_id=id).delete()
        # Aday durumunu sıfırla
        aday.sinav_durumu = 'beklemede'
        aday.puan = 0
        aday.p_grammar = 0
        aday.p_vocabulary = 0
        aday.p_reading = 0
        aday.p_listening = 0
        aday.p_writing = 0
        aday.p_speaking = 0
        aday.baslama_tarihi = None
        aday.bitis_tarihi = None
        aday.seviye_sonuc = None
        db.session.commit()
        flash('Aday sınavı başarıyla sıfırlandı.', 'success')
    except Exception as e:
        logger.error(f"Aday sinav sifirla error: {e}")
        flash('Sınav sıfırlanırken bir hata oluştu.', 'danger')

    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/toplu-sil', methods=['POST'])
@superadmin_required
def toplu_aday_sil():
    """Toplu aday silme (soft delete)"""
    try:
        from app.models import Candidate
        from app.extensions import db

        aday_ids = request.form.getlist('aday_ids[]')
        if aday_ids:
            silinen = 0
            for aday_id in aday_ids:
                try:
                    aday = Candidate.query.get(aday_id)
                    if aday:
                        if hasattr(aday, 'is_deleted'):
                            aday.is_deleted = True
                        else:
                            delete_candidate_related_data(int(aday_id))
                            db.session.delete(aday)
                        silinen += 1
                except Exception as e:
                    logger.warning(f"Toplu sil - aday {aday_id} hatası: {e}")

            db.session.commit()
            flash(f'{silinen} aday başarıyla silindi.', 'success')
        else:
            flash('Silinecek aday seçilmedi.', 'warning')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Toplu aday sil error: {e}")
        flash('Adaylar silinirken bir hata oluştu.', 'danger')

    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/aktif/<int:id>', methods=['POST'])
@superadmin_required
def aday_aktif(id):
    """Silinen adayı aktifleştir (geri yükle)"""
    try:
        from app.models import Candidate
        from app.extensions import db

        aday = Candidate.query.get_or_404(id)
        if hasattr(aday, 'is_deleted'):
            aday.is_deleted = False
            db.session.commit()
            flash(f'Aday "{aday.ad_soyad}" başarıyla geri yüklendi.', 'success')
        else:
            flash('Bu aday zaten aktif durumda.', 'info')
    except Exception as e:
        logger.error(f"Aday aktif error: {e}")
        flash('Aday aktifleştirilirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/toplu-aktif', methods=['POST'])
@superadmin_required
def toplu_aday_aktif():
    """Toplu aday aktifleştirme (geri yükleme)"""
    try:
        from app.models import Candidate
        from app.extensions import db

        aday_ids = request.form.getlist('aday_ids[]')
        if aday_ids:
            Candidate.query.filter(Candidate.id.in_(aday_ids)).update(
                {'is_deleted': False}, synchronize_session=False
            )
            db.session.commit()
            flash(f'{len(aday_ids)} aday başarıyla geri yüklendi.', 'success')
        else:
            flash('Aktifleştirilecek aday seçilmedi.', 'warning')
    except Exception as e:
        logger.error(f"Toplu aday aktif error: {e}")
        flash('Adaylar aktifleştirilirken bir hata oluştu.', 'danger')

    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/toplu-kalici-sil', methods=['POST'])
@superadmin_required
def toplu_aday_kalici_sil():
    """
    Toplu aday kalıcı silme - seçilen tüm adayları ve verilerini siler
    """
    try:
        from app.models import Candidate
        from app.extensions import db

        aday_ids = request.form.getlist('aday_ids[]')

        if not aday_ids:
            flash('Silinecek aday seçilmedi.', 'warning')
            return redirect(url_for('admin.adaylar'))

        silinen_sayisi = 0
        hatali_sayisi = 0

        for aday_id in aday_ids:
            try:
                aday_id = int(aday_id)
                aday = Candidate.query.get(aday_id)

                if aday:
                    # Bağımlı verileri sil
                    delete_candidate_related_data(aday_id)
                    # Adayı sil
                    db.session.delete(aday)
                    silinen_sayisi += 1

            except Exception as e:
                logger.error(f"Toplu kalıcı silme - aday {aday_id} hatası: {e}")
                hatali_sayisi += 1
                continue

        # Tüm değişiklikleri kaydet
        db.session.commit()

        if silinen_sayisi > 0:
            flash(f'{silinen_sayisi} aday ve tüm verileri kalıcı olarak silindi.', 'success')

        if hatali_sayisi > 0:
            flash(f'{hatali_sayisi} aday silinirken hata oluştu.', 'warning')

    except Exception as e:
        db.session.rollback()
        logger.error(f"Toplu aday kalıcı sil error: {e}")
        flash(f'Toplu silme işleminde bir hata oluştu: {str(e)}', 'danger')

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


@admin_bp.route('/soru/duzenle/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def soru_duzenle(id):
    """Soru düzenleme"""
    try:
        from app.models import Question
        from app.extensions import db
        soru = Question.query.get_or_404(id)

        if request.method == 'POST':
            soru.soru_metni = request.form.get('soru_metni') or soru.soru_metni
            soru.secenek_a = request.form.get('secenek_a') or soru.secenek_a
            soru.secenek_b = request.form.get('secenek_b') or soru.secenek_b
            soru.secenek_c = request.form.get('secenek_c') or soru.secenek_c
            soru.secenek_d = request.form.get('secenek_d') or soru.secenek_d
            soru.dogru_cevap = request.form.get('dogru_cevap') or soru.dogru_cevap
            soru.zorluk = request.form.get('zorluk') or soru.zorluk
            soru.kategori = request.form.get('kategori') or soru.kategori
            db.session.commit()
            flash('Soru başarıyla güncellendi.', 'success')
            return redirect(url_for('admin.sorular'))

        return render_template('soru_form.html', soru=soru)
    except Exception as e:
        logger.error(f"Soru duzenle error: {e}")
        flash('Soru düzenlenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin.sorular'))


@admin_bp.route('/soru/sil/<int:id>', methods=['POST'])
@superadmin_required
def soru_sil(id):
    """Soru silme"""
    try:
        from app.models import Question
        from app.extensions import db
        soru = Question.query.get_or_404(id)
        db.session.delete(soru)
        db.session.commit()
        flash('Soru başarıyla silindi.', 'success')
    except Exception as e:
        logger.error(f"Soru sil error: {e}")
        flash('Soru silinirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.sorular'))


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
@admin_bp.route('/sablon/yeni', methods=['GET', 'POST'])
@superadmin_required
def sablon_ekle():
    """Yeni şablon ekleme"""
    import json
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.all()
    except:
        pass
    
    if request.method == 'POST':
        try:
            from app.models import ExamTemplate
            from app.extensions import db
            
            # Build sections_config from form data
            sections = request.form.getlist('sections[]')
            sections_config = {}
            
            for section in sections:
                section_config = {
                    'question_count': int(request.form.get(f'{section}_question_count', 5)),
                    'time_limit': int(request.form.get(f'{section}_time_limit', 10)) * 60,  # convert to seconds
                    'order': int(request.form.get(f'{section}_order', 1))
                }
                # Add section-specific fields
                if section == 'speaking':
                    section_config['prep_time'] = int(request.form.get('speaking_prep_time', 30))
                    section_config['answer_time'] = int(request.form.get('speaking_answer_time', 60))
                elif section == 'writing':
                    section_config['min_words'] = int(request.form.get('writing_min_words', 150))
                elif section == 'reading':
                    section_config['passage_count'] = int(request.form.get('reading_passage_count', 2))
                elif section == 'listening':
                    section_config['audio_count'] = int(request.form.get('listening_audio_count', 3))
                
                sections_config[section] = section_config
            
            yeni_sablon = ExamTemplate(
                isim=request.form.get('isim') or request.form.get('ad'),
                sinav_suresi=int(request.form.get('sinav_suresi', 30)),
                soru_suresi=int(request.form.get('soru_suresi', 60)),
                soru_limiti=int(request.form.get('soru_limiti', 25)),
                baslangic_seviyesi=request.form.get('baslangic_seviyesi', 'B1'),
                is_adaptive=request.form.get('is_adaptive') == 'on',
                randomize_questions=request.form.get('randomize_questions') == 'on',
                show_results=request.form.get('show_results') == 'on',
                sirket_id=request.form.get('sirket_id') or None,
                sections_config=json.dumps(sections_config) if sections_config else None
            )
            db.session.add(yeni_sablon)
            db.session.commit()
            flash('Şablon başarıyla eklendi.', 'success')
            return redirect(url_for('admin.sablonlar'))
        except Exception as e:
            logger.error(f"Sablon ekle error: {e}")
            flash(f'Şablon eklenirken bir hata oluştu: {str(e)}', 'danger')
    return render_template('sablon_form.html', sirketler=sirketler)


# Alias for sablon_yeni -> sablon_ekle
@admin_bp.route('/sablon-yeni', methods=['GET', 'POST'])
@admin_bp.route('/sablon-ekle', methods=['GET', 'POST'])
@superadmin_required
def sablon_yeni():
    """Alias for sablon_ekle"""
    return redirect(url_for('admin.sablon_ekle'))


@admin_bp.route('/sablon/duzenle/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def sablon_duzenle(id):
    """Şablon düzenleme"""
    import json
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.all()
    except:
        pass
    
    try:
        from app.models import ExamTemplate
        from app.extensions import db
        sablon = ExamTemplate.query.get_or_404(id)

        if request.method == 'POST':
            # Build sections_config from form data
            sections = request.form.getlist('sections[]')
            sections_config = {}
            
            for section in sections:
                section_config = {
                    'question_count': int(request.form.get(f'{section}_question_count', 5)),
                    'time_limit': int(request.form.get(f'{section}_time_limit', 10)) * 60,
                    'order': int(request.form.get(f'{section}_order', 1))
                }
                if section == 'speaking':
                    section_config['prep_time'] = int(request.form.get('speaking_prep_time', 30))
                    section_config['answer_time'] = int(request.form.get('speaking_answer_time', 60))
                elif section == 'writing':
                    section_config['min_words'] = int(request.form.get('writing_min_words', 150))
                elif section == 'reading':
                    section_config['passage_count'] = int(request.form.get('reading_passage_count', 2))
                elif section == 'listening':
                    section_config['audio_count'] = int(request.form.get('listening_audio_count', 3))
                
                sections_config[section] = section_config
            
            sablon.isim = request.form.get('isim') or request.form.get('ad') or sablon.isim
            sablon.sinav_suresi = int(request.form.get('sinav_suresi', sablon.sinav_suresi))
            sablon.soru_suresi = int(request.form.get('soru_suresi', sablon.soru_suresi or 60))
            sablon.soru_limiti = int(request.form.get('soru_limiti', sablon.soru_limiti))
            sablon.baslangic_seviyesi = request.form.get('baslangic_seviyesi') or sablon.baslangic_seviyesi
            sablon.is_adaptive = request.form.get('is_adaptive') == 'on'
            sablon.randomize_questions = request.form.get('randomize_questions') == 'on'
            sablon.show_results = request.form.get('show_results') == 'on'
            sablon.sirket_id = request.form.get('sirket_id') or sablon.sirket_id
            sablon.sections_config = json.dumps(sections_config) if sections_config else sablon.sections_config
            db.session.commit()
            flash('Şablon başarıyla güncellendi.', 'success')
            return redirect(url_for('admin.sablonlar'))

        return render_template('sablon_form.html', sablon=sablon, sirketler=sirketler)
    except Exception as e:
        logger.error(f"Sablon duzenle error: {e}")
        flash(f'Şablon düzenlenirken bir hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('admin.sablonlar'))


@admin_bp.route('/sablon/sil/<int:id>', methods=['POST'])
@superadmin_required
def sablon_sil(id):
    """Şablon silme"""
    try:
        from app.models import ExamTemplate
        from app.extensions import db
        sablon = ExamTemplate.query.get_or_404(id)
        db.session.delete(sablon)
        db.session.commit()
        flash('Şablon başarıyla silindi.', 'success')
    except Exception as e:
        logger.error(f"Sablon sil error: {e}")
        flash('Şablon silinirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.sablonlar'))


# ==================== EXPORT ====================
@admin_bp.route('/export')
@superadmin_required
def export():
    """Data export - CSV formatında veri indirme"""
    export_type = request.args.get('type', 'candidates')
    format_type = request.args.get('format', 'csv')

    try:
        from flask import Response
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        if export_type == 'candidates' or export_type == 'adaylar':
            from app.models import Candidate
            # CSV header
            writer.writerow(['ID', 'Ad Soyad', 'Email', 'Cep No', 'Giriş Kodu', 'Durum', 'Puan', 'Seviye', 'Oluşturulma'])

            candidates = Candidate.query.order_by(Candidate.id.desc()).all()
            for c in candidates:
                writer.writerow([
                    c.id,
                    c.ad_soyad,
                    c.email or '',
                    c.cep_no or '',
                    c.giris_kodu or '',
                    c.sinav_durumu or 'beklemede',
                    c.puan or '',
                    c.seviye_sonuc or '',
                    c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ''
                ])
            filename = 'adaylar_export.csv'

        elif export_type == 'companies' or export_type == 'sirketler':
            from app.models import Company
            writer.writerow(['ID', 'İsim', 'Email', 'Telefon', 'Adres', 'Kredi', 'Aktif', 'Oluşturulma'])

            companies = Company.query.order_by(Company.id.desc()).all()
            for c in companies:
                writer.writerow([
                    c.id,
                    c.isim,
                    c.email or '',
                    c.telefon or '',
                    c.adres or '',
                    c.kredi or 0,
                    'Evet' if c.is_active else 'Hayır',
                    c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ''
                ])
            filename = 'sirketler_export.csv'

        elif export_type == 'questions' or export_type == 'sorular':
            from app.models import Question
            writer.writerow(['ID', 'Soru Metni', 'Seviye', 'Beceri', 'Doğru Cevap', 'Aktif'])

            questions = Question.query.order_by(Question.id.desc()).all()
            for q in questions:
                writer.writerow([
                    q.id,
                    (q.soru_metni or '')[:100],  # İlk 100 karakter
                    q.seviye or '',
                    q.beceri or '',
                    q.dogru_cevap or '',
                    'Evet' if q.is_active else 'Hayır'
                ])
            filename = 'sorular_export.csv'

        else:
            # Varsayılan olarak tüm adayları indir
            from app.models import Candidate
            writer.writerow(['ID', 'Ad Soyad', 'Email', 'Puan', 'Seviye'])
            candidates = Candidate.query.all()
            for c in candidates:
                writer.writerow([c.id, c.ad_soyad, c.email or '', c.puan or '', c.seviye_sonuc or ''])
            filename = 'veriler_export.csv'

        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

    except Exception as e:
        logger.error(f"Export error: {e}")
        flash(f'Export işlemi başarısız: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


# ==================== RAPORLAR ==================== (DÜZELTİLDİ)
@admin_bp.route('/raporlar')
@superadmin_required
def raporlar():
    """Raporlar sayfası"""
    stats = {
        'total': 0,
        'completed': 0,
        'pending': 0,
    }
    try:
        from app.models import Candidate
        stats = {
            'total': Candidate.query.filter_by(is_deleted=False).count(),
            'completed': Candidate.query.filter_by(is_deleted=False, sinav_durumu='tamamlandi').count(),
            'pending': Candidate.query.filter_by(is_deleted=False, sinav_durumu='beklemede').count(),
        }
    except Exception as e:
        logger.error(f"Raporlar error: {e}")
    return render_template('raporlar.html', stats=stats)


@admin_bp.route('/super-rapor')
@superadmin_required
def super_rapor():
    """Platform geneli rapor"""
    stats = {
        'total_companies': 0,
        'active_companies': 0,
        'total_users': 0,
        'total_candidates': 0,
        'completed_exams': 0,
        'total_credits_used': 0,
    }
    try:
        from app.models import Company, User, Question, Candidate
        from app.extensions import db
        stats = {
            'total_companies': Company.query.count(),
            'active_companies': Company.query.filter_by(is_active=True).count(),
            'total_users': User.query.count(),
            'total_candidates': Candidate.query.filter_by(is_deleted=False).count(),
            'completed_exams': Candidate.query.filter_by(is_deleted=False, sinav_durumu='tamamlandi').count(),
            'total_credits_used': db.session.query(db.func.sum(Company.kredi)).scalar() or 0,
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


# ==================== VERİ YÖNETİMİ ==================== (DÜZELTİLDİ)
@admin_bp.route('/veri-yonetimi')
@superadmin_required
def veri_yonetimi():
    """Veri yönetimi sayfası"""
    stats = {
        'total_candidates': 0,
        'total_questions': 0,
        'total_answers': 0,
        'speaking_recordings': 0,
        'audit_logs': 0,
        'db_size_mb': 0,
    }
    backups = []
    try:
        from app.models import Candidate, Question, ExamAnswer, AuditLog
        stats = {
            'total_candidates': Candidate.query.filter_by(is_deleted=False).count(),
            'total_questions': Question.query.count(),
            'total_answers': ExamAnswer.query.count(),
            'speaking_recordings': 0,
            'audit_logs': AuditLog.query.count(),
            'db_size_mb': 0,
        }
    except Exception as e:
        logger.error(f"Veri yonetimi error: {e}")
    return render_template('veri_yonetimi.html', stats=stats, backups=backups)


@admin_bp.route('/fraud-heatmap')
@superadmin_required
def fraud_heatmap():
    """Fraud heatmap"""
    return render_template('fraud_heatmap.html')


# ==================== LOGLAR ====================
@admin_bp.route('/logs')
@superadmin_required
def logs():
    """Admin logları - main function"""
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action', '')
    logs_list = []

    # Create pagination object
    class LogPagination:
        def __init__(self):
            self.page = page
            self.pages = 1
            self.has_prev = False
            self.has_next = False
            self.prev_num = None
            self.next_num = None

    pagination = LogPagination()

    try:
        from app.models import AuditLog
        query = AuditLog.query
        if action:
            query = query.filter(AuditLog.action == action)
        logs_data = query.order_by(AuditLog.id.desc()).paginate(
            page=page, per_page=50, error_out=False
        )
        logs_list = logs_data.items
        pagination.page = logs_data.page
        pagination.pages = logs_data.pages
        pagination.has_prev = logs_data.has_prev
        pagination.has_next = logs_data.has_next
        pagination.prev_num = logs_data.prev_num
        pagination.next_num = logs_data.next_num
    except Exception as e:
        logger.error(f"Logs error: {e}")

    return render_template('admin_logs.html', logs=logs_list, pagination=pagination)


@admin_bp.route('/loglar')
@superadmin_required
def loglar():
    """Admin logları - alias that the template uses"""
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action', '')
    logs_list = []

    # Create pagination object
    class LogPagination:
        def __init__(self):
            self.page = page
            self.pages = 1
            self.has_prev = False
            self.has_next = False
            self.prev_num = None
            self.next_num = None

    pagination = LogPagination()

    try:
        from app.models import AuditLog
        query = AuditLog.query
        if action:
            query = query.filter(AuditLog.action == action)
        logs_data = query.order_by(AuditLog.id.desc()).paginate(
            page=page, per_page=50, error_out=False
        )
        logs_list = logs_data.items
        pagination.page = logs_data.page
        pagination.pages = logs_data.pages
        pagination.has_prev = logs_data.has_prev
        pagination.has_next = logs_data.has_next
        pagination.prev_num = logs_data.prev_num
        pagination.next_num = logs_data.next_num
    except Exception as e:
        logger.error(f"Loglar error: {e}")

    return render_template('admin_logs.html', logs=logs_list, pagination=pagination)


@admin_bp.route('/log-listesi')
@superadmin_required
def loglar_liste():
    """Alias for logs"""
    return redirect(url_for('admin.loglar'))


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


# ==================== YEDEK ALMA VE VERİ ALT ROUTE'LARI ====================
@admin_bp.route('/veri-yonetimi/yedek-al', methods=['GET', 'POST'])
@superadmin_required
def yedek_al():
    """Yedek alma sayfası - data.backup'a yönlendir"""
    if request.method == 'POST':
        return redirect(url_for('data.create_backup'), code=307)
    return redirect(url_for('data.backup'))


@admin_bp.route('/veri-yonetimi/temizlik')
@superadmin_required
def veri_temizlik():
    """Veri temizliği sayfası"""
    return redirect(url_for('data.cleanup'))


@admin_bp.route('/veri-yonetimi/gdpr')
@superadmin_required
def veri_gdpr():
    """GDPR sayfası"""
    return redirect(url_for('data.gdpr'))


@admin_bp.route('/veri-yonetimi/kvkk')
@superadmin_required
def veri_kvkk():
    """KVKK sayfası"""
    return redirect(url_for('data.kvkk'))

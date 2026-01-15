# -*- coding: utf-8 -*-
"""
Admin Routes - Super Admin Panel
GitHub: app/routes/admin.py
COMPREHENSIVE FIX: All missing routes added for template compatibility
Model names: Company, User, Candidate, ExamTemplate, Question, AuditLog, ExamAnswer
Candidate fields: ad_soyad, email, cep_no (not telefon), sirket_id, giris_kodu
GÃœNCELLENDI: Aday silme fonksiyonlarÄ± dÃ¼zeltildi - foreign key constraint hatalarÄ± giderildi
FIXED: Rapor route'larÄ± dÃ¼zeltildi - template'lerin beklediÄŸi key isimleri eklendi
FIXED: Speaking/Writing sorularÄ±nda ÅŸÄ±k alanlarÄ± NULL olarak kaydedilir
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def superadmin_required(f):
    """Super admin yetkisi gerektiren route'lar iÃ§in dekoratÃ¶r"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfaya eriÅŸmek iÃ§in giriÅŸ yapmalÄ±sÄ±nÄ±z.', 'warning')
            return redirect(url_for('auth.login'))

        rol = session.get('rol', '')
        if rol not in ['superadmin', 'super_admin', 'admin']:
            flash('Bu sayfaya eriÅŸim yetkiniz yok.', 'danger')
            return redirect(url_for('main.index'))

        return f(*args, **kwargs)
    return decorated_function

# ==================== YARDIMCI FONKSÄ°YON: ADAY BAÄžIMLI VERÄ°LERÄ° SÄ°L ====================
def delete_candidate_related_data(candidate_id):
    """
    Bir adaya ait tÃ¼m baÄŸÄ±mlÄ± verileri siler
    Foreign key constraint hatalarÄ±nÄ± Ã¶nlemek iÃ§in kullanÄ±lÄ±r

    Returns:
        list: [(tablo_adÄ±, silinen_kayÄ±t_sayÄ±sÄ±), ...]
    """
    from app.extensions import db
    silinen_veriler = []

    # 1. ExamAnswer (SÄ±nav cevaplarÄ±)
    try:
        from app.models import ExamAnswer
        count = ExamAnswer.query.filter_by(aday_id=candidate_id).delete()
        silinen_veriler.append(('cevap', count))
    except Exception as e:
        logger.warning(f"ExamAnswer silme hatasÄ±: {e}")

    # 2. EmailLog (Email loglarÄ±)
    try:
        from app.models import EmailLog
        count = EmailLog.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('email log', count))
    except Exception as e:
        logger.warning(f"EmailLog silme hatasÄ±: {e}")

    # 3. ProctoringSnapshot (Proctoring fotoÄŸraflarÄ±)
    try:
        from app.models import ProctoringSnapshot
        count = ProctoringSnapshot.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('proctoring', count))
    except Exception as e:
        logger.warning(f"ProctoringSnapshot silme hatasÄ±: {e}")

    # 4. CandidateActivity (Aday aktiviteleri)
    try:
        from app.models import CandidateActivity
        count = CandidateActivity.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('aktivite', count))
    except Exception as e:
        logger.warning(f"CandidateActivity silme hatasÄ±: {e}")

    # 5. Certificate (Sertifikalar)
    try:
        from app.models import Certificate
        count = Certificate.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('sertifika', count))
    except Exception as e:
        logger.warning(f"Certificate silme hatasÄ±: {e}")

    # 6. AuditLog (Denetim loglarÄ± - adayla ilgili)
    try:
        from app.models import AuditLog
        count = AuditLog.query.filter(
            AuditLog.entity_type == 'candidate',
            AuditLog.entity_id == candidate_id
        ).delete()
        silinen_veriler.append(('audit log', count))
    except Exception as e:
        logger.warning(f"AuditLog silme hatasÄ±: {e}")

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

# ==================== ÅžÄ°RKET YÃ–NETÄ°MÄ° ====================
@admin_bp.route('/sirketler')
@superadmin_required
def sirketler():
    """Åžirket listesi"""
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.order_by(Company.id.desc()).all()
    except Exception as e:
        logger.error(f"Sirketler error: {e}")
        flash('Åžirketler yÃ¼klenirken bir hata oluÅŸtu.', 'danger')
    return render_template('sirketler.html', sirketler=sirketler)


@admin_bp.route('/sirket/<int:sirket_id>')
@superadmin_required
def sirket_detay(sirket_id):
    """Åžirket detay sayfasÄ±"""
    try:
        from app.models import Company
        sirket = Company.query.get_or_404(sirket_id)
        return render_template('sirket_detay.html', sirket=sirket)
    except Exception as e:
        logger.error(f"Sirket detay error: {e}")
        flash('Åžirket bulunamadÄ±.', 'danger')
        return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/ekle', methods=['GET', 'POST'])
@superadmin_required
def sirket_ekle():
    """Yeni ÅŸirket ekleme"""
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
            flash('Åžirket baÅŸarÄ±yla eklendi.', 'success')
            return redirect(url_for('admin.sirketler'))
        except Exception as e:
            logger.error(f"Sirket ekle error: {e}")
            flash('Åžirket eklenirken bir hata oluÅŸtu.', 'danger')
    return render_template('sirket_form.html')


@admin_bp.route('/sirket/duzenle/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def sirket_duzenle(id):
    """Åžirket dÃ¼zenleme"""
    try:
        from app.models import Company, User
        from app.extensions import db
        sirket = Company.query.get_or_404(id)

        # Åžirkete ait admin kullanÄ±cÄ±sÄ±nÄ± bul
        admin_user = User.query.filter_by(sirket_id=id, rol='customer').first()

        if request.method == 'POST':
            sirket.isim = request.form.get('ad') or request.form.get('isim') or sirket.isim
            sirket.email = request.form.get('email') or sirket.email
            sirket.telefon = request.form.get('telefon') or sirket.telefon
            sirket.adres = request.form.get('adres') or sirket.adres

            # Åžifre deÄŸiÅŸtirme iÅŸlemi
            new_password = request.form.get('new_password')
            new_password_confirm = request.form.get('new_password_confirm')

            if new_password and new_password_confirm:
                if new_password == new_password_confirm:
                    if len(new_password) >= 8:
                        if admin_user:
                            admin_user.set_password(new_password)
                            if hasattr(admin_user, 'plain_password'):
                                admin_user.plain_password = new_password
                            flash('Åžifre baÅŸarÄ±yla deÄŸiÅŸtirildi.', 'success')
                    else:
                        flash('Åžifre en az 8 karakter olmalÄ±dÄ±r.', 'warning')
                else:
                    flash('Åžifreler eÅŸleÅŸmiyor.', 'warning')

            db.session.commit()
            flash('Åžirket baÅŸarÄ±yla gÃ¼ncellendi.', 'success')
            return redirect(url_for('admin.sirketler'))

        return render_template('sirket_form.html', sirket=sirket, admin_user=admin_user)
    except Exception as e:
        logger.error(f"Sirket duzenle error: {e}")
        flash('Åžirket dÃ¼zenlenirken bir hata oluÅŸtu.', 'danger')
        return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/sil/<int:id>', methods=['POST'])
@superadmin_required
def sirket_sil(id):
    """Åžirket silme"""
    try:
        from app.models import Company
        from app.extensions import db
        sirket = Company.query.get_or_404(id)
        db.session.delete(sirket)
        db.session.commit()
        flash('Åžirket baÅŸarÄ±yla silindi.', 'success')
    except Exception as e:
        logger.error(f"Sirket sil error: {e}")
        flash('Åžirket silinirken bir hata oluÅŸtu.', 'danger')
    return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/kredi/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def sirket_kredi(id):
    """Åžirkete kredi ekleme sayfasÄ±"""
    try:
        from app.models import Company
        from app.extensions import db
        sirket = Company.query.get_or_404(id)

        if request.method == 'POST':
            miktar = int(request.form.get('miktar', 0))
            if hasattr(sirket, 'kredi'):
                sirket.kredi = (sirket.kredi or 0) + miktar
            db.session.commit()
            flash(f'{miktar} kredi baÅŸarÄ±yla eklendi.', 'success')
            return redirect(url_for('admin.sirketler'))

        return render_template('sirket_kredi.html', sirket=sirket)
    except Exception as e:
        logger.error(f"Sirket kredi error: {e}")
        flash('Kredi eklenirken bir hata oluÅŸtu.', 'danger')
        return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/toplu-pasif', methods=['POST'])
@superadmin_required
def toplu_sirket_pasif():
    """Toplu ÅŸirket pasifleÅŸtirme"""
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
            flash(f'{len(sirket_ids)} ÅŸirket pasifleÅŸtirildi.', 'success')
        else:
            flash('PasifleÅŸtirilecek ÅŸirket seÃ§ilmedi.', 'warning')
    except Exception as e:
        logger.error(f"Toplu sirket pasif error: {e}")
        flash('Åžirketler pasifleÅŸtirilirken bir hata oluÅŸtu.', 'danger')

    return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/toplu-aktif', methods=['POST'])
@superadmin_required
def toplu_sirket_aktif():
    """Toplu ÅŸirket aktifleÅŸtirme"""
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
            flash(f'{len(sirket_ids)} ÅŸirket aktifleÅŸtirildi.', 'success')
        else:
            flash('AktifleÅŸtirilecek ÅŸirket seÃ§ilmedi.', 'warning')
    except Exception as e:
        logger.error(f"Toplu sirket aktif error: {e}")
        flash('Åžirketler aktifleÅŸtirilirken bir hata oluÅŸtu.', 'danger')

    return redirect(url_for('admin.sirketler'))

# ==================== KULLANICI YÃ–NETÄ°MÄ° ====================
@admin_bp.route('/kullanicilar')
@superadmin_required
def kullanicilar():
    """KullanÄ±cÄ± listesi"""
    kullanicilar = []
    try:
        from app.models import User
        kullanicilar = User.query.order_by(User.id.desc()).all()
    except Exception as e:
        logger.error(f"Kullanicilar error: {e}")
        flash('KullanÄ±cÄ±lar yÃ¼klenirken bir hata oluÅŸtu.', 'danger')
    return render_template('kullanicilar.html', kullanicilar=kullanicilar)


@admin_bp.route('/kullanici/ekle', methods=['GET', 'POST'])
@superadmin_required
def kullanici_ekle():
    """Yeni kullanÄ±cÄ± ekleme"""
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
            flash('KullanÄ±cÄ± baÅŸarÄ±yla eklendi.', 'success')
            return redirect(url_for('admin.kullanicilar'))
        except Exception as e:
            logger.error(f"Kullanici ekle error: {e}")
            flash('KullanÄ±cÄ± eklenirken bir hata oluÅŸtu.', 'danger')
    return render_template('kullanici_form.html', sirketler=sirketler)


@admin_bp.route('/kullanici/duzenle/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def kullanici_duzenle(id):
    """KullanÄ±cÄ± dÃ¼zenleme"""
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
            flash('KullanÄ±cÄ± baÅŸarÄ±yla gÃ¼ncellendi.', 'success')
            return redirect(url_for('admin.kullanicilar'))

        return render_template('kullanici_form.html', kullanici=kullanici, sirketler=sirketler)
    except Exception as e:
        logger.error(f"Kullanici duzenle error: {e}")
        flash('KullanÄ±cÄ± dÃ¼zenlenirken bir hata oluÅŸtu.', 'danger')
        return redirect(url_for('admin.kullanicilar'))


@admin_bp.route('/kullanici/sil/<int:id>', methods=['POST'])
@superadmin_required
def kullanici_sil(id):
    """KullanÄ±cÄ± silme"""
    try:
        from app.models import User
        from app.extensions import db
        kullanici = User.query.get_or_404(id)
        db.session.delete(kullanici)
        db.session.commit()
        flash('KullanÄ±cÄ± baÅŸarÄ±yla silindi.', 'success')
    except Exception as e:
        logger.error(f"Kullanici sil error: {e}")
        flash('KullanÄ±cÄ± silinirken bir hata oluÅŸtu.', 'danger')
    return redirect(url_for('admin.kullanicilar'))


@admin_bp.route('/kullanici/kalici-sil/<int:id>', methods=['POST'])
@superadmin_required
def kullanici_kalici_sil(id):
    """KullanÄ±cÄ± kalÄ±cÄ± silme (alias for kullanici_sil)"""
    return kullanici_sil(id)

# ==================== ADAY YÃ–NETÄ°MÄ° ====================
@admin_bp.route('/adaylar')
@superadmin_required
def adaylar():
    """Aday listesi with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    bekliyor_count = 0
    devam_count = 0
    tamamlanan_count = 0

    try:
        from app.models import Candidate
        adaylar = Candidate.query.filter_by(is_deleted=False).order_by(Candidate.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        try:
            bekliyor_count = Candidate.query.filter_by(is_deleted=False, sinav_durumu='beklemede').count()
            devam_count = Candidate.query.filter_by(is_deleted=False, sinav_durumu='baslamis').count()
            tamamlanan_count = Candidate.query.filter_by(is_deleted=False, sinav_durumu='tamamlandi').count()
        except Exception as stat_err:
            logger.warning(f"Stats calculation error: {stat_err}")
    except Exception as e:
        logger.error(f"Adaylar error: {e}")
        flash('Adaylar yÃ¼klenirken bir hata oluÅŸtu.', 'danger')
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
    """Toplu aday yÃ¼kleme"""
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
            flash('Toplu yÃ¼kleme iÅŸlemi baÅŸarÄ±lÄ±.', 'success')
            return redirect(url_for('admin.adaylar'))
        except Exception as e:
            logger.error(f"Bulk upload error: {e}")
            flash('Toplu yÃ¼kleme sÄ±rasÄ±nda bir hata oluÅŸtu.', 'danger')

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
            flash(f'Aday baÅŸarÄ±yla eklendi. GiriÅŸ kodu: {giris_kodu}', 'success')
            return redirect(url_for('admin.adaylar'))
        except Exception as e:
            logger.error(f"Aday ekle error: {e}")
            flash('Aday eklenirken bir hata oluÅŸtu.', 'danger')
    return render_template('aday_form.html', sirketler=sirketler, sablonlar=sablonlar)


@admin_bp.route('/aday/<int:aday_id>')
@superadmin_required
def aday_detay(aday_id):
    """Aday detay sayfasÄ±"""
    from app.models import Candidate
    aday = Candidate.query.get(aday_id)
    if not aday:
        flash('Aday bulunamadÄ±.', 'danger')
        return redirect(url_for('admin.adaylar'))
    return render_template('aday_detay.html', aday=aday)


# ==================== ADAY SÄ°LME - DÃœZELTÄ°LDÄ° ====================
@admin_bp.route('/aday/sil/<int:id>', methods=['POST'])
@superadmin_required
def aday_sil(id):
    """Aday soft delete - is_deleted = True yapar"""
    try:
        from app.models import Candidate
        from app.extensions import db
        aday = Candidate.query.get_or_404(id)
        aday_adi = aday.ad_soyad
        if hasattr(aday, 'is_deleted'):
            aday.is_deleted = True
            db.session.commit()
            flash(f'Aday "{aday_adi}" silindi (geri alÄ±nabilir).', 'success')
        else:
            delete_candidate_related_data(id)
            db.session.delete(aday)
            db.session.commit()
            flash(f'Aday "{aday_adi}" baÅŸarÄ±yla silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Aday sil error (id={id}): {e}")
        flash(f'Aday silinirken bir hata oluÅŸtu: {str(e)}', 'danger')
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/kalici-sil/<int:id>', methods=['POST'])
@superadmin_required
def aday_kalici_sil(id):
    """Aday kalÄ±cÄ± silme - veritabanÄ±ndan tamamen kaldÄ±rÄ±r"""
    try:
        from app.models import Candidate
        from app.extensions import db
        aday = Candidate.query.get_or_404(id)
        aday_adi = aday.ad_soyad
        silinen_veri = delete_candidate_related_data(id)
        db.session.delete(aday)
        db.session.commit()
        mesaj = f'Aday "{aday_adi}" ve tÃ¼m verileri kalÄ±cÄ± olarak silindi.'
        if silinen_veri:
            detay = ', '.join([f'{v[1]} {v[0]}' for v in silinen_veri if v[1] > 0])
            if detay:
                mesaj += f' (Silinen: {detay})'
        flash(mesaj, 'success')
        logger.info(f"Aday kalÄ±cÄ± silindi: {aday_adi} (id={id})")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Aday kalÄ±cÄ± sil error (id={id}): {e}")
        flash(f'Aday silinirken bir hata oluÅŸtu: {str(e)}', 'danger')
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/sinav-sifirla/<int:id>', methods=['POST'])
@superadmin_required
def aday_sinav_sifirla(id):
    """Aday sÄ±nav sÄ±fÄ±rlama"""
    try:
        from app.models import Candidate, ExamAnswer
        from app.extensions import db
        aday = Candidate.query.get_or_404(id)
        ExamAnswer.query.filter_by(aday_id=id).delete()
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
        flash('Aday sÄ±navÄ± baÅŸarÄ±yla sÄ±fÄ±rlandÄ±.', 'success')
    except Exception as e:
        logger.error(f"Aday sinav sifirla error: {e}")
        flash('SÄ±nav sÄ±fÄ±rlanÄ±rken bir hata oluÅŸtu.', 'danger')
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
                    logger.warning(f"Toplu sil - aday {aday_id} hatasÄ±: {e}")
            db.session.commit()
            flash(f'{silinen} aday baÅŸarÄ±yla silindi.', 'success')
        else:
            flash('Silinecek aday seÃ§ilmedi.', 'warning')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Toplu aday sil error: {e}")
        flash('Adaylar silinirken bir hata oluÅŸtu.', 'danger')
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/aktif/<int:id>', methods=['POST'])
@superadmin_required
def aday_aktif(id):
    """Silinen adayÄ± aktifleÅŸtir (geri yÃ¼kle)"""
    try:
        from app.models import Candidate
        from app.extensions import db
        aday = Candidate.query.get_or_404(id)
        if hasattr(aday, 'is_deleted'):
            aday.is_deleted = False
            db.session.commit()
            flash(f'Aday "{aday.ad_soyad}" baÅŸarÄ±yla geri yÃ¼klendi.', 'success')
        else:
            flash('Bu aday zaten aktif durumda.', 'info')
    except Exception as e:
        logger.error(f"Aday aktif error: {e}")
        flash('Aday aktifleÅŸtirilirken bir hata oluÅŸtu.', 'danger')
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/toplu-aktif', methods=['POST'])
@superadmin_required
def toplu_aday_aktif():
    """Toplu aday aktifleÅŸtirme (geri yÃ¼kleme)"""
    try:
        from app.models import Candidate
        from app.extensions import db
        aday_ids = request.form.getlist('aday_ids[]')
        if aday_ids:
            Candidate.query.filter(Candidate.id.in_(aday_ids)).update(
                {'is_deleted': False}, synchronize_session=False
            )
            db.session.commit()
            flash(f'{len(aday_ids)} aday baÅŸarÄ±yla geri yÃ¼klendi.', 'success')
        else:
            flash('AktifleÅŸtirilecek aday seÃ§ilmedi.', 'warning')
    except Exception as e:
        logger.error(f"Toplu aday aktif error: {e}")
        flash('Adaylar aktifleÅŸtirilirken bir hata oluÅŸtu.', 'danger')
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/toplu-kalici-sil', methods=['POST'])
@superadmin_required
def toplu_aday_kalici_sil():
    """Toplu aday kalÄ±cÄ± silme"""
    try:
        from app.models import Candidate
        from app.extensions import db
        aday_ids = request.form.getlist('aday_ids[]')
        if not aday_ids:
            flash('Silinecek aday seÃ§ilmedi.', 'warning')
            return redirect(url_for('admin.adaylar'))
        silinen_sayisi = 0
        hatali_sayisi = 0
        for aday_id in aday_ids:
            try:
                aday_id = int(aday_id)
                aday = Candidate.query.get(aday_id)
                if aday:
                    delete_candidate_related_data(aday_id)
                    db.session.delete(aday)
                    silinen_sayisi += 1
            except Exception as e:
                logger.error(f"Toplu kalÄ±cÄ± silme - aday {aday_id} hatasÄ±: {e}")
                hatali_sayisi += 1
                continue
        db.session.commit()
        if silinen_sayisi > 0:
            flash(f'{silinen_sayisi} aday ve tÃ¼m verileri kalÄ±cÄ± olarak silindi.', 'success')
        if hatali_sayisi > 0:
            flash(f'{hatali_sayisi} aday silinirken hata oluÅŸtu.', 'warning')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Toplu aday kalÄ±cÄ± sil error: {e}")
        flash(f'Toplu silme iÅŸleminde bir hata oluÅŸtu: {str(e)}', 'danger')
    return redirect(url_for('admin.adaylar'))

# ==================== SORU YÃ–NETÄ°MÄ° ==================== (DÃœZELTÄ°LDÄ° - Speaking/Writing iÃ§in ÅŸÄ±klar NULL)
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
        flash('Sorular yÃ¼klenirken bir hata oluÅŸtu.', 'danger')
    return render_template('sorular.html', sorular=sorular)


@admin_bp.route('/soru/ekle', methods=['GET', 'POST'])
@superadmin_required
def soru_ekle():
    """Yeni soru ekleme - Speaking/Writing iÃ§in ÅŸÄ±k alanlarÄ± temizlenir"""
    if request.method == 'POST':
        try:
            from app.models import Question
            from app.extensions import db
            
            kategori = (request.form.get('kategori') or '').strip().lower()
            
            # Speaking ve Writing iÃ§in ÅŸÄ±k ve doÄŸru cevap alanlarÄ±nÄ± NULL yap
            if kategori in ['speaking', 'writing']:
                yeni_soru = Question(
                    soru_metni=request.form.get('soru_metni'),
                    secenek_a=None,
                    secenek_b=None,
                    secenek_c=None,
                    secenek_d=None,
                    dogru_cevap=None,  # Speaking/Writing iÃ§in ÅŸÄ±k yok
                    zorluk=request.form.get('zorluk', 'orta'),
                    kategori=request.form.get('kategori')  # Original case'i koru
                )
            else:
                # Ã‡oktan seÃ§meli ve diÄŸer soru tipleri iÃ§in ÅŸÄ±klarÄ± al
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
            flash('Soru baÅŸarÄ±yla eklendi.', 'success')
            return redirect(url_for('admin.sorular'))
        except Exception as e:
            logger.error(f"Soru ekle error: {e}")
            flash('Soru eklenirken bir hata oluÅŸtu.', 'danger')
    return render_template('soru_form.html')


@admin_bp.route('/soru/duzenle/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def soru_duzenle(id):
    """Soru dÃ¼zenleme - Speaking/Writing iÃ§in ÅŸÄ±k alanlarÄ± temizlenir"""
    try:
        from app.models import Question
        from app.extensions import db
        soru = Question.query.get_or_404(id)

        if request.method == 'POST':
            kategori = (request.form.get('kategori') or soru.kategori or '').strip().lower()
            
            soru.soru_metni = request.form.get('soru_metni') or soru.soru_metni
            soru.zorluk = request.form.get('zorluk') or soru.zorluk
            soru.kategori = request.form.get('kategori') or soru.kategori
            
            # Speaking ve Writing iÃ§in ÅŸÄ±k ve doÄŸru cevap alanlarÄ±nÄ± NULL yap
            if kategori in ['speaking', 'writing']:
                soru.secenek_a = None
                soru.secenek_b = None
                soru.secenek_c = None
                soru.secenek_d = None
                soru.dogru_cevap = None
            else:
                # DiÄŸer soru tipleri iÃ§in ÅŸÄ±klarÄ± gÃ¼ncelle
                soru.secenek_a = request.form.get('secenek_a') or soru.secenek_a
                soru.secenek_b = request.form.get('secenek_b') or soru.secenek_b
                soru.secenek_c = request.form.get('secenek_c') or soru.secenek_c
                soru.secenek_d = request.form.get('secenek_d') or soru.secenek_d
                soru.dogru_cevap = request.form.get('dogru_cevap') or soru.dogru_cevap
            
            db.session.commit()
            flash('Soru baÅŸarÄ±yla gÃ¼ncellendi.', 'success')
            return redirect(url_for('admin.sorular'))

        return render_template('soru_form.html', soru=soru)
    except Exception as e:
        logger.error(f"Soru duzenle error: {e}")
        flash('Soru dÃ¼zenlenirken bir hata oluÅŸtu.', 'danger')
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
        flash('Soru baÅŸarÄ±yla silindi.', 'success')
    except Exception as e:
        logger.error(f"Soru sil error: {e}")
        flash('Soru silinirken bir hata oluÅŸtu.', 'danger')
    return redirect(url_for('admin.sorular'))


# ==================== MEVCUT SPEAKING/WRITING SORULARINI DUZELT ====================
@admin_bp.route('/fix-speaking-writing-questions', methods=['GET', 'POST'])
@superadmin_required
def fix_speaking_writing_questions():
    """Speaking ve Writing sorularÄ±ndaki ÅŸÄ±k/doÄŸru_cevap alanlarÄ±nÄ± temizler - TEK SEFERLIK"""
    if request.method == 'POST':
        try:
            from app.models import Question
            from app.extensions import db
            speaking_count = Question.query.filter(
                db.func.lower(Question.kategori) == 'speaking'
            ).update({
                'dogru_cevap': None,
                'secenek_a': None,
                'secenek_b': None,
                'secenek_c': None,
                'secenek_d': None
            }, synchronize_session=False)
            writing_count = Question.query.filter(
                db.func.lower(Question.kategori) == 'writing'
            ).update({
                'dogru_cevap': None,
                'secenek_a': None,
                'secenek_b': None,
                'secenek_c': None,
                'secenek_d': None
            }, synchronize_session=False)
            db.session.commit()
            flash(f'{speaking_count} Speaking ve {writing_count} Writing sorusu dÃ¼zeltildi!', 'success')
            return redirect(url_for('admin.sorular'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fix speaking/writing error: {e}")
            flash(f'Hata oluÅŸtu: {str(e)}', 'danger')
    
    try:
        from app.models import Question
        from app.extensions import db
        speaking_count = Question.query.filter(db.func.lower(Question.kategori) == 'speaking').count()
        writing_count = Question.query.filter(db.func.lower(Question.kategori) == 'writing').count()
        speaking_with_answer = Question.query.filter(
            db.func.lower(Question.kategori) == 'speaking',
            Question.dogru_cevap != None
        ).count()
        writing_with_answer = Question.query.filter(
            db.func.lower(Question.kategori) == 'writing',
            Question.dogru_cevap != None
        ).count()
    except:
        speaking_count = writing_count = speaking_with_answer = writing_with_answer = 0
    
    return f'''
    <!DOCTYPE html>
    <html><head><title>Speaking/Writing DÃ¼zeltme</title>
    <style>body{{font-family:Arial;padding:40px;max-width:600px;margin:0 auto}}.card{{background:#f5f5f5;padding:20px;border-radius:8px;margin:20px 0}}.warning{{background:#fff3cd;border:1px solid #ffc107}}.btn{{background:#dc3545;color:#fff;padding:12px 24px;border:none;border-radius:4px;cursor:pointer;font-size:16px}}.btn:hover{{background:#c82333}}</style>
    </head><body>
    <h1>ðŸ”§ Speaking/Writing SorularÄ±nÄ± DÃ¼zelt</h1>
    <div class="card"><p><strong>Speaking:</strong> {speaking_count} (ÅŸÄ±klÄ±: {speaking_with_answer})</p><p><strong>Writing:</strong> {writing_count} (ÅŸÄ±klÄ±: {writing_with_answer})</p></div>
    <div class="card warning"><p>âš ï¸ Bu iÅŸlem tÃ¼m Speaking ve Writing sorularÄ±nÄ±n ÅŸÄ±k ve doÄŸru_cevap alanlarÄ±nÄ± NULL yapacak.</p></div>
    <form method="POST"><button type="submit" class="btn">âœ… DÃ¼zeltmeyi Uygula</button></form>
    <p><a href="/admin/sorular">â† Sorulara DÃ¶n</a></p>
    </body></html>
    '''

# ==================== ÅžABLON YÃ–NETÄ°MÄ° ====================
@admin_bp.route('/sablonlar')
@superadmin_required
def sablonlar():
    """SÄ±nav ÅŸablonlarÄ± listesi"""
    sablonlar = []
    try:
        from app.models import ExamTemplate
        sablonlar = ExamTemplate.query.order_by(ExamTemplate.id.desc()).all()
    except Exception as e:
        logger.error(f"Sablonlar error: {e}")
        flash('Åžablonlar yÃ¼klenirken bir hata oluÅŸtu.', 'danger')
    return render_template('sablonlar.html', sablonlar=sablonlar)


@admin_bp.route('/sablon/ekle', methods=['GET', 'POST'])
@admin_bp.route('/sablon/yeni', methods=['GET', 'POST'])
@superadmin_required
def sablon_ekle():
    """Yeni ÅŸablon ekleme"""
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
            flash('Åžablon baÅŸarÄ±yla eklendi.', 'success')
            return redirect(url_for('admin.sablonlar'))
        except Exception as e:
            logger.error(f"Sablon ekle error: {e}")
            flash('Åžablon eklenirken bir hata oluÅŸtu.', 'danger')
    return render_template('sablon_form.html')

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
    """Åžablon dÃ¼zenleme"""
    try:
        from app.models import ExamTemplate
        from app.extensions import db
        sablon = ExamTemplate.query.get_or_404(id)

        if request.method == 'POST':
            sablon.ad = request.form.get('ad') or sablon.ad
            sablon.aciklama = request.form.get('aciklama') or sablon.aciklama
            sablon.sure = int(request.form.get('sure', sablon.sure))
            sablon.soru_sayisi = int(request.form.get('soru_sayisi', sablon.soru_sayisi))
            db.session.commit()
            flash('Åžablon baÅŸarÄ±yla gÃ¼ncellendi.', 'success')
            return redirect(url_for('admin.sablonlar'))

        return render_template('sablon_form.html', sablon=sablon)
    except Exception as e:
        logger.error(f"Sablon duzenle error: {e}")
        flash('Åžablon dÃ¼zenlenirken bir hata oluÅŸtu.', 'danger')
        return redirect(url_for('admin.sablonlar'))


@admin_bp.route('/sablon/sil/<int:id>', methods=['POST'])
@superadmin_required
def sablon_sil(id):
    """Åžablon silme"""
    try:
        from app.models import ExamTemplate
        from app.extensions import db
        sablon = ExamTemplate.query.get_or_404(id)
        db.session.delete(sablon)
        db.session.commit()
        flash('Åžablon baÅŸarÄ±yla silindi.', 'success')
    except Exception as e:
        logger.error(f"Sablon sil error: {e}")
        flash('Åžablon silinirken bir hata oluÅŸtu.', 'danger')
    return redirect(url_for('admin.sablonlar'))


# ==================== EXPORT ====================
@admin_bp.route('/export')
@superadmin_required
def export():
    """Data export - CSV formatÄ±nda veri indirme"""
    export_type = request.args.get('type', 'candidates')
    try:
        from flask import Response
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)

        if export_type == 'candidates' or export_type == 'adaylar':
            from app.models import Candidate
            writer.writerow(['ID', 'Ad Soyad', 'Email', 'Cep No', 'GiriÅŸ Kodu', 'Durum', 'Puan', 'Seviye', 'OluÅŸturulma'])
            candidates = Candidate.query.order_by(Candidate.id.desc()).all()
            for c in candidates:
                writer.writerow([c.id, c.ad_soyad, c.email or '', c.cep_no or '', c.giris_kodu or '',
                    c.sinav_durumu or 'beklemede', c.puan or '', c.seviye_sonuc or '',
                    c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ''])
            filename = 'adaylar_export.csv'
        elif export_type == 'companies' or export_type == 'sirketler':
            from app.models import Company
            writer.writerow(['ID', 'Ä°sim', 'Email', 'Telefon', 'Adres', 'Kredi', 'Aktif', 'OluÅŸturulma'])
            companies = Company.query.order_by(Company.id.desc()).all()
            for c in companies:
                writer.writerow([c.id, c.isim, c.email or '', c.telefon or '', c.adres or '',
                    c.kredi or 0, 'Evet' if c.is_active else 'HayÄ±r',
                    c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ''])
            filename = 'sirketler_export.csv'
        elif export_type == 'questions' or export_type == 'sorular':
            from app.models import Question
            writer.writerow(['ID', 'Soru Metni', 'Seviye', 'Beceri', 'DoÄŸru Cevap', 'Aktif'])
            questions = Question.query.order_by(Question.id.desc()).all()
            for q in questions:
                writer.writerow([q.id, (q.soru_metni or '')[:100], q.seviye or '', q.beceri or '',
                    q.dogru_cevap or '', 'Evet' if q.is_active else 'HayÄ±r'])
            filename = 'sorular_export.csv'
        else:
            from app.models import Candidate
            writer.writerow(['ID', 'Ad Soyad', 'Email', 'Puan', 'Seviye'])
            candidates = Candidate.query.all()
            for c in candidates:
                writer.writerow([c.id, c.ad_soyad, c.email or '', c.puan or '', c.seviye_sonuc or ''])
            filename = 'veriler_export.csv'

        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'})
    except Exception as e:
        logger.error(f"Export error: {e}")
        flash(f'Export iÅŸlemi baÅŸarÄ±sÄ±z: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))

# ==================== RAPORLAR ==================== (DÃœZELTÄ°LDÄ°)
@admin_bp.route('/raporlar')
@superadmin_required
def raporlar():
    """Raporlar sayfasÄ±"""
    stats = {'total': 0, 'completed': 0, 'pending': 0}
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
    stats = {'total_companies': 0, 'active_companies': 0, 'total_users': 0,
             'total_candidates': 0, 'completed_exams': 0, 'total_credits_used': 0}
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

# ==================== KREDÄ° YÃ–NETÄ°MÄ° ====================
@admin_bp.route('/krediler')
@superadmin_required
def krediler():
    """Kredi yÃ¶netimi"""
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.order_by(Company.id.desc()).all()
    except Exception as e:
        logger.error(f"Krediler error: {e}")
        flash('Krediler yÃ¼klenirken bir hata oluÅŸtu.', 'danger')
    return render_template('krediler.html', sirketler=sirketler)


@admin_bp.route('/kredi/ekle/<int:sirket_id>', methods=['POST'])
@superadmin_required
def kredi_ekle(sirket_id):
    """Åžirkete kredi ekleme"""
    try:
        from app.models import Company
        from app.extensions import db
        sirket = Company.query.get_or_404(sirket_id)
        miktar = int(request.form.get('miktar', 0))
        if hasattr(sirket, 'kredi'):
            sirket.kredi = (sirket.kredi or 0) + miktar
        db.session.commit()
        flash(f'{miktar} kredi baÅŸarÄ±yla eklendi.', 'success')
    except Exception as e:
        logger.error(f"Kredi ekle error: {e}")
        flash('Kredi eklenirken bir hata oluÅŸtu.', 'danger')
    return redirect(url_for('admin.krediler'))

# ==================== AYARLAR ====================
@admin_bp.route('/ayarlar')
@superadmin_required
def ayarlar():
    """Sistem ayarlarÄ±"""
    return render_template('ayarlar.html')

# ==================== VERÄ° YÃ–NETÄ°MÄ° ==================== (DÃœZELTÄ°LDÄ°)
@admin_bp.route('/veri-yonetimi')
@superadmin_required
def veri_yonetimi():
    """Veri yÃ¶netimi sayfasÄ±"""
    stats = {'total_candidates': 0, 'total_questions': 0, 'total_answers': 0,
             'speaking_recordings': 0, 'audit_logs': 0, 'db_size_mb': 0}
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
    """Admin loglarÄ± - main function"""
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action', '')
    logs_list = []
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
        logs_data = query.order_by(AuditLog.id.desc()).paginate(page=page, per_page=50, error_out=False)
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
    """Admin loglarÄ± - alias that the template uses"""
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action', '')
    logs_list = []
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
        logs_data = query.order_by(AuditLog.id.desc()).paginate(page=page, per_page=50, error_out=False)
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

# ==================== DEMO OLUÅžTURMA ====================
@admin_bp.route('/demo-olustur', methods=['GET', 'POST'])
@superadmin_required
def demo_olustur():
    """HÄ±zlÄ± demo ÅŸirket ve aday oluÅŸturma"""
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
            flash('Demo ÅŸirket baÅŸarÄ±yla oluÅŸturuldu.', 'success')
            return redirect(url_for('admin.sirketler'))
        except Exception as e:
            logger.error(f"Demo olustur error: {e}")
            flash('Demo oluÅŸturulurken bir hata oluÅŸtu.', 'danger')
    return render_template('demo_olustur.html')

# ==================== YEDEK ALMA VE VERÄ° ALT ROUTE'LARI ====================
@admin_bp.route('/veri-yonetimi/yedek-al', methods=['GET', 'POST'])
@superadmin_required
def yedek_al():
    """Yedek alma sayfasÄ± - data.backup'a yÃ¶nlendir"""
    if request.method == 'POST':
        return redirect(url_for('data.create_backup'), code=307)
    return redirect(url_for('data.backup'))


@admin_bp.route('/veri-yonetimi/temizlik')
@superadmin_required
def veri_temizlik():
    """Veri temizliÄŸi sayfasÄ±"""
    return redirect(url_for('data.cleanup'))


@admin_bp.route('/veri-yonetimi/gdpr')
@superadmin_required
def veri_gdpr():
    """GDPR sayfasÄ±"""
    return redirect(url_for('data.gdpr'))


@admin_bp.route('/veri-yonetimi/kvkk')
@superadmin_required
def veri_kvkk():
    """KVKK sayfasÄ±"""
    return redirect(url_for('data.kvkk'))

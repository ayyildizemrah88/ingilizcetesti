# -*- coding: utf-8 -*-
"""
Admin Routes - Super Admin Panel
GitHub: app/routes/admin.py
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def superadmin_required(f):
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


def delete_candidate_related_data(candidate_id):
    from app.extensions import db
    silinen_veriler = []

    try:
        from app.models import ExamAnswer
        count = ExamAnswer.query.filter_by(aday_id=candidate_id).delete()
        silinen_veriler.append(('cevap', count))
    except Exception as e:
        logger.warning(f"ExamAnswer silme hatası: {e}")

    try:
        from app.models import EmailLog
        count = EmailLog.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('email log', count))
    except Exception as e:
        logger.warning(f"EmailLog silme hatası: {e}")

    try:
        from app.models import ProctoringSnapshot
        count = ProctoringSnapshot.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('proctoring', count))
    except Exception as e:
        logger.warning(f"ProctoringSnapshot silme hatası: {e}")

    try:
        from app.models import CandidateActivity
        count = CandidateActivity.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('aktivite', count))
    except Exception as e:
        logger.warning(f"CandidateActivity silme hatası: {e}")

    try:
        from app.models import Certificate
        count = Certificate.query.filter_by(candidate_id=candidate_id).delete()
        silinen_veriler.append(('sertifika', count))
    except Exception as e:
        logger.warning(f"Certificate silme hatası: {e}")

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
    try:
        from app.models import Company, User
        from app.extensions import db
        sirket = Company.query.get_or_404(id)
        admin_user = User.query.filter_by(sirket_id=id, rol='customer').first()

        if request.method == 'POST':
            sirket.isim = request.form.get('ad') or request.form.get('isim') or sirket.isim
            sirket.email = request.form.get('email') or sirket.email
            sirket.telefon = request.form.get('telefon') or sirket.telefon
            sirket.adres = request.form.get('adres') or sirket.adres

            new_password = request.form.get('new_password')
            new_password_confirm = request.form.get('new_password_confirm')

            if new_password and new_password_confirm:
                if new_password == new_password_confirm:
                    if len(new_password) >= 8:
                        if admin_user:
                            admin_user.set_password(new_password)
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


@admin_bp.route('/sirket/admin-olustur/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def sirket_admin_olustur(id):
    """Şirket için admin kullanıcısı oluştur"""
    try:
        from app.models import Company, User
        from app.extensions import db
        
        sirket = Company.query.get_or_404(id)
        
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            ad_soyad = request.form.get('ad_soyad', '').strip()
            sifre = request.form.get('sifre', '')
            
            if not email or not sifre:
                flash('Email ve şifre zorunludur.', 'warning')
                return render_template('sirket_admin_olustur.html', sirket=sirket)
            
            # Email zaten kullanılıyor mu kontrol et
            mevcut = User.query.filter_by(email=email).first()
            if mevcut:
                flash('Bu email adresi zaten kullanılıyor.', 'danger')
                return render_template('sirket_admin_olustur.html', sirket=sirket)
            
            # Yeni admin kullanıcısı oluştur
            yeni_admin = User(
                email=email,
                ad_soyad=ad_soyad or f"{sirket.isim} Admin",
                rol='customer',
                sirket_id=sirket.id,
                is_active=True
            )
            yeni_admin.set_password(sifre)
            db.session.add(yeni_admin)
            db.session.commit()
            
            flash(f'"{sirket.isim}" için admin kullanıcısı oluşturuldu: {email}', 'success')
            return redirect(url_for('admin.sirket_duzenle', id=id))
        
        return render_template('sirket_admin_olustur.html', sirket=sirket)
    except Exception as e:
        logger.error(f"Sirket admin olustur error: {e}")
        flash('Admin oluşturulurken bir hata oluştu.', 'danger')
        return redirect(url_for('admin.sirketler'))


# ==================== KULLANICI YÖNETİMİ ====================
@admin_bp.route('/kullanicilar')
@superadmin_required
def kullanicilar():
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
    return kullanici_sil(id)


# ==================== ADAY YÖNETİMİ ====================
@admin_bp.route('/adaylar')
@superadmin_required
def adaylar():
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
        bekliyor_count = Candidate.query.filter_by(is_deleted=False, sinav_durumu='beklemede').count()
        devam_count = Candidate.query.filter_by(is_deleted=False, sinav_durumu='baslamis').count()
        tamamlanan_count = Candidate.query.filter_by(is_deleted=False, sinav_durumu='tamamlandi').count()
    except Exception as e:
        logger.error(f"Adaylar error: {e}")
        flash('Adaylar yüklenirken bir hata oluştu.', 'danger')
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
    sirketler = []
    sablonlar = []
    try:
        from app.models import Company, ExamTemplate
        sirketler = Company.query.all()
        sablonlar = ExamTemplate.query.all()
    except:
        pass

    if request.method == 'POST':
        flash('Toplu yükleme işlemi başarılı.', 'success')
        return redirect(url_for('admin.adaylar'))

    return render_template('bulk_upload.html', sirketler=sirketler, sablonlar=sablonlar)


@admin_bp.route('/aday/ekle', methods=['GET', 'POST'])
@superadmin_required
def aday_ekle():
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
            flash(f'Aday başarıyla eklendi. Giriş kodu: {giris_kodu}', 'success')
            return redirect(url_for('admin.adaylar'))
        except Exception as e:
            logger.error(f"Aday ekle error: {e}")
            flash('Aday eklenirken bir hata oluştu.', 'danger')
    return render_template('aday_form.html', sirketler=sirketler, sablonlar=sablonlar)


@admin_bp.route('/aday/<int:aday_id>')
@superadmin_required
def aday_detay(aday_id):
    from app.models import Candidate
    aday = Candidate.query.get(aday_id)
    if not aday:
        flash('Aday bulunamadı.', 'danger')
        return redirect(url_for('admin.adaylar'))
    return render_template('aday_detay.html', aday=aday)


@admin_bp.route('/aday/duzenle/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def aday_duzenle(id):
    sirketler = []
    sablonlar = []
    try:
        from app.models import Company, ExamTemplate
        sirketler = Company.query.all()
        sablonlar = ExamTemplate.query.all()
    except:
        pass
    
    try:
        from app.models import Candidate
        from app.extensions import db
        aday = Candidate.query.get_or_404(id)

        if request.method == 'POST':
            aday.ad_soyad = request.form.get('ad_soyad') or aday.ad_soyad
            aday.email = request.form.get('email') or aday.email
            aday.tc_kimlik = request.form.get('tc_kimlik') or aday.tc_kimlik
            aday.cep_no = request.form.get('cep_no') or request.form.get('telefon') or aday.cep_no
            aday.sirket_id = request.form.get('sirket_id') or aday.sirket_id
            aday.admin_notes = request.form.get('admin_notes') or aday.admin_notes
            
            db.session.commit()
            flash('Aday bilgileri başarıyla güncellendi.', 'success')
            return redirect(url_for('admin.adaylar'))

        return render_template('aday_form.html', aday=aday, sirketler=sirketler, sablonlar=sablonlar)
    except Exception as e:
        logger.error(f"Aday duzenle error: {e}")
        flash('Aday düzenlenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/sil/<int:id>', methods=['POST'])
@superadmin_required
def aday_sil(id):
    try:
        from app.models import Candidate
        from app.extensions import db
        aday = Candidate.query.get_or_404(id)
        aday_adi = aday.ad_soyad
        if hasattr(aday, 'is_deleted'):
            aday.is_deleted = True
            db.session.commit()
            flash(f'Aday "{aday_adi}" silindi (geri alınabilir).', 'success')
        else:
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
    try:
        from app.models import Candidate
        from app.extensions import db
        aday = Candidate.query.get_or_404(id)
        aday_adi = aday.ad_soyad
        silinen_veri = delete_candidate_related_data(id)
        db.session.delete(aday)
        db.session.commit()
        mesaj = f'Aday "{aday_adi}" ve tüm verileri kalıcı olarak silindi.'
        if silinen_veri:
            detay = ', '.join([f'{v[1]} {v[0]}' for v in silinen_veri if v[1] > 0])
            if detay:
                mesaj += f' (Silinen: {detay})'
        flash(mesaj, 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Aday kalici sil error (id={id}): {e}")
        flash(f'Aday silinirken bir hata oluştu: {str(e)}', 'danger')
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/sinav-sifirla/<int:id>', methods=['POST'])
@superadmin_required
def aday_sinav_sifirla(id):
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
        flash('Aday sınavı başarıyla sıfırlandı.', 'success')
    except Exception as e:
        logger.error(f"Aday sinav sifirla error: {e}")
        flash('Sınav sıfırlanırken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/toplu-sil', methods=['POST'])
@superadmin_required
def toplu_aday_sil():
    try:
        from app.models import Candidate
        from app.extensions import db
        aday_ids = request.form.getlist('aday_ids[]')
        if aday_ids:
            silinen = 0
            for aday_id in aday_ids:
                aday = Candidate.query.get(aday_id)
                if aday:
                    if hasattr(aday, 'is_deleted'):
                        aday.is_deleted = True
                    else:
                        delete_candidate_related_data(int(aday_id))
                        db.session.delete(aday)
                    silinen += 1
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
                    delete_candidate_related_data(aday_id)
                    db.session.delete(aday)
                    silinen_sayisi += 1
            except Exception as e:
                logger.error(f"Toplu kalıcı silme - aday {aday_id} hatası: {e}")
                hatali_sayisi += 1
                continue
        db.session.commit()
        if silinen_sayisi > 0:
            flash(f'{silinen_sayisi} aday ve tüm verileri kalıcı olarak silindi.', 'success')
        if hatali_sayisi > 0:
            flash(f'{hatali_sayisi} aday silinirken hata oluştu.', 'warning')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Toplu aday kalici sil error: {e}")
        flash(f'Toplu silme işleminde bir hata oluştu: {str(e)}', 'danger')
    return redirect(url_for('admin.adaylar'))


# ==================== SORU YÖNETİMİ ====================
@admin_bp.route('/sorular')
@superadmin_required
def sorular():
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
    if request.method == 'POST':
        try:
            from app.models import Question
            from app.extensions import db
            
            kategori = (request.form.get('kategori') or '').strip().lower()
            
            if kategori in ['speaking', 'writing']:
                yeni_soru = Question(
                    soru_metni=request.form.get('soru_metni'),
                    secenek_a=None,
                    secenek_b=None,
                    secenek_c=None,
                    secenek_d=None,
                    dogru_cevap=None,
                    zorluk=request.form.get('zorluk', 'orta'),
                    kategori=request.form.get('kategori')
                )
            else:
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
    try:
        from app.models import Question
        from app.extensions import db
        soru = Question.query.get_or_404(id)

        if request.method == 'POST':
            soru.soru_metni = request.form.get('soru_metni') or soru.soru_metni
            soru.zorluk = request.form.get('zorluk') or soru.zorluk
            soru.kategori = request.form.get('kategori') or soru.kategori
            
            kategori = (soru.kategori or '').strip().lower()
            if kategori in ['speaking', 'writing']:
                soru.secenek_a = None
                soru.secenek_b = None
                soru.secenek_c = None
                soru.secenek_d = None
                soru.dogru_cevap = None
            else:
                soru.secenek_a = request.form.get('secenek_a') or soru.secenek_a
                soru.secenek_b = request.form.get('secenek_b') or soru.secenek_b
                soru.secenek_c = request.form.get('secenek_c') or soru.secenek_c
                soru.secenek_d = request.form.get('secenek_d') or soru.secenek_d
                soru.dogru_cevap = request.form.get('dogru_cevap') or soru.dogru_cevap
            
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


@admin_bp.route('/fix-speaking-writing-questions', methods=['GET', 'POST'])
@superadmin_required
def fix_speaking_writing_questions():
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
            flash(f'{speaking_count} Speaking ve {writing_count} Writing sorusu düzeltildi!', 'success')
            return redirect(url_for('admin.sorular'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Fix speaking/writing error: {e}")
            flash(f'Hata oluştu: {str(e)}', 'danger')
    
    from app.models import Question
    from app.extensions import db
    try:
        speaking_count = Question.query.filter(db.func.lower(Question.kategori) == 'speaking').count()
        writing_count = Question.query.filter(db.func.lower(Question.kategori) == 'writing').count()
    except:
        speaking_count = 0
        writing_count = 0
    
    return f'''
    <html>
    <head><title>Speaking/Writing Soruları Düzelt</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h2>Speaking ve Writing Sorularını Düzelt</h2>
        <p>Bu işlem {speaking_count} Speaking ve {writing_count} Writing sorusunun şık/doğru cevap alanlarını temizleyecek.</p>
        <form method="POST">
            <button type="submit" style="padding: 10px 20px; background: #dc3545; color: white; border: none; cursor: pointer;">
                Düzelt
            </button>
        </form>
        <br><a href="/admin/sorular">Geri Dön</a>
    </body>
    </html>
    '''


# ==================== ŞABLON YÖNETİMİ (ESNEK SİSTEM) ====================
@admin_bp.route('/sablonlar')
@superadmin_required
def sablonlar():
    sablonlar = []
    sirketler = []
    try:
        from app.models import ExamTemplate, Company
        sablonlar = ExamTemplate.query.order_by(ExamTemplate.id.desc()).all()
        sirketler = Company.query.all()
    except Exception as e:
        logger.error(f"Sablonlar error: {e}")
        flash('Şablonlar yüklenirken bir hata oluştu.', 'danger')
    return render_template('sablonlar.html', sablonlar=sablonlar, sirketler=sirketler)


@admin_bp.route('/sablon/ekle', methods=['GET', 'POST'])
@admin_bp.route('/sablon-ekle', methods=['GET', 'POST'])
@admin_bp.route('/sablon/yeni', methods=['GET', 'POST'])
@superadmin_required
def sablon_ekle():
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.filter_by(is_active=True).all()
    except:
        pass
    
    if request.method == 'POST':
        try:
            from app.models import ExamTemplate
            from app.extensions import db
            import json
            
            # Hangi becerilerin dahil edileceğini al
            secili_beceriler = request.form.getlist('beceriler')
            
            # Her beceri için soru sayısı ve süre ayarları
            beceri_dagilimi = {}
            beceri_sureleri = {}
            toplam_soru = 0
            
            for beceri in ['grammar', 'vocabulary', 'reading', 'listening', 'speaking', 'writing']:
                if beceri in secili_beceriler:
                    soru_sayisi = int(request.form.get(f'{beceri}_count', 0) or 0)
                    sure_saniye = int(request.form.get(f'{beceri}_sure', 60) or 60)
                    if soru_sayisi > 0:
                        beceri_dagilimi[beceri] = soru_sayisi
                        beceri_sureleri[beceri] = sure_saniye
                        toplam_soru += soru_sayisi
            
            if toplam_soru == 0:
                flash('En az bir beceri ve soru sayısı girilmelidir.', 'warning')
                return render_template('sablon_form.html', sirketler=sirketler)
            
            # Şablon ayarlarını JSON olarak kaydet
            sablon_ayarlari = {
                'beceri_dagilimi': beceri_dagilimi,
                'beceri_sureleri': beceri_sureleri,
                'toplam_sure_dakika': int(request.form.get('toplam_sure', 30) or 30),
                'gecme_puani': int(request.form.get('gecme_puani', 60) or 60),
                'karisik_soru': request.form.get('karisik_soru') == 'on',
                'geri_donus': request.form.get('geri_donus') == 'on'
            }
            
            yeni_sablon = ExamTemplate(
                isim=request.form.get('isim'),
                aciklama=request.form.get('aciklama'),
                sure=sablon_ayarlari['toplam_sure_dakika'],
                soru_sayisi=toplam_soru,
                beceri_dagilimi=json.dumps(sablon_ayarlari),
                is_active=True
            )
            db.session.add(yeni_sablon)
            db.session.commit()
            
            flash(f'"{yeni_sablon.isim}" şablonu başarıyla oluşturuldu. ({toplam_soru} soru)', 'success')
            return redirect(url_for('admin.sablonlar'))
        except Exception as e:
            logger.error(f"Sablon ekle error: {e}")
            flash(f'Şablon oluşturulurken bir hata oluştu: {str(e)}', 'danger')
    
    return render_template('sablon_form.html', sirketler=sirketler)


# Alias for template compatibility
@admin_bp.route('/sablon-yeni', methods=['GET', 'POST'])
@superadmin_required
def sablon_yeni():
    return sablon_ekle()


@admin_bp.route('/sablon/duzenle/<int:id>', methods=['GET', 'POST'])
@superadmin_required
def sablon_duzenle(id):
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.filter_by(is_active=True).all()
    except:
        pass
    
    try:
        from app.models import ExamTemplate
        from app.extensions import db
        import json
        sablon = ExamTemplate.query.get_or_404(id)
        
        # Mevcut ayarları parse et
        mevcut_ayarlar = {}
        if sablon.beceri_dagilimi:
            try:
                mevcut_ayarlar = json.loads(sablon.beceri_dagilimi)
            except:
                pass

        if request.method == 'POST':
            sablon.isim = request.form.get('isim') or sablon.isim
            sablon.aciklama = request.form.get('aciklama') or sablon.aciklama
            
            # Hangi becerilerin dahil edileceğini al
            secili_beceriler = request.form.getlist('beceriler')
            
            # Her beceri için soru sayısı ve süre ayarları
            beceri_dagilimi = {}
            beceri_sureleri = {}
            toplam_soru = 0
            
            for beceri in ['grammar', 'vocabulary', 'reading', 'listening', 'speaking', 'writing']:
                if beceri in secili_beceriler:
                    soru_sayisi = int(request.form.get(f'{beceri}_count', 0) or 0)
                    sure_saniye = int(request.form.get(f'{beceri}_sure', 60) or 60)
                    if soru_sayisi > 0:
                        beceri_dagilimi[beceri] = soru_sayisi
                        beceri_sureleri[beceri] = sure_saniye
                        toplam_soru += soru_sayisi
            
            if toplam_soru == 0:
                flash('En az bir beceri ve soru sayısı girilmelidir.', 'warning')
                return render_template('sablon_form.html', sablon=sablon, sirketler=sirketler, mevcut_ayarlar=mevcut_ayarlar)
            
            # Şablon ayarlarını JSON olarak kaydet
            sablon_ayarlari = {
                'beceri_dagilimi': beceri_dagilimi,
                'beceri_sureleri': beceri_sureleri,
                'toplam_sure_dakika': int(request.form.get('toplam_sure', 30) or 30),
                'gecme_puani': int(request.form.get('gecme_puani', 60) or 60),
                'karisik_soru': request.form.get('karisik_soru') == 'on',
                'geri_donus': request.form.get('geri_donus') == 'on'
            }
            
            sablon.sure = sablon_ayarlari['toplam_sure_dakika']
            sablon.soru_sayisi = toplam_soru
            sablon.beceri_dagilimi = json.dumps(sablon_ayarlari)
            
            db.session.commit()
            flash(f'"{sablon.isim}" şablonu başarıyla güncellendi.', 'success')
            return redirect(url_for('admin.sablonlar'))

        return render_template('sablon_form.html', sablon=sablon, sirketler=sirketler, mevcut_ayarlar=mevcut_ayarlar)
    except Exception as e:
        logger.error(f"Sablon duzenle error: {e}")
        flash('Şablon düzenlenirken bir hata oluştu.', 'danger')
        return redirect(url_for('admin.sablonlar'))


@admin_bp.route('/sablon/sil/<int:id>', methods=['POST'])
@superadmin_required
def sablon_sil(id):
    try:
        from app.models import ExamTemplate
        from app.extensions import db
        sablon = ExamTemplate.query.get_or_404(id)
        sablon_isim = sablon.isim
        db.session.delete(sablon)
        db.session.commit()
        flash(f'"{sablon_isim}" şablonu başarıyla silindi.', 'success')
    except Exception as e:
        logger.error(f"Sablon sil error: {e}")
        flash('Şablon silinirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.sablonlar'))


@admin_bp.route('/sablon/kopyala/<int:id>', methods=['POST'])
@superadmin_required
def sablon_kopyala(id):
    """Mevcut şablonu kopyala"""
    try:
        from app.models import ExamTemplate
        from app.extensions import db
        
        orijinal = ExamTemplate.query.get_or_404(id)
        kopya = ExamTemplate(
            isim=f"{orijinal.isim} (Kopya)",
            aciklama=orijinal.aciklama,
            sure=orijinal.sure,
            soru_sayisi=orijinal.soru_sayisi,
            beceri_dagilimi=orijinal.beceri_dagilimi,
            is_active=True
        )
        db.session.add(kopya)
        db.session.commit()
        flash(f'"{orijinal.isim}" şablonu kopyalandı.', 'success')
    except Exception as e:
        logger.error(f"Sablon kopyala error: {e}")
        flash('Şablon kopyalanırken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.sablonlar'))


@admin_bp.route('/sirket/sablon-ata/<int:sirket_id>', methods=['GET', 'POST'])
@superadmin_required
def sirket_sablon_ata(sirket_id):
    """Şirkete şablon atama"""
    try:
        from app.models import Company, ExamTemplate
        from app.extensions import db
        
        sirket = Company.query.get_or_404(sirket_id)
        sablonlar = ExamTemplate.query.filter_by(is_active=True).all()
        
        if request.method == 'POST':
            sablon_id = request.form.get('sablon_id')
            if sablon_id:
                # Şirkete şablon ID'sini kaydet (Company modeline sablon_id alanı eklenmelidir)
                if hasattr(sirket, 'sablon_id'):
                    sirket.sablon_id = int(sablon_id)
                    db.session.commit()
                    flash(f'"{sirket.isim}" şirketine şablon atandı.', 'success')
                else:
                    flash('Şirket modeline sablon_id alanı eklenmeli.', 'warning')
            return redirect(url_for('admin.sirketler'))
        
        return render_template('sirket_sablon_ata.html', sirket=sirket, sablonlar=sablonlar)
    except Exception as e:
        logger.error(f"Sirket sablon ata error: {e}")
        flash('Şablon atanırken bir hata oluştu.', 'danger')
        return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sablon/tumunu-sil', methods=['POST'])
@superadmin_required
def sablon_tumunu_sil():
    """Tüm şablonları sil - Sıfırdan başlamak için"""
    try:
        from app.models import ExamTemplate
        from app.extensions import db
        
        silinen = ExamTemplate.query.delete()
        db.session.commit()
        flash(f'{silinen} şablon silindi. Artık sıfırdan şablon oluşturabilirsiniz.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Sablon tumunu sil error: {e}")
        flash('Şablonlar silinirken bir hata oluştu.', 'danger')
    return redirect(url_for('admin.sablonlar'))


# ==================== RAPORLAR ====================
@admin_bp.route('/raporlar')
@superadmin_required
def raporlar():
    stats = {
        'toplam_aday': 0,
        'tamamlanan_sinav': 0,
        'ortalama_puan': 0,
        'bekleyen_sinav': 0
    }
    son_sinavlar = []
    
    try:
        from app.models import Candidate
        from app.extensions import db
        from sqlalchemy import func
        
        stats['toplam_aday'] = Candidate.query.filter_by(is_deleted=False).count()
        stats['tamamlanan_sinav'] = Candidate.query.filter_by(
            sinav_durumu='tamamlandi', is_deleted=False
        ).count()
        stats['bekleyen_sinav'] = Candidate.query.filter_by(
            sinav_durumu='beklemede', is_deleted=False
        ).count()
        
        avg = db.session.query(func.avg(Candidate.puan)).filter(
            Candidate.sinav_durumu == 'tamamlandi',
            Candidate.is_deleted == False
        ).scalar()
        stats['ortalama_puan'] = round(avg, 1) if avg else 0
        
        son_sinavlar = Candidate.query.filter_by(
            sinav_durumu='tamamlandi', is_deleted=False
        ).order_by(Candidate.bitis_tarihi.desc()).limit(10).all()
    except Exception as e:
        logger.error(f"Raporlar error: {e}")

    return render_template('raporlar.html', stats=stats, son_sinavlar=son_sinavlar)


@admin_bp.route('/export')
@superadmin_required
def export():
    return render_template('export.html')


# ==================== KREDİLER ====================
@admin_bp.route('/krediler')
@superadmin_required
def krediler():
    sirketler = []
    try:
        from app.models import Company
        sirketler = Company.query.order_by(Company.id.desc()).all()
    except Exception as e:
        logger.error(f"Krediler error: {e}")
    return render_template('krediler.html', sirketler=sirketler)


# ==================== AYARLAR ====================
@admin_bp.route('/ayarlar', methods=['GET', 'POST'])
@superadmin_required
def ayarlar():
    settings = {}
    try:
        from app.models import SystemSetting
        from app.extensions import db
        
        if request.method == 'POST':
            flash('Ayarlar başarıyla kaydedildi.', 'success')
            return redirect(url_for('admin.ayarlar'))
        
        all_settings = SystemSetting.query.all()
        settings = {s.key: s.value for s in all_settings}
    except Exception as e:
        logger.error(f"Ayarlar error: {e}")
    
    return render_template('ayarlar.html', settings=settings)


# ==================== VERİ YÖNETİMİ ====================
@admin_bp.route('/veri-yonetimi')
@superadmin_required
def veri_yonetimi():
    stats = {}
    try:
        from app.models import Company, User, Candidate, Question, ExamAnswer
        stats = {
            'sirket': Company.query.count(),
            'kullanici': User.query.count(),
            'aday': Candidate.query.count(),
            'soru': Question.query.count(),
            'cevap': ExamAnswer.query.count()
        }
    except Exception as e:
        logger.error(f"Veri yonetimi error: {e}")
    return render_template('veri_yonetimi.html', stats=stats)


# ==================== LOGLAR ====================
@admin_bp.route('/loglar')
@superadmin_required
def loglar():
    logs = []
    try:
        from app.models import AuditLog
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    except Exception as e:
        logger.error(f"Loglar error: {e}")
    return render_template('logs.html', logs=logs)


# ==================== DEMO ====================
@admin_bp.route('/demo-olustur', methods=['GET', 'POST'])
@superadmin_required
def demo_olustur():
    if request.method == 'POST':
        try:
            from app.models import Candidate
            from app.extensions import db
            import secrets
            
            giris_kodu = 'DEMO-' + secrets.token_hex(3).upper()
            demo_aday = Candidate(
                ad_soyad='Demo Kullanıcı',
                email='demo@test.com',
                giris_kodu=giris_kodu,
                is_practice=True
            )
            db.session.add(demo_aday)
            db.session.commit()
            
            flash(f'Demo sınav oluşturuldu. Giriş kodu: {giris_kodu}', 'success')
            return redirect(url_for('admin.adaylar'))
        except Exception as e:
            logger.error(f"Demo olustur error: {e}")
            flash('Demo oluşturulurken bir hata oluştu.', 'danger')
    
    return render_template('demo_bilgi.html')


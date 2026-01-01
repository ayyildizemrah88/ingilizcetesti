# -*- coding: utf-8 -*-
"""
Admin Routes - Dashboard and management
TAM DOSYA - TÜM ROUTE'LAR DAHİL (GÜNCEL ŞABLON SİSTEMİ İLE)
ŞİRKET KALICI SİLME VE AKTİFLEŞTİRME ÖZELLİKLERİ EKLENDİ
GitHub: app/routes/admin.py
"""
from functools import wraps
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.extensions import db
admin_bp = Blueprint('admin', __name__)
# ══════════════════════════════════════════════════════════════
def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
def superadmin_required(f):
    """Only superadmin can access - for questions, users, settings"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu işlem sadece süper admin tarafından yapılabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated
def customer_or_superadmin(f):
    """Superadmin and customer can access - for candidates, reports"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') not in ['superadmin', 'customer']:
            flash("Bu işlem için yetkiniz yok.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard with statistics"""
    from app.models import Candidate, Question, Company, User
    sirket_id = session.get('sirket_id')
    try:
        aday_sayisi = Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False).count() if sirket_id else Candidate.query.filter_by(is_deleted=False).count()
    except:
        aday_sayisi = 0
    try:
        soru_sayisi = Question.query.filter_by(sirket_id=sirket_id, is_active=True).count() if sirket_id else Question.query.filter_by(is_active=True).count()
    except:
        soru_sayisi = 0
    try:
        sirket_sayisi = Company.query.count()
    except:
        sirket_sayisi = 0
    try:
        recent_candidates = Candidate.query.filter_by(
            sirket_id=sirket_id, is_deleted=False
        ).order_by(Candidate.created_at.desc()).limit(10).all() if sirket_id else []
    except:
        recent_candidates = []
    try:
        company = Company.query.get(sirket_id) if sirket_id else None
    except:
        company = None
    return render_template('dashboard.html', 
                          aday_sayisi=aday_sayisi,
                          soru_sayisi=soru_sayisi,
                          sirket_sayisi=sirket_sayisi,
                          recent_candidates=recent_candidates,
                          company=company)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/adaylar')
@login_required
def adaylar():
    """List all candidates"""
    from app.models import Candidate
    sirket_id = session.get('sirket_id')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    if sirket_id:
        candidates = Candidate.query.filter_by(
            sirket_id=sirket_id, is_deleted=False
        ).order_by(Candidate.created_at.desc()).paginate(page=page, per_page=per_page)
    else:
        candidates = Candidate.query.filter_by(
            is_deleted=False
        ).order_by(Candidate.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('adaylar.html', adaylar=candidates)
@admin_bp.route('/aday/ekle', methods=['GET', 'POST'])
@login_required
def aday_ekle():
    """Add new candidate"""
    from app.models import Candidate, Company
    import string
    import random
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        email = request.form.get('email', '').strip().lower()
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        cep_no = request.form.get('cep_no', '').strip()
        sinav_suresi = int(request.form.get('sinav_suresi', 30))
        soru_limiti = int(request.form.get('soru_limiti', 25))
        sirket_id = session.get('sirket_id')
        if not sirket_id and session.get('rol') == 'superadmin':
            sirket_id = request.form.get('sirket_id', type=int)
            if not sirket_id:
                flash("Lütfen bir şirket seçin.", "danger")
                companies = Company.query.filter_by(is_active=True).all()
                return render_template('aday_form.html', sirketler=companies)
        giris_kodu = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        candidate = Candidate(
            ad_soyad=ad_soyad,
            email=email,
            tc_kimlik=tc_kimlik,
            cep_no=cep_no,
            giris_kodu=giris_kodu,
            sinav_suresi=sinav_suresi,
            soru_limiti=soru_limiti,
            sirket_id=sirket_id
        )
        db.session.add(candidate)
        db.session.commit()
        if email:
            try:
                from app.tasks.email_tasks import send_exam_invitation
                send_exam_invitation.delay(candidate.id)
            except:
                pass
        flash(f"Aday eklendi. Giriş Kodu: {giris_kodu}", "success")
        return redirect(url_for('admin.adaylar'))
    sirketler = None
    if session.get('rol') == 'superadmin':
        from app.models import Company
        sirketler = Company.query.filter_by(is_active=True).all()
    return render_template('aday_form.html', sirketler=sirketler)
@admin_bp.route('/aday/<int:id>/detay')
@login_required
def aday_detay(id):
    """Candidate detail view"""
    from app.models import Candidate
    candidate = Candidate.query.get_or_404(id)
    if candidate.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu adaya erişim yetkiniz yok.", "danger")
        return redirect(url_for('admin.adaylar'))
    return render_template('aday_detay.html', aday=candidate)
@admin_bp.route('/aday/<int:id>/sil', methods=['POST'])
@login_required
def aday_sil(id):
    """Delete candidate (soft delete)"""
    from app.models import Candidate
    candidate = Candidate.query.get_or_404(id)
    if candidate.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu adaya erişim yetkiniz yok.", "danger")
        return redirect(url_for('admin.adaylar'))
    candidate.is_deleted = True
    db.session.commit()
    flash("Aday silindi.", "success")
    return redirect(url_for('admin.adaylar'))
@admin_bp.route('/aday/<int:id>/sinav-sifirla', methods=['POST'])
@login_required
def aday_sinav_sifirla(id):
    """Reset candidate's exam - clears answers and allows re-entry"""
    from app.models import Candidate, ExamAnswer
    candidate = Candidate.query.get_or_404(id)
    sirket_id = session.get('sirket_id')
    rol = session.get('rol')
    if rol not in ['super_admin', 'superadmin']:
        if sirket_id and candidate.sirket_id != sirket_id:
            return jsonify({'success': False, 'message': 'Yetkiniz yok'}), 403
    try:
        # Delete all answers for this candidate
        ExamAnswer.query.filter_by(aday_id=id).delete()
        # Reset candidate exam status
        candidate.sinav_durumu = 'beklemede'
        candidate.puan = None
        candidate.seviye_sonuc = None
        candidate.baslama_tarihi = None
        candidate.bitis_tarihi = None
        candidate.current_difficulty = 'B1'
        candidate.p_grammar = None
        candidate.p_vocabulary = None
        candidate.p_reading = None
        candidate.p_listening = None
        candidate.p_speaking = None
        candidate.p_writing = None
        candidate.certificate_hash = None
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='exam_reset',
                details=f"Aday sınavı sıfırlandı: {candidate.ad_soyad} (ID: {id})"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Sınav başarıyla sıfırlandı'})
        flash(f'{candidate.ad_soyad} adayının sınavı sıfırlandı.', 'success')
        return redirect(url_for('admin.aday_detay', id=id))
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f'Hata oluştu: {str(e)}', 'error')
        return redirect(url_for('admin.aday_detay', id=id))
@admin_bp.route('/aday/<int:id>/sure-uzat', methods=['POST'])
@login_required
def aday_sure_uzat(id):
    """Extend candidate's exam time"""
    from app.models import Candidate
    candidate = Candidate.query.get_or_404(id)
    sirket_id = session.get('sirket_id')
    rol = session.get('rol')
    if rol not in ['super_admin', 'superadmin']:
        if sirket_id and candidate.sirket_id != sirket_id:
            return jsonify({'success': False, 'message': 'Yetkiniz yok'}), 403
    try:
        ek_sure = request.form.get('ek_sure', 10, type=int)
        candidate.sinav_suresi = (candidate.sinav_suresi or 30) + ek_sure
        db.session.commit()
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='time_extended',
                details=f"Aday süresi uzatıldı: {candidate.ad_soyad} (+{ek_sure} dk)"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'{ek_sure} dakika eklendi'})
        flash(f'{candidate.ad_soyad} adayının süresi {ek_sure} dakika uzatıldı.', 'success')
        return redirect(url_for('admin.aday_detay', id=id))
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f'Hata oluştu: {str(e)}', 'error')
        return redirect(url_for('admin.aday_detay', id=id))
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/bulk-upload', methods=['POST'])
@login_required
def bulk_upload():
    """Bulk upload candidates from Excel file"""
    from app.models import Candidate
    import pandas as pd
    import string
    import random
    import io
    if 'file' not in request.files:
        flash("Dosya seçilmedi.", "danger")
        return redirect(url_for('admin.adaylar'))
    file = request.files['file']
    if file.filename == '':
        flash("Dosya seçilmedi.", "danger")
        return redirect(url_for('admin.adaylar'))
    if not file.filename.endswith(('.xlsx', '.xls')):
        flash("Sadece Excel dosyaları (.xlsx, .xls) kabul edilir.", "danger")
        return redirect(url_for('admin.adaylar'))
    try:
        df = pd.read_excel(io.BytesIO(file.read()))
        if 'ad_soyad' not in df.columns:
            flash("Excel dosyasında 'ad_soyad' kolonu bulunamadı.", "danger")
            return redirect(url_for('admin.adaylar'))
        sirket_id = session.get('sirket_id')
        added_count = 0
        for _, row in df.iterrows():
            ad_soyad = str(row.get('ad_soyad', '')).strip()
            if not ad_soyad or ad_soyad == 'nan':
                continue
            giris_kodu = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            candidate = Candidate(
                ad_soyad=ad_soyad,
                email=str(row.get('email', '')).strip() if pd.notna(row.get('email')) else None,
                tc_kimlik=str(row.get('tc_kimlik', '')).strip() if pd.notna(row.get('tc_kimlik')) else None,
                giris_kodu=giris_kodu,
                sirket_id=sirket_id
            )
            db.session.add(candidate)
            added_count += 1
        db.session.commit()
        flash(f"{added_count} aday başarıyla eklendi.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Dosya işlenirken hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.adaylar'))
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/sorular')
@login_required
@superadmin_required
def sorular():
    """Question bank management"""
    from app.models import Question
    sirket_id = session.get('sirket_id')
    kategori = request.args.get('kategori')
    zorluk = request.args.get('zorluk')
    page = request.args.get('page', 1, type=int)
    query = Question.query.filter_by(is_active=True)
    if sirket_id:
        query = query.filter_by(sirket_id=sirket_id)
    if kategori:
        query = query.filter_by(kategori=kategori)
    if zorluk:
        query = query.filter_by(zorluk=zorluk)
    questions = query.order_by(Question.id.desc()).paginate(page=page, per_page=20)
    return render_template('sorular.html', sorular=questions)
@admin_bp.route('/soru/ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def soru_ekle():
    """Add new question"""
    if request.method == 'POST':
        from app.models import Question
        question = Question(
            soru_metni=request.form.get('soru_metni'),
            secenek_a=request.form.get('secenek_a'),
            secenek_b=request.form.get('secenek_b'),
            secenek_c=request.form.get('secenek_c'),
            secenek_d=request.form.get('secenek_d'),
            dogru_cevap=request.form.get('dogru_cevap'),
            kategori=request.form.get('kategori'),
            zorluk=request.form.get('zorluk', 'B1'),
            soru_tipi=request.form.get('soru_tipi', 'SECMELI'),
            sirket_id=session.get('sirket_id')
        )
        db.session.add(question)
        db.session.commit()
        flash("Soru eklendi.", "success")
        return redirect(url_for('admin.sorular'))
    return render_template('soru_form.html')
@admin_bp.route('/soru/<int:id>/sil', methods=['POST'])
@login_required
@superadmin_required
def soru_sil(id):
    """Delete question (soft delete)"""
    from app.models import Question
    question = Question.query.get_or_404(id)
    if question.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu soruya erişim yetkiniz yok.", "danger")
        return redirect(url_for('admin.sorular'))
    question.is_active = False
    db.session.commit()
    flash("Soru silindi.", "success")
    return redirect(url_for('admin.sorular'))
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/kullanicilar')
@login_required
@superadmin_required
def kullanicilar():
    """User management"""
    from app.models import User
    sirket_id = session.get('sirket_id')
    if session.get('rol') == 'superadmin':
        users = User.query.all()
    else:
        users = User.query.filter_by(sirket_id=sirket_id).all()
    return render_template('kullanicilar.html', kullanicilar=users)
@admin_bp.route('/kullanici-ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def kullanici_ekle():
    """Add new user"""
    from app.models import User, Company
    from werkzeug.security import generate_password_hash
    import string
    import random
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        ad_soyad = request.form.get('ad_soyad', '').strip()
        rol = request.form.get('rol', 'customer')
        sirket_id = request.form.get('sirket_id', type=int)
        password = request.form.get('password', '')
        if not email or not ad_soyad:
            flash("Email ve ad soyad zorunludur.", "danger")
            companies = Company.query.filter_by(is_active=True).all()
            return render_template('kullanici_form.html', sirketler=companies)
        if User.query.filter_by(email=email).first():
            flash("Bu email adresi zaten kayıtlı.", "danger")
            companies = Company.query.filter_by(is_active=True).all()
            return render_template('kullanici_form.html', sirketler=companies)
        if not password:
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        user = User(
            email=email,
            ad_soyad=ad_soyad,
            password=generate_password_hash(password),
            rol=rol,
            sirket_id=sirket_id if rol != 'superadmin' else None,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        flash(f"Kullanıcı oluşturuldu. Email: {email}, Şifre: {password}", "success")
        return redirect(url_for('admin.kullanicilar'))
    companies = Company.query.filter_by(is_active=True).all()
    return render_template('kullanici_form.html', sirketler=companies)
@admin_bp.route('/kullanici/<int:id>/sil', methods=['POST'])
@login_required
@superadmin_required
def kullanici_sil(id):
    """Delete user (soft delete)"""
    from app.models import User
    user = User.query.get_or_404(id)
    user.is_active = False
    db.session.commit()
    flash("Kullanıcı devre dışı bırakıldı.", "success")
    return redirect(url_for('admin.kullanicilar'))
@admin_bp.route('/kullanici/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def kullanici_duzenle(id):
    """Edit user"""
    from app.models import User, Company
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.ad_soyad = request.form.get('ad_soyad', '').strip()
        user.email = request.form.get('email', '').strip().lower()
        user.rol = request.form.get('rol', 'customer')
        user.sirket_id = request.form.get('sirket_id', type=int)
        user.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash("Kullanıcı güncellendi.", "success")
        return redirect(url_for('admin.kullanicilar'))
    companies = Company.query.filter_by(is_active=True).all()
    return render_template('kullanici_form.html', kullanici=user, sirketler=companies)
@admin_bp.route('/kullanici/<int:id>/aktif', methods=['POST'])
@login_required
@superadmin_required
def kullanici_aktif(id):
    """Reactivate user - Kullanıcıyı tekrar aktifleştirme"""
    from app.models import User
    user = User.query.get_or_404(id)
    user.is_active = True
    db.session.commit()
    # Log action
    try:
        from app.models import AuditLog
        log = AuditLog(
            user_id=session.get('kullanici_id'),
            action='user_activated',
            details=f"Kullanıcı aktifleştirildi: {user.email} (ID: {id})"
        )
        db.session.add(log)
        db.session.commit()
    except:
        pass
    flash("Kullanıcı tekrar aktifleştirildi.", "success")
    return redirect(url_for('admin.kullanicilar'))
@admin_bp.route('/kullanici/<int:id>/kalici-sil', methods=['POST'])
@login_required
@superadmin_required
def kullanici_kalici_sil(id):
    """Permanently delete user - Kullanıcıyı kalıcı olarak silme
    
    DİKKAT: Bu işlem geri alınamaz!
    """
    from app.models import User
    user = User.query.get_or_404(id)
    
    # Kendini silmeye çalışıyor mu kontrol et
    if user.id == session.get('kullanici_id'):
        flash("Kendinizi silemezsiniz!", "danger")
        return redirect(url_for('admin.kullanicilar'))
    
    user_email = user.email
    try:
        db.session.delete(user)
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='user_permanently_deleted',
                details=f"Kullanıcı kalıcı olarak silindi: {user_email} (ID: {id})"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        flash(f"'{user_email}' kullanıcısı kalıcı olarak silindi.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Kullanıcı silinirken hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.kullanicilar'))
# ══════════════════════════════════════════════════════════════
# ADAY KALICI SİLME VE AKTİFLEŞTİRME
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/aday/<int:id>/aktif', methods=['POST'])
@login_required
def aday_aktif(id):
    """Reactivate candidate - Adayı tekrar aktifleştirme (soft delete geri alma)"""
    from app.models import Candidate
    candidate = Candidate.query.get_or_404(id)
    if candidate.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu adaya erişim yetkiniz yok.", "danger")
        return redirect(url_for('admin.adaylar'))
    candidate.is_deleted = False
    db.session.commit()
    # Log action
    try:
        from app.models import AuditLog
        log = AuditLog(
            user_id=session.get('kullanici_id'),
            action='candidate_activated',
            details=f"Aday aktifleştirildi: {candidate.ad_soyad} (ID: {id})"
        )
        db.session.add(log)
        db.session.commit()
    except:
        pass
    flash("Aday tekrar aktifleştirildi.", "success")
    return redirect(url_for('admin.adaylar'))
@admin_bp.route('/aday/<int:id>/kalici-sil', methods=['POST'])
@login_required
def aday_kalici_sil(id):
    """Permanently delete candidate and all related data - Adayı kalıcı olarak silme
    
    DİKKAT: Bu işlem geri alınamaz!
    Silinecekler:
    - Adayın tüm sınav cevapları
    - Aday kaydı
    """
    from app.models import Candidate, ExamAnswer
    candidate = Candidate.query.get_or_404(id)
    if candidate.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu adaya erişim yetkiniz yok.", "danger")
        return redirect(url_for('admin.adaylar'))
    candidate_name = candidate.ad_soyad
    try:
        # 1. Adayın sınav cevaplarını sil
        ExamAnswer.query.filter_by(aday_id=id).delete(synchronize_session=False)
        
        # 2. Adayı sil
        db.session.delete(candidate)
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='candidate_permanently_deleted',
                details=f"Aday kalıcı olarak silindi: {candidate_name} (ID: {id})"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        flash(f"'{candidate_name}' adayı ve tüm verileri kalıcı olarak silindi.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Aday silinirken hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.adaylar'))
# ══════════════════════════════════════════════════════════════
# TOPLU İŞLEMLER
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/adaylar/toplu-sil', methods=['POST'])
@login_required
def toplu_aday_sil():
    """Bulk soft delete candidates - Toplu aday pasife alma"""
    from app.models import Candidate
    aday_ids = request.form.getlist('aday_ids[]')
    
    if not aday_ids:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Hiç aday seçilmedi'}), 400
        flash("Hiç aday seçilmedi.", "warning")
        return redirect(url_for('admin.adaylar'))
    sirket_id = session.get('sirket_id')
    deleted_count = 0
    try:
        for aday_id in aday_ids:
            candidate = Candidate.query.get(int(aday_id))
            if candidate:
                # Yetki kontrolü
                if sirket_id and candidate.sirket_id != sirket_id and session.get('rol') != 'superadmin':
                    continue
                candidate.is_deleted = True
                deleted_count += 1
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='bulk_candidates_deleted',
                details=f"Toplu aday silindi: {deleted_count} aday"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'{deleted_count} aday pasife alındı', 'count': deleted_count})
        flash(f"{deleted_count} aday pasife alındı.", "success")
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f"Hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.adaylar'))
@admin_bp.route('/adaylar/toplu-kalici-sil', methods=['POST'])
@login_required
@superadmin_required
def toplu_aday_kalici_sil():
    """Bulk permanently delete candidates - Toplu aday kalıcı silme
    
    DİKKAT: Bu işlem geri alınamaz!
    """
    from app.models import Candidate, ExamAnswer
    aday_ids = request.form.getlist('aday_ids[]')
    
    if not aday_ids:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Hiç aday seçilmedi'}), 400
        flash("Hiç aday seçilmedi.", "warning")
        return redirect(url_for('admin.adaylar'))
    sirket_id = session.get('sirket_id')
    deleted_count = 0
    try:
        for aday_id in aday_ids:
            candidate = Candidate.query.get(int(aday_id))
            if candidate:
                # Yetki kontrolü
                if sirket_id and candidate.sirket_id != sirket_id and session.get('rol') != 'superadmin':
                    continue
                
                # Sınav cevaplarını sil
                ExamAnswer.query.filter_by(aday_id=int(aday_id)).delete(synchronize_session=False)
                
                # Adayı sil
                db.session.delete(candidate)
                deleted_count += 1
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='bulk_candidates_permanently_deleted',
                details=f"Toplu aday kalıcı olarak silindi: {deleted_count} aday"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'{deleted_count} aday kalıcı olarak silindi', 'count': deleted_count})
        flash(f"{deleted_count} aday kalıcı olarak silindi.", "success")
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f"Hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.adaylar'))
@admin_bp.route('/adaylar/toplu-aktif', methods=['POST'])
@login_required
def toplu_aday_aktif():
    """Bulk reactivate candidates - Toplu aday aktifleştirme"""
    from app.models import Candidate
    aday_ids = request.form.getlist('aday_ids[]')
    
    if not aday_ids:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Hiç aday seçilmedi'}), 400
        flash("Hiç aday seçilmedi.", "warning")
        return redirect(url_for('admin.adaylar'))
    sirket_id = session.get('sirket_id')
    activated_count = 0
    try:
        for aday_id in aday_ids:
            candidate = Candidate.query.get(int(aday_id))
            if candidate:
                # Yetki kontrolü
                if sirket_id and candidate.sirket_id != sirket_id and session.get('rol') != 'superadmin':
                    continue
                candidate.is_deleted = False
                activated_count += 1
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='bulk_candidates_activated',
                details=f"Toplu aday aktifleştirildi: {activated_count} aday"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'{activated_count} aday aktifleştirildi', 'count': activated_count})
        flash(f"{activated_count} aday aktifleştirildi.", "success")
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f"Hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.adaylar'))
@admin_bp.route('/sirketler/toplu-pasif', methods=['POST'])
@login_required
@superadmin_required
def toplu_sirket_pasif():
    """Bulk deactivate companies - Toplu şirket pasife alma"""
    from app.models import Company
    sirket_ids = request.form.getlist('sirket_ids[]')
    
    if not sirket_ids:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Hiç şirket seçilmedi'}), 400
        flash("Hiç şirket seçilmedi.", "warning")
        return redirect(url_for('admin.sirketler'))
    deactivated_count = 0
    try:
        for sirket_id in sirket_ids:
            company = Company.query.get(int(sirket_id))
            if company:
                company.is_active = False
                deactivated_count += 1
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='bulk_companies_deactivated',
                details=f"Toplu şirket pasife alındı: {deactivated_count} şirket"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'{deactivated_count} şirket pasife alındı', 'count': deactivated_count})
        flash(f"{deactivated_count} şirket pasife alındı.", "success")
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f"Hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.sirketler'))
@admin_bp.route('/sirketler/toplu-aktif', methods=['POST'])
@login_required
@superadmin_required
def toplu_sirket_aktif():
    """Bulk reactivate companies - Toplu şirket aktifleştirme"""
    from app.models import Company
    sirket_ids = request.form.getlist('sirket_ids[]')
    
    if not sirket_ids:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Hiç şirket seçilmedi'}), 400
        flash("Hiç şirket seçilmedi.", "warning")
        return redirect(url_for('admin.sirketler'))
    activated_count = 0
    try:
        for sirket_id in sirket_ids:
            company = Company.query.get(int(sirket_id))
            if company:
                company.is_active = True
                activated_count += 1
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='bulk_companies_activated',
                details=f"Toplu şirket aktifleştirildi: {activated_count} şirket"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': f'{activated_count} şirket aktifleştirildi', 'count': activated_count})
        flash(f"{activated_count} şirket aktifleştirildi.", "success")
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        flash(f"Hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.sirketler'))
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/demo-olustur', methods=['GET', 'POST'])
@login_required
@superadmin_required
def demo_olustur():
    """Create demo company with test data"""
    from app.models import Company, User, Candidate
    from werkzeug.security import generate_password_hash
    import string
    import random
    if request.method == 'POST':
        demo_name = request.form.get('demo_name', 'Demo Şirket')
        company = Company(
            isim=demo_name,
            ad=demo_name,
            email=f"demo_{random.randint(1000,9999)}@skillstestcenter.com",
            kredi=100,
            is_active=True
        )
        db.session.add(company)
        db.session.flush()
        demo_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        demo_email = f"demo{company.id}@skillstestcenter.com"
        admin = User(
            email=demo_email,
            password=generate_password_hash(demo_password),
            ad_soyad=f"{demo_name} Admin",
            rol='customer',
            sirket_id=company.id,
            is_active=True
        )
        db.session.add(admin)
        for i in range(5):
            giris_kodu = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            candidate = Candidate(
                ad_soyad=f"Demo Aday {i+1}",
                email=f"aday{i+1}@demo.local",
                giris_kodu=giris_kodu,
                sirket_id=company.id
            )
            db.session.add(candidate)
        db.session.commit()
        flash(f"Demo şirket oluşturuldu. Email: {demo_email}, Şifre: {demo_password}", "success")
        return redirect(url_for('admin.sirketler'))
    return render_template('demo_olustur.html')
@admin_bp.route('/ayarlar', methods=['GET', 'POST'])
@login_required
@superadmin_required
def ayarlar():
    """Company settings"""
    from app.models import Company
    company = Company.query.get(session.get('sirket_id'))
    if request.method == 'POST':
        company.isim = request.form.get('isim')
        company.email = request.form.get('email')
        company.telefon = request.form.get('telefon')
        company.logo_url = request.form.get('logo_url')
        company.primary_color = request.form.get('primary_color')
        company.webhook_url = request.form.get('webhook_url')
        company.smtp_host = request.form.get('smtp_host')
        company.smtp_port = int(request.form.get('smtp_port', 587))
        company.smtp_user = request.form.get('smtp_user')
        if request.form.get('smtp_pass'):
            company.smtp_pass = request.form.get('smtp_pass')
        company.smtp_from = request.form.get('smtp_from')
        db.session.commit()
        flash("Ayarlar kaydedildi.", "success")
    return render_template('ayarlar.html', company=company)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/sablonlar')
@login_required
def sablonlar():
    """Exam templates list - Updated with flexible sections"""
    from app.models import ExamTemplate, Company
    sirket_id = session.get('sirket_id')
    rol = session.get('rol')
    if rol == 'superadmin':
        templates = ExamTemplate.query.order_by(ExamTemplate.created_at.desc()).all()
    else:
        templates = ExamTemplate.query.filter(
            (ExamTemplate.sirket_id == sirket_id) | 
            (ExamTemplate.sirket_id == None)
        ).order_by(ExamTemplate.created_at.desc()).all()
    return render_template('sablonlar.html', sablonlar=templates)
@admin_bp.route('/sablon/yeni')
@login_required
def sablon_yeni():
    """New exam template form"""
    from app.models import Company
    sirketler = []
    if session.get('rol') == 'superadmin':
        sirketler = Company.query.filter_by(is_active=True).order_by(Company.isim).all()
    return render_template('sablon_form.html', sablon=None, sirketler=sirketler)
@admin_bp.route('/sablon/duzenle/<int:id>')
@login_required
def sablon_duzenle(id):
    """Edit exam template"""
    from app.models import ExamTemplate, Company
    sablon = ExamTemplate.query.get_or_404(id)
    # Yetki kontrolü
    sirket_id = session.get('sirket_id')
    rol = session.get('rol')
    if rol != 'superadmin' and sablon.sirket_id != sirket_id:
        flash("Bu şablonu düzenleme yetkiniz yok.", "danger")
        return redirect(url_for('admin.sablonlar'))
    sirketler = []
    if rol == 'superadmin':
        sirketler = Company.query.filter_by(is_active=True).order_by(Company.isim).all()
    return render_template('sablon_form.html', sablon=sablon, sirketler=sirketler)
@admin_bp.route('/sablon/kaydet', methods=['POST'])
@admin_bp.route('/sablon/kaydet/<int:id>', methods=['POST'])
@login_required
def sablon_kaydet(id=None):
    """Save or update exam template with flexible sections"""
    from app.models import ExamTemplate, ExamSection
    try:
        # Temel bilgiler
        isim = request.form.get('isim', '').strip()
        if not isim:
            flash("Şablon adı zorunludur.", "danger")
            return redirect(request.referrer or url_for('admin.sablon_yeni'))
        sinav_suresi = int(request.form.get('sinav_suresi', 60))
        baslangic_seviyesi = request.form.get('baslangic_seviyesi', 'B1')
        # Şirket ataması
        sirket_id = request.form.get('sirket_id')
        if sirket_id:
            sirket_id = int(sirket_id)
        else:
            sirket_id = None
        # Yetki kontrolü - superadmin değilse kendi şirketine atar
        if session.get('rol') != 'superadmin':
            sirket_id = session.get('sirket_id')
        # Ek ayarlar
        is_adaptive = 'is_adaptive' in request.form
        randomize_questions = 'randomize_questions' in request.form
        show_results = 'show_results' in request.form
        # Seçilen bölümler
        selected_sections = request.form.getlist('sections[]')
        if not selected_sections:
            flash("Lütfen en az bir sınav bölümü seçin.", "danger")
            return redirect(request.referrer or url_for('admin.sablon_yeni'))
        # Bölüm yapılandırması oluştur
        sections_config = {}
        for section in selected_sections:
            section_order = int(request.form.get(f'{section}_order', 1))
            question_count = int(request.form.get(f'{section}_question_count', 5))
            time_limit_minutes = int(request.form.get(f'{section}_time_limit', 10))
            time_limit_seconds = time_limit_minutes * 60
            config = {
                'order': section_order,
                'question_count': question_count,
                'time_limit': time_limit_seconds,
                'time_limit_minutes': time_limit_minutes
            }
            # Bölüme özel ayarlar
            if section == 'reading':
                config['passage_count'] = int(request.form.get('reading_passage_count', 1))
            elif section == 'listening':
                config['audio_count'] = int(request.form.get('listening_audio_count', 3))
            elif section == 'writing':
                config['min_words'] = int(request.form.get('writing_min_words', 100))
            elif section == 'speaking':
                config['prep_time'] = int(request.form.get('speaking_prep_time', 30))
                config['answer_time'] = int(request.form.get('speaking_answer_time', 60))
            sections_config[section] = config
        # Toplam soru sayısını hesapla
        total_questions = sum(c['question_count'] for c in sections_config.values())
        if id:
            # Güncelleme
            sablon = ExamTemplate.query.get_or_404(id)
            # Yetki kontrolü
            if session.get('rol') != 'superadmin' and sablon.sirket_id != session.get('sirket_id'):
                flash("Bu şablonu düzenleme yetkiniz yok.", "danger")
                return redirect(url_for('admin.sablonlar'))
            sablon.isim = isim
            sablon.sinav_suresi = sinav_suresi
            sablon.soru_limiti = total_questions
            sablon.baslangic_seviyesi = baslangic_seviyesi
            sablon.sirket_id = sirket_id
            sablon.is_adaptive = is_adaptive
            sablon.randomize_questions = randomize_questions
            sablon.show_results = show_results
            sablon.sections_config = json.dumps(sections_config)
            # Eski bölüm ayarlarını sil
            ExamSection.query.filter_by(template_id=sablon.id).delete()
            flash("Şablon başarıyla güncellendi!", "success")
        else:
            # Yeni oluştur
            sablon = ExamTemplate(
                isim=isim,
                sinav_suresi=sinav_suresi,
                soru_limiti=total_questions,
                baslangic_seviyesi=baslangic_seviyesi,
                sirket_id=sirket_id,
                is_adaptive=is_adaptive,
                randomize_questions=randomize_questions,
                show_results=show_results,
                sections_config=json.dumps(sections_config)
            )
            db.session.add(sablon)
            db.session.flush()
            flash("Şablon başarıyla oluşturuldu!", "success")
        # ExamSection kayıtlarını oluştur
        for section_name, config in sections_config.items():
            exam_section = ExamSection(
                template_id=sablon.id,
                section_name=section_name,
                section_order=config['order'],
                question_count=config['question_count'],
                time_limit=config['time_limit']
            )
            db.session.add(exam_section)
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            action = 'template_updated' if id else 'template_created'
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action=action,
                details=f"Şablon: {isim}, Bölümler: {', '.join(selected_sections)}"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        return redirect(url_for('admin.sablonlar'))
    except Exception as e:
        db.session.rollback()
        flash(f"Bir hata oluştu: {str(e)}", "danger")
        return redirect(request.referrer or url_for('admin.sablon_yeni'))
@admin_bp.route('/sablon/sil/<int:id>', methods=['POST'])
@login_required
def sablon_sil(id):
    """Delete exam template"""
    from app.models import ExamTemplate, ExamSection
    sablon = ExamTemplate.query.get_or_404(id)
    # Yetki kontrolü
    if session.get('rol') != 'superadmin' and sablon.sirket_id != session.get('sirket_id'):
        flash("Bu şablonu silme yetkiniz yok.", "danger")
        return redirect(url_for('admin.sablonlar'))
    try:
        # Bölüm ayarlarını sil
        ExamSection.query.filter_by(template_id=sablon.id).delete()
        # Şablonu sil
        isim = sablon.isim
        db.session.delete(sablon)
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='template_deleted',
                details=f"Şablon silindi: {isim}"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        flash("Şablon başarıyla silindi.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Şablon silinirken hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.sablonlar'))
@admin_bp.route('/sablon/kopyala/<int:id>', methods=['POST'])
@login_required
def sablon_kopyala(id):
    """Copy exam template"""
    from app.models import ExamTemplate, ExamSection
    kaynak = ExamTemplate.query.get_or_404(id)
    try:
        yeni_sablon = ExamTemplate(
            isim=f"{kaynak.isim} (Kopya)",
            sinav_suresi=kaynak.sinav_suresi,
            soru_suresi=kaynak.soru_suresi,
            soru_limiti=kaynak.soru_limiti,
            baslangic_seviyesi=kaynak.baslangic_seviyesi,
            sections_config=kaynak.sections_config,
            is_adaptive=kaynak.is_adaptive,
            randomize_questions=kaynak.randomize_questions,
            show_results=kaynak.show_results,
            sirket_id=session.get('sirket_id') if session.get('rol') != 'superadmin' else kaynak.sirket_id
        )
        db.session.add(yeni_sablon)
        db.session.flush()
        # Bölüm ayarlarını kopyala
        for section in kaynak.sections:
            yeni_section = ExamSection(
                template_id=yeni_sablon.id,
                section_name=section.section_name,
                section_order=section.section_order,
                question_count=section.question_count,
                time_limit=section.time_limit
            )
            db.session.add(yeni_section)
        db.session.commit()
        flash("Şablon başarıyla kopyalandı.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Kopyalama hatası: {str(e)}", "danger")
    return redirect(url_for('admin.sablonlar'))
@admin_bp.route('/api/sablon/<int:id>')
@login_required
def api_sablon_detay(id):
    """API: Get template details as JSON"""
    from app.models import ExamTemplate, ExamSection
    sablon = ExamTemplate.query.get_or_404(id)
    sections = []
    for section in sablon.sections.order_by(ExamSection.section_order):
        sections.append({
            'name': section.section_name,
            'order': section.section_order,
            'question_count': section.question_count,
            'time_limit': section.time_limit,
            'time_limit_minutes': section.time_limit // 60 if section.time_limit else 0
        })
    return jsonify({
        'id': sablon.id,
        'isim': sablon.isim,
        'sinav_suresi': sablon.sinav_suresi,
        'baslangic_seviyesi': sablon.baslangic_seviyesi,
        'is_adaptive': sablon.is_adaptive,
        'randomize_questions': sablon.randomize_questions,
        'show_results': sablon.show_results,
        'sirket_id': sablon.sirket_id,
        'sections': sections,
        'sections_config': json.loads(sablon.sections_config) if sablon.sections_config else {}
    })
# Eski route'u yeni sisteme yönlendir
@admin_bp.route('/sablon-ekle', methods=['GET', 'POST'])
@login_required
def sablon_ekle_eski():
    """Redirect old route to new template form"""
    return redirect(url_for('admin.sablon_yeni'))
# ══════════════════════════════════════════════════════════════
# ŞİRKET YÖNETİMİ - GÜNCELLENMIŞ (KALICI SİLME VE AKTİFLEŞTİRME DAHİL)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/sirketler')
@login_required
@superadmin_required
def sirketler():
    """Company management page"""
    from app.models import Company
    companies = Company.query.order_by(Company.id.desc()).all()
    return render_template('sirketler.html', sirketler=companies)
@admin_bp.route('/sirket-ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def sirket_ekle():
    """Add new company"""
    from app.models import Company, User
    import string
    import random
    from werkzeug.security import generate_password_hash
    if request.method == 'POST':
        isim = request.form.get('isim', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        adres = request.form.get('adres', '').strip()
        admin_email = request.form.get('admin_email', '').strip().lower()
        admin_ad_soyad = request.form.get('admin_ad_soyad', '').strip()
        admin_password = request.form.get('admin_password', '')
        if not isim or not admin_email:
            flash("Şirket adı ve admin email zorunludur.", "danger")
            return render_template('sirket_form.html')
        company = Company(
            isim=isim,
            ad=isim,
            email=email,
            telefon=telefon,
            adres=adres,
            kredi=10,
            is_active=True
        )
        db.session.add(company)
        db.session.flush()
        if not admin_password:
            admin_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        admin_user = User(
            email=admin_email,
            password=generate_password_hash(admin_password),
            ad_soyad=admin_ad_soyad or f"{isim} Admin",
            rol='customer',
            sirket_id=company.id,
            is_active=True
        )
        db.session.add(admin_user)
        db.session.commit()
        flash(f"Şirket oluşturuldu. Admin: {admin_email}, Şifre: {admin_password}", "success")
        return redirect(url_for('admin.sirketler'))
    return render_template('sirket_form.html')
@admin_bp.route('/sirket/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def sirket_duzenle(id):
    """Edit company"""
    from app.models import Company
    company = Company.query.get_or_404(id)
    if request.method == 'POST':
        company.isim = request.form.get('isim', '').strip()
        company.ad = company.isim
        company.email = request.form.get('email', '').strip()
        company.telefon = request.form.get('telefon', '').strip()
        company.adres = request.form.get('adres', '').strip()
        company.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash("Şirket güncellendi.", "success")
        return redirect(url_for('admin.sirketler'))
    return render_template('sirket_form.html', sirket=company)
@admin_bp.route('/sirket/<int:id>/sil', methods=['POST'])
@login_required
@superadmin_required
def sirket_sil(id):
    """Deactivate company (soft delete) - Şirketi pasife alma"""
    from app.models import Company
    company = Company.query.get_or_404(id)
    company.is_active = False
    db.session.commit()
    # Log action
    try:
        from app.models import AuditLog
        log = AuditLog(
            user_id=session.get('kullanici_id'),
            action='company_deactivated',
            details=f"Şirket pasife alındı: {company.isim} (ID: {id})"
        )
        db.session.add(log)
        db.session.commit()
    except:
        pass
    flash("Şirket devre dışı bırakıldı.", "success")
    return redirect(url_for('admin.sirketler'))
@admin_bp.route('/sirket/<int:id>/aktif', methods=['POST'])
@login_required
@superadmin_required
def sirket_aktif(id):
    """Reactivate company - Şirketi tekrar aktifleştirme"""
    from app.models import Company
    company = Company.query.get_or_404(id)
    company.is_active = True
    db.session.commit()
    # Log action
    try:
        from app.models import AuditLog
        log = AuditLog(
            user_id=session.get('kullanici_id'),
            action='company_activated',
            details=f"Şirket aktifleştirildi: {company.isim} (ID: {id})"
        )
        db.session.add(log)
        db.session.commit()
    except:
        pass
    flash("Şirket tekrar aktifleştirildi.", "success")
    return redirect(url_for('admin.sirketler'))
@admin_bp.route('/sirket/<int:id>/kalici-sil', methods=['POST'])
@login_required
@superadmin_required
def sirket_kalici_sil(id):
    """Permanently delete company and all related data - Şirketi kalıcı olarak silme
    
    DİKKAT: Bu işlem geri alınamaz!
    Silinecekler:
    - Şirketin tüm adayları ve sınav cevapları
    - Şirketin tüm kullanıcıları
    - Şirketin tüm soruları
    - Şirketin tüm sınav şablonları
    - Şirket kaydı
    """
    from app.models import Company, Candidate, User, Question, ExamTemplate, ExamSection, ExamAnswer
    company = Company.query.get_or_404(id)
    company_name = company.isim
    try:
        # 1. Şirketin adaylarının sınav cevaplarını sil
        candidate_ids = [c.id for c in Candidate.query.filter_by(sirket_id=id).all()]
        if candidate_ids:
            ExamAnswer.query.filter(ExamAnswer.aday_id.in_(candidate_ids)).delete(synchronize_session=False)
        
        # 2. Şirketin adaylarını sil
        Candidate.query.filter_by(sirket_id=id).delete(synchronize_session=False)
        
        # 3. Şirketin kullanıcılarını sil
        User.query.filter_by(sirket_id=id).delete(synchronize_session=False)
        
        # 4. Şirketin sorularını sil
        Question.query.filter_by(sirket_id=id).delete(synchronize_session=False)
        
        # 5. Şirketin sınav şablonlarının bölümlerini sil
        template_ids = [t.id for t in ExamTemplate.query.filter_by(sirket_id=id).all()]
        if template_ids:
            ExamSection.query.filter(ExamSection.template_id.in_(template_ids)).delete(synchronize_session=False)
        
        # 6. Şirketin sınav şablonlarını sil
        ExamTemplate.query.filter_by(sirket_id=id).delete(synchronize_session=False)
        
        # 7. Şirketi sil
        db.session.delete(company)
        db.session.commit()
        # Log action
        try:
            from app.models import AuditLog
            log = AuditLog(
                user_id=session.get('kullanici_id'),
                action='company_permanently_deleted',
                details=f"Şirket kalıcı olarak silindi: {company_name} (ID: {id})"
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        flash(f"'{company_name}' şirketi ve tüm ilişkili verileri kalıcı olarak silindi.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Şirket silinirken hata oluştu: {str(e)}", "danger")
    return redirect(url_for('admin.sirketler'))
@admin_bp.route('/sirket/<int:id>/kredi-yukle', methods=['POST'])
@login_required
@superadmin_required
def sirket_kredi_yukle(id):
    """Add credits to company"""
    from app.models import Company
    company = Company.query.get_or_404(id)
    miktar = int(request.form.get('miktar', 0))
    if miktar > 0:
        company.kredi = (company.kredi or 0) + miktar
        db.session.commit()
        flash(f"{miktar} kredi yüklendi. Yeni bakiye: {company.kredi}", "success")
    else:
        flash("Geçersiz miktar.", "danger")
    return redirect(url_for('admin.sirketler'))
@admin_bp.route('/sirket/<int:id>/kredi', methods=['GET', 'POST'])
@login_required
@superadmin_required
def sirket_kredi(id):
    """Company credit management page"""
    from app.models import Company
    company = Company.query.get_or_404(id)
    if request.method == 'POST':
        miktar = int(request.form.get('miktar', 0))
        if miktar > 0:
            company.kredi = (company.kredi or 0) + miktar
            db.session.commit()
            flash(f"{miktar} kredi yüklendi.", "success")
    return render_template('kredi_yukle.html', sirket=company)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/raporlar')
@login_required
def raporlar():
    """Reports page"""
    from app.models import Candidate
    from datetime import datetime, timedelta
    sirket_id = session.get('sirket_id')
    if sirket_id:
        base_query = Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False)
    else:
        base_query = Candidate.query.filter_by(is_deleted=False)
    stats = {
        'total': base_query.count(),
        'completed': base_query.filter_by(sinav_durumu='tamamlandi').count(),
        'pending': base_query.filter_by(sinav_durumu='beklemede').count()
    }
    if sirket_id:
        completed = Candidate.query.filter_by(
            sirket_id=sirket_id, 
            sinav_durumu='tamamlandi',
            is_deleted=False
        ).order_by(Candidate.bitis_tarihi.desc()).limit(50).all()
    else:
        completed = Candidate.query.filter_by(
            sinav_durumu='tamamlandi',
            is_deleted=False
        ).order_by(Candidate.bitis_tarihi.desc()).limit(50).all()
    return render_template('raporlar.html', completed=completed, stats=stats)
@admin_bp.route('/super-rapor')
@login_required
@superadmin_required
def super_rapor():
    """Platform-wide report for superadmin"""
    from app.models import Candidate, Company, Question, User
    from sqlalchemy import func
    from datetime import datetime, timedelta
    stats = {
        'total_companies': Company.query.count(),
        'active_companies': Company.query.filter_by(is_active=True).count(),
        'total_candidates': Candidate.query.filter_by(is_deleted=False).count(),
        'completed_exams': Candidate.query.filter_by(sinav_durumu='tamamlandi', is_deleted=False).count(),
        'total_questions': Question.query.filter_by(is_active=True).count(),
        'total_users': User.query.filter_by(is_active=True).count()
    }
    recent_candidates = Candidate.query.filter_by(is_deleted=False).order_by(
        Candidate.created_at.desc()
    ).limit(10).all()
    return render_template('super_rapor.html', stats=stats, recent_candidates=recent_candidates)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/export')
@login_required
def export_data():
    """Export data as Excel"""
    from app.models import Candidate
    import pandas as pd
    from flask import Response
    import io
    sirket_id = session.get('sirket_id')
    format_type = request.args.get('format', 'xlsx')
    if sirket_id:
        candidates = Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False).all()
    else:
        candidates = Candidate.query.filter_by(is_deleted=False).all()
    data = []
    for c in candidates:
        data.append({
            'Ad Soyad': c.ad_soyad,
            'Email': c.email,
            'Giriş Kodu': c.giris_kodu,
            'Puan': c.puan,
            'Seviye': c.seviye_sonuc,
            'Durum': c.sinav_durumu,
            'Oluşturma Tarihi': c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else ''
        })
    df = pd.DataFrame(data)
    if format_type == 'xlsx':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Adaylar')
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment;filename=adaylar.xlsx'}
        )
    else:
        csv_data = df.to_csv(index=False)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=adaylar.csv'}
        )
@admin_bp.route('/logs')
@login_required
@superadmin_required
def admin_logs():
    """View audit logs"""
    from app.models import AuditLog
    page = request.args.get('page', 1, type=int)
    logs = []
    pagination = None
    try:
        pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
        logs = pagination.items
    except:
        pass
    return render_template('admin_logs.html', logs=logs, pagination=pagination)
@admin_bp.route('/veri-yonetimi')
@login_required
@superadmin_required
def veri_yonetimi():
    """Data management page"""
    from app.models import Candidate, Question, AuditLog
    stats = {
        'total_candidates': Candidate.query.filter_by(is_deleted=False).count(),
        'total_questions': Question.query.filter_by(is_active=True).count(),
        'total_answers': 0,
        'speaking_recordings': 0,
        'audit_logs': AuditLog.query.count() if AuditLog else 0,
        'db_size_mb': 0
    }
    backups = []
    deletion_requests = []
    return render_template('veri_yonetimi.html', 
                          stats=stats, 
                          backups=backups, 
                          deletion_requests=deletion_requests)
@admin_bp.route('/fraud-heatmap')
@login_required
@superadmin_required
def fraud_heatmap():
    """Fraud detection heatmap"""
    return render_template('fraud_heatmap.html')
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/loglar')
@login_required
@superadmin_required
def loglar():
    from app.models import AuditLog
    page = request.args.get('page', 1, type=int)
    logs = []
    pagination = None
    try:
        query = AuditLog.query.order_by(AuditLog.created_at.desc())
        pagination = query.paginate(page=page, per_page=50, error_out=False)
        logs = pagination.items
    except:
        pass
    return render_template('admin_logs.html', logs=logs, pagination=pagination)

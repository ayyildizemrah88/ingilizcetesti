# -*- coding: utf-8 -*-
"""
Admin Routes - Complete Superadmin Features
Company management, demo accounts, credits, questions, templates, reports

All model imports are at the top level for better performance and code clarity.
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from app.extensions import db
from datetime import datetime, timedelta
import io
import csv
import json
import string
import random

# ══════════════════════════════════════════════════════════════
# MODEL IMPORTS - All imports at module level (best practice)
# ══════════════════════════════════════════════════════════════
from app.models import Candidate, Question, Company, User, ExamTemplate, ExamAnswer
from app.models.admin import CreditTransaction
from app.models.audit_log import AuditLog


admin_bp = Blueprint('admin', __name__)

# ══════════════════════════════════════════════════════════════
# DECORATORS
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
    """Only superadmin can access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu işlem sadece süper admin tarafından yapılabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated

def customer_or_superadmin(f):
    """Superadmin and customer can access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') not in ['superadmin', 'customer']:
            flash("Bu işlem için yetkiniz yok.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard with statistics"""
    sirket_id = session.get('sirket_id')
    is_superadmin = session.get('rol') == 'superadmin'
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    stats = {
        'total_candidates': 0,
        'completed_exams': 0,
        'pending_exams': 0,
        'total_questions': 0,
        'exams_this_week': 0,
        'total_companies': 0,
        'total_users': 0
    }
    
    try:
        if is_superadmin:
            stats['total_candidates'] = Candidate.query.filter_by(is_deleted=False).count()
            stats['completed_exams'] = Candidate.query.filter_by(sinav_durumu='tamamlandi').count()
            stats['pending_exams'] = Candidate.query.filter_by(sinav_durumu='beklemede').count()
            stats['total_questions'] = Question.query.filter_by(is_active=True).count()
            stats['total_companies'] = Company.query.count()
            stats['total_users'] = User.query.count()
        elif sirket_id:
            stats['total_candidates'] = Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False).count()
            stats['completed_exams'] = Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='tamamlandi').count()
            stats['pending_exams'] = Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='beklemede').count()
            stats['total_questions'] = Question.query.filter_by(is_active=True).count()
    except Exception as e:
        print(f"Stats error: {e}")
    
    recent_candidates = []
    try:
        if is_superadmin:
            recent_candidates = Candidate.query.filter_by(is_deleted=False).order_by(
                Candidate.created_at.desc()
            ).limit(10).all()
        elif sirket_id:
            recent_candidates = Candidate.query.filter_by(
                sirket_id=sirket_id, is_deleted=False
            ).order_by(Candidate.created_at.desc()).limit(10).all()
    except:
        pass
    
    company = None
    try:
        if sirket_id:
            company = Company.query.get(sirket_id)
    except:
        pass
    
    return render_template('dashboard.html', 
                          stats=stats, 
                          recent_candidates=recent_candidates,
                          company=company,
                          is_superadmin=is_superadmin)

# ══════════════════════════════════════════════════════════════
# CANDIDATE MANAGEMENT
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/adaylar')
@login_required
def adaylar():
    """List all candidates"""
    sirket_id = session.get('sirket_id')
    is_superadmin = session.get('rol') == 'superadmin'
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if is_superadmin:
        candidates = Candidate.query.filter_by(is_deleted=False).order_by(
            Candidate.created_at.desc()
        ).paginate(page=page, per_page=per_page)
    elif sirket_id:
        candidates = Candidate.query.filter_by(
            sirket_id=sirket_id, is_deleted=False
        ).order_by(Candidate.created_at.desc()).paginate(page=page, per_page=per_page)
    else:
        candidates = []
    
    return render_template('adaylar.html', adaylar=candidates)

@admin_bp.route('/aday/ekle', methods=['GET', 'POST'])
@login_required
def aday_ekle():
    """Add new candidate"""
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        email = request.form.get('email', '').strip().lower()
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        cep_no = request.form.get('cep_no', '').strip()
        sinav_suresi = int(request.form.get('sinav_suresi', 30))
        soru_limiti = int(request.form.get('soru_limiti', 25))
        giris_kodu = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        candidate = Candidate(
            ad_soyad=ad_soyad,
            email=email,
            tc_kimlik=tc_kimlik,
            cep_no=cep_no,
            giris_kodu=giris_kodu,
            sinav_suresi=sinav_suresi,
            soru_limiti=soru_limiti,
            sirket_id=session.get('sirket_id')
        )
        db.session.add(candidate)
        db.session.commit()
        flash(f"Aday eklendi. Giriş Kodu: {giris_kodu}", "success")
        return redirect(url_for('admin.adaylar'))
    
    return render_template('aday_form.html')

@admin_bp.route('/aday/<int:id>/detay')
@login_required
def aday_detay(id):
    """Candidate detail view"""
    candidate = Candidate.query.get_or_404(id)
    
    if candidate.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu adaya erişim yetkiniz yok.", "danger")
        return redirect(url_for('admin.adaylar'))
    
    return render_template('aday_detay.html', aday=candidate)

@admin_bp.route('/aday/<int:id>/sil', methods=['POST'])
@login_required
def aday_sil(id):
    """Delete candidate (soft delete)"""
    candidate = Candidate.query.get_or_404(id)

    if candidate.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu adayı silme yetkiniz yok.", "danger")
        return redirect(url_for('admin.adaylar'))
    
    candidate.is_deleted = True
    db.session.commit()
    flash("Aday silindi.", "success")
    return redirect(url_for('admin.adaylar'))

@admin_bp.route('/aday/<int:id>/sifirla', methods=['POST'])
@login_required
def aday_sifirla(id):
    """Reset candidate exam"""
    candidate = Candidate.query.get_or_404(id)

    if candidate.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu işlem için yetkiniz yok.", "danger")
        return redirect(url_for('admin.adaylar'))
    
    # Reset exam data
    candidate.baslama_tarihi = None
    candidate.bitis_tarihi = None
    candidate.sinav_durumu = 'beklemede'
    candidate.toplam_puan = None
    candidate.cefr_seviye = None

    # Delete answers
    ExamAnswer.query.filter_by(aday_id=id).delete()

    # Generate new code
    candidate.giris_kodu = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    db.session.commit()
    flash(f"Aday sıfırlandı. Yeni Giriş Kodu: {candidate.giris_kodu}", "success")
    return redirect(url_for('admin.aday_detay', id=id))

# ══════════════════════════════════════════════════════════════
# QUESTION MANAGEMENT
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/sorular')
@login_required
@superadmin_required
def sorular():
    """Question bank management"""
    kategori = request.args.get('kategori')
    zorluk = request.args.get('zorluk')
    page = request.args.get('page', 1, type=int)
    
    query = Question.query.filter_by(is_active=True)
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

@admin_bp.route('/soru/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def soru_duzenle(id):
    """Edit question"""
    question = Question.query.get_or_404(id)
    
    if request.method == 'POST':
        question.soru_metni = request.form.get('soru_metni')
        question.secenek_a = request.form.get('secenek_a')
        question.secenek_b = request.form.get('secenek_b')
        question.secenek_c = request.form.get('secenek_c')
        question.secenek_d = request.form.get('secenek_d')
        question.dogru_cevap = request.form.get('dogru_cevap')
        question.kategori = request.form.get('kategori')
        question.zorluk = request.form.get('zorluk', 'B1')

        db.session.commit()
        flash("Soru güncellendi.", "success")
        return redirect(url_for('admin.sorular'))
    
    return render_template('soru_form.html', soru=question)

@admin_bp.route('/soru/<int:id>/sil', methods=['POST'])
@login_required
@superadmin_required
def soru_sil(id):
    """Delete question (soft delete)"""
    question = Question.query.get_or_404(id)
    question.is_active = False
    db.session.commit()
    flash("Soru silindi.", "success")
    return redirect(url_for('admin.sorular'))

# ══════════════════════════════════════════════════════════════
# TEMPLATE MANAGEMENT
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/sablonlar')
@login_required
def sablonlar():
    """Exam templates list"""
    sirket_id = session.get('sirket_id')
    is_superadmin = session.get('rol') == 'superadmin'
    
    try:
        if is_superadmin:
            templates = ExamTemplate.query.all()
        elif sirket_id:
            templates = ExamTemplate.query.filter_by(sirket_id=sirket_id).all()
        else:
            templates = []
    except:
        templates = []
    
    return render_template('sablonlar.html', sablonlar=templates)

@admin_bp.route('/sablon/ekle', methods=['GET', 'POST'])
@login_required
def sablon_ekle():
    """Add exam template"""
    if request.method == 'POST':
        template = ExamTemplate(
            isim=request.form.get('isim'),
            aciklama=request.form.get('aciklama', ''),
            sinav_suresi=int(request.form.get('sinav_suresi', 30)),
            soru_sayisi=int(request.form.get('soru_sayisi', 25)),
            sirket_id=session.get('sirket_id'),
            aktif=True
        )
        db.session.add(template)
        db.session.commit()
        flash("Şablon eklendi.", "success")
        return redirect(url_for('admin.sablonlar'))
    
    return render_template('sablon_form.html')

@admin_bp.route('/sablon/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
def sablon_duzenle(id):
    """Edit exam template"""
    template = ExamTemplate.query.get_or_404(id)
    
    if request.method == 'POST':
        template.isim = request.form.get('isim')
        template.aciklama = request.form.get('aciklama', '')
        template.sinav_suresi = int(request.form.get('sinav_suresi', 30))
        template.soru_sayisi = int(request.form.get('soru_sayisi', 25))

        db.session.commit()
        flash("Şablon güncellendi.", "success")
        return redirect(url_for('admin.sablonlar'))
    
    return render_template('sablon_form.html', sablon=template)

@admin_bp.route('/sablon/<int:id>/sil', methods=['POST'])
@login_required
def sablon_sil(id):
    """Delete exam template"""
    template = ExamTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    flash("Şablon silindi.", "success")
    return redirect(url_for('admin.sablonlar'))

# ══════════════════════════════════════════════════════════════
# COMPANY MANAGEMENT
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/sirketler')
@login_required
@superadmin_required
def sirketler():
    """Company management"""
    companies = Company.query.order_by(Company.created_at.desc()).all()
    return render_template('sirketler.html', sirketler=companies)

@admin_bp.route('/sirket/ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def sirket_ekle():
    """Add new company"""
    if request.method == 'POST':
        company = Company(
            isim=request.form.get('isim'),
            email=request.form.get('email'),
            telefon=request.form.get('telefon'),
            adres=request.form.get('adres', ''),
            kredi=int(request.form.get('kredi', 0)),
            aktif=True
        )
        db.session.add(company)
        db.session.commit()
        flash("Şirket eklendi.", "success")
        return redirect(url_for('admin.sirketler'))
    
    return render_template('sirket_form.html')

@admin_bp.route('/sirket/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def sirket_duzenle(id):
    """Edit company"""
    company = Company.query.get_or_404(id)
    
    if request.method == 'POST':
        company.isim = request.form.get('isim')
        company.email = request.form.get('email')
        company.telefon = request.form.get('telefon')
        company.adres = request.form.get('adres', '')

        db.session.commit()
        flash("Şirket güncellendi.", "success")
        return redirect(url_for('admin.sirketler'))
    
    return render_template('sirket_form.html', sirket=company)

@admin_bp.route('/sirket/<int:id>/pasif', methods=['POST'])
@login_required
@superadmin_required
def sirket_pasif(id):
    """Deactivate company"""
    company = Company.query.get_or_404(id)
    company.aktif = False
    db.session.commit()
    flash("Şirket pasife alındı.", "warning")
    return redirect(url_for('admin.sirketler'))

@admin_bp.route('/sirket/<int:id>/aktif', methods=['POST'])
@login_required
@superadmin_required
def sirket_aktif(id):
    """Activate company"""
    company = Company.query.get_or_404(id)
    company.aktif = True
    db.session.commit()
    flash("Şirket aktif edildi.", "success")
    return redirect(url_for('admin.sirketler'))

@admin_bp.route('/sirket/<int:id>/sil', methods=['POST'])
@login_required
@superadmin_required
def sirket_sil(id):
    """Delete company"""
    company = Company.query.get_or_404(id)
    db.session.delete(company)
    db.session.commit()
    flash("Şirket silindi.", "danger")
    return redirect(url_for('admin.sirketler'))

@admin_bp.route('/sirket/<int:id>/kredi', methods=['GET', 'POST'])
@login_required
@superadmin_required
def sirket_kredi(id):
    """Add credits to company"""
    company = Company.query.get_or_404(id)
    
    if request.method == 'POST':
        miktar = int(request.form.get('miktar', 0))
        aciklama = request.form.get('aciklama', 'Manuel kredi yükleme')
        
        if miktar > 0:
            company.kredi = (company.kredi or 0) + miktar

            # Log transaction
            try:
                transaction = CreditTransaction(
                    company_id=company.id,
                    amount=miktar,
                    transaction_type='manual',
                    description=aciklama,
                    created_by=session.get('kullanici_id')
                )
                db.session.add(transaction)
            except:
                pass

            db.session.commit()
            flash(f"{miktar} kredi eklendi. Toplam: {company.kredi}", "success")
        else:
            flash("Geçersiz miktar.", "danger")
        return redirect(url_for('admin.sirketler'))
    
    return render_template('kredi_yukle.html', sirket=company)

# ══════════════════════════════════════════════════════════════
# DEMO ACCOUNT CREATION
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/demo/olustur', methods=['GET', 'POST'])
@login_required
@superadmin_required
def demo_olustur():
    """Create demo company with user and sample data"""
    if request.method == 'POST':
        firma_adi = request.form.get('firma_adi', 'Demo Şirket')
        admin_email = request.form.get('admin_email', '').strip().lower()
        admin_sifre = request.form.get('admin_sifre', 'Demo123!')
        kredi = int(request.form.get('kredi', 10))
        
        # Create company
        company = Company(
            isim=firma_adi,
            email=admin_email,
            kredi=kredi,
            aktif=True
        )
        db.session.add(company)
        db.session.flush()
        
        # Create admin user
        user = User(
            email=admin_email,
            ad_soyad=f"{firma_adi} Admin",
            rol='customer',
            sirket_id=company.id,
            is_active=True
        )
        user.set_password(admin_sifre)
        db.session.add(user)
        db.session.commit()
        
        flash(f"Demo hesap oluşturuldu! Email: {admin_email}, Şifre: {admin_sifre}", "success")
        return redirect(url_for('admin.sirketler'))
    
    return render_template('demo_olustur.html')

# ══════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/kullanicilar')
@login_required
@superadmin_required
def kullanicilar():
    """User management"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('kullanicilar.html', kullanicilar=users)

@admin_bp.route('/kullanici/ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def kullanici_ekle():
    """Add new user"""
    if request.method == 'POST':
        user = User(
            email=request.form.get('email', '').strip().lower(),
            ad_soyad=request.form.get('ad_soyad', '').strip(),
            rol=request.form.get('rol', 'customer'),
            sirket_id=request.form.get('sirket_id', type=int),
            is_active=True
        )
        user.set_password(request.form.get('sifre', 'Temp123!'))

        db.session.add(user)
        db.session.commit()
        flash("Kullanıcı eklendi.", "success")
        return redirect(url_for('admin.kullanicilar'))
    
    companies = Company.query.filter_by(aktif=True).all()
    return render_template('kullanici_form.html', sirketler=companies)

@admin_bp.route('/kullanici/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def kullanici_duzenle(id):
    """Edit user"""
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        user.email = request.form.get('email', '').strip().lower()
        user.ad_soyad = request.form.get('ad_soyad', '').strip()
        user.rol = request.form.get('rol', 'customer')
        user.sirket_id = request.form.get('sirket_id', type=int)

        new_password = request.form.get('sifre', '')
        if new_password:
            user.set_password(new_password)

        db.session.commit()
        flash("Kullanıcı güncellendi.", "success")
        return redirect(url_for('admin.kullanicilar'))
    
    companies = Company.query.filter_by(aktif=True).all()
    return render_template('kullanici_form.html', kullanici=user, sirketler=companies)

@admin_bp.route('/kullanici/<int:id>/sil', methods=['POST'])
@login_required
@superadmin_required
def kullanici_sil(id):
    """Delete user"""
    user = User.query.get_or_404(id)
    user.is_active = False
    db.session.commit()
    flash("Kullanıcı silindi.", "warning")
    return redirect(url_for('admin.kullanicilar'))

# ══════════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/raporlar')
@login_required
def raporlar():
    """Reports page"""
    sirket_id = session.get('sirket_id')
    is_superadmin = session.get('rol') == 'superadmin'
    
    stats = {
        'total': 0,
        'completed': 0,
        'pending': 0,
        'in_progress': 0,
        'average_score': 0,
        'pass_rate': 0
    }
    
    try:
        if is_superadmin:
            candidates = Candidate.query.filter_by(is_deleted=False)
        elif sirket_id:
            candidates = Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False)
        else:
            candidates = Candidate.query.filter_by(id=-1)  # Empty
        
        stats['total'] = candidates.count()
        stats['completed'] = candidates.filter_by(sinav_durumu='tamamlandi').count()
        stats['pending'] = candidates.filter_by(sinav_durumu='beklemede').count()
        stats['in_progress'] = candidates.filter_by(sinav_durumu='devam_ediyor').count()
        
        completed_list = candidates.filter_by(sinav_durumu='tamamlandi').all()
        if completed_list:
            scores = [c.toplam_puan or 0 for c in completed_list]
            stats['average_score'] = round(sum(scores) / len(scores), 1)
            passed = len([s for s in scores if s >= 60])
            stats['pass_rate'] = round((passed / len(scores)) * 100, 1)
    except:
        pass
    
    return render_template('raporlar.html', stats=stats)

@admin_bp.route('/super-rapor')
@login_required
@superadmin_required
def super_rapor():
    """Platform-wide report for superadmin"""
    stats = {
        'total_companies': Company.query.count(),
        'active_companies': Company.query.filter_by(aktif=True).count(),
        'total_users': User.query.count(),
        'total_candidates': Candidate.query.count(),
        'completed_exams': Candidate.query.filter_by(sinav_durumu='tamamlandi').count(),
        'total_credits_used': 0
    }
    
    companies = Company.query.order_by(Company.created_at.desc()).all()
    return render_template('super_rapor.html', stats=stats, companies=companies)

# ══════════════════════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/ayarlar', methods=['GET', 'POST'])
@login_required
def ayarlar():
    """Company settings"""
    company = Company.query.get(session.get('sirket_id'))
    
    if request.method == 'POST' and company:
        company.isim = request.form.get('isim')
        company.email = request.form.get('email')
        company.telefon = request.form.get('telefon')
        company.logo_url = request.form.get('logo_url')
        company.primary_color = request.form.get('primary_color')
        company.webhook_url = request.form.get('webhook_url')
        company.smtp_host = request.form.get('smtp_host')
        company.smtp_port = int(request.form.get('smtp_port', 587) or 587)
        company.smtp_user = request.form.get('smtp_user')
        if request.form.get('smtp_pass'):
            company.smtp_pass = request.form.get('smtp_pass')
        company.smtp_from = request.form.get('smtp_from')
        db.session.commit()
        flash("Ayarlar kaydedildi.", "success")
    
    return render_template('ayarlar.html', company=company)

# ══════════════════════════════════════════════════════════════
# EXPORT & LOGS
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/export')
@login_required
def export_data():
    """Export candidates data as CSV"""
    sirket_id = session.get('sirket_id')
    is_superadmin = session.get('rol') == 'superadmin'

    if is_superadmin:
        candidates = Candidate.query.filter_by(is_deleted=False).all()
    elif sirket_id:
        candidates = Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False).all()
    else:
        candidates = []
    
    output = io.StringIO()
    output.write("Ad Soyad,Email,TC Kimlik,Giriş Kodu,Durum,Puan,CEFR,Başlangıç,Bitiş\n")

    for c in candidates:
        baslama = c.baslama_tarihi.strftime('%Y-%m-%d %H:%M') if c.baslama_tarihi else ''
        bitis = c.bitis_tarihi.strftime('%Y-%m-%d %H:%M') if c.bitis_tarihi else ''
        output.write(f"{c.ad_soyad},{c.email},{c.tc_kimlik},{c.giris_kodu},{c.sinav_durumu},{c.toplam_puan or 0},{c.cefr_seviye or ''},{baslama},{bitis}\n")
    
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='adaylar.csv'
    )

@admin_bp.route('/logs')
@login_required
@superadmin_required
def admin_logs():
    """Admin activity logs"""
    page = request.args.get('page', 1, type=int)

    try:
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50)
    except:
        logs = None
    
    return render_template('admin_logs.html', logs=logs)

@admin_bp.route('/fraud-heatmap')
@login_required
@superadmin_required
def fraud_heatmap():
    """Fraud detection heatmap"""
    return render_template('fraud_heatmap.html')

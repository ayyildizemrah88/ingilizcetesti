# -*- coding: utf-8 -*-
"""
Admin Routes - Dashboard and management
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from app.extensions import db
import io

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


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard with statistics"""
    from app.models import Candidate, Question, Company, User
    from datetime import datetime, timedelta

    sirket_id = session.get('sirket_id')

    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)

    stats = {
        'total_candidates': Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False).count() if sirket_id else 0,
        'completed_exams': Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='tamamlandi').count() if sirket_id else 0,
        'pending_exams': Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='beklemede').count() if sirket_id else 0,
        'total_questions': Question.query.filter_by(is_active=True).count(),
        'exams_this_week': 0
    }

    try:
        if sirket_id:
            stats['exams_this_week'] = Candidate.query.filter(
                Candidate.sirket_id == sirket_id,
                Candidate.bitis_tarihi >= week_ago
            ).count()
    except:
        pass

    recent_candidates = []
    try:
        if sirket_id:
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
                          company=company)


# ══════════════════════════════════════════════════════════════
# ADAYLAR (Candidates)
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
        candidates = Candidate.query.filter_by(is_deleted=False).order_by(
            Candidate.created_at.desc()
        ).paginate(page=page, per_page=per_page)

    return render_template('adaylar.html', adaylar=candidates)


@admin_bp.route('/aday/ekle', methods=['GET', 'POST'])
@login_required
def aday_ekle():
    """Add new candidate"""
    if request.method == 'POST':
        from app.models import Candidate
        import string
        import random

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

        try:
            if email:
                from app.tasks.email_tasks import send_exam_invitation
                send_exam_invitation.delay(candidate.id)
        except:
            pass

        flash(f"Aday eklendi. Giriş Kodu: {giris_kodu}", "success")
        return redirect(url_for('admin.adaylar'))

    return render_template('aday_form.html')


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
        flash("Bu adayı silme yetkiniz yok.", "danger")
        return redirect(url_for('admin.adaylar'))

    candidate.is_deleted = True
    db.session.commit()
    flash("Aday silindi.", "success")
    return redirect(url_for('admin.adaylar'))


# ══════════════════════════════════════════════════════════════
# SORULAR (Questions)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/sorular')
@login_required
@superadmin_required
def sorular():
    """Question bank management"""
    from app.models import Question

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
    question.is_active = False
    db.session.commit()
    flash("Soru silindi.", "success")
    return redirect(url_for('admin.sorular'))


# ══════════════════════════════════════════════════════════════
# ŞABLONLAR (Templates)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/sablonlar')
@login_required
def sablonlar():
    """Exam templates"""
    from app.models import ExamTemplate

    sirket_id = session.get('sirket_id')
    
    try:
        if sirket_id:
            templates = ExamTemplate.query.filter_by(sirket_id=sirket_id).all()
        else:
            templates = ExamTemplate.query.all()
    except:
        templates = []

    return render_template('sablonlar.html', sablonlar=templates)


@admin_bp.route('/sablon/ekle', methods=['GET', 'POST'])
@login_required
def sablon_ekle():
    """Add exam template"""
    if request.method == 'POST':
        from app.models import ExamTemplate

        template = ExamTemplate(
            isim=request.form.get('isim'),
            sinav_suresi=int(request.form.get('sinav_suresi', 30)),
            soru_sayisi=int(request.form.get('soru_sayisi', 25)),
            sirket_id=session.get('sirket_id')
        )
        db.session.add(template)
        db.session.commit()
        flash("Şablon eklendi.", "success")
        return redirect(url_for('admin.sablonlar'))

    return render_template('sablon_form.html')


# ══════════════════════════════════════════════════════════════
# RAPORLAR (Reports)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/raporlar')
@login_required
def raporlar():
    """Reports page"""
    from app.models import Candidate
    from datetime import datetime, timedelta

    sirket_id = session.get('sirket_id')
    
    stats = {
        'total': 0,
        'completed': 0,
        'pending': 0,
        'average_score': 0
    }

    try:
        if sirket_id:
            stats['total'] = Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False).count()
            stats['completed'] = Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='tamamlandi').count()
            stats['pending'] = Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='beklemede').count()
            
            completed_candidates = Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='tamamlandi').all()
            if completed_candidates:
                scores = [c.toplam_puan or 0 for c in completed_candidates]
                stats['average_score'] = sum(scores) / len(scores) if scores else 0
    except:
        pass

    return render_template('raporlar.html', stats=stats)


# ══════════════════════════════════════════════════════════════
# KULLANICILAR (Users)
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


@admin_bp.route('/kullanici/ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def kullanici_ekle():
    """Add new user"""
    if request.method == 'POST':
        from app.models import User

        user = User(
            email=request.form.get('email', '').strip().lower(),
            ad_soyad=request.form.get('ad_soyad', '').strip(),
            rol=request.form.get('rol', 'customer'),
            sirket_id=session.get('sirket_id')
        )
        user.set_password(request.form.get('sifre', 'Temp123!'))
        
        db.session.add(user)
        db.session.commit()

        flash("Kullanıcı eklendi.", "success")
        return redirect(url_for('admin.kullanicilar'))

    return render_template('kullanici_form.html')


# ══════════════════════════════════════════════════════════════
# ŞİRKETLER (Companies) - Superadmin only
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/sirketler')
@login_required
@superadmin_required
def sirketler():
    """Company management (superadmin only)"""
    from app.models import Company

    companies = Company.query.all()
    return render_template('sirketler.html', sirketler=companies)


@admin_bp.route('/sirket/ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def sirket_ekle():
    """Add new company"""
    if request.method == 'POST':
        from app.models import Company

        company = Company(
            isim=request.form.get('isim'),
            email=request.form.get('email'),
            telefon=request.form.get('telefon'),
            kredi=int(request.form.get('kredi', 0))
        )
        db.session.add(company)
        db.session.commit()

        flash("Şirket eklendi.", "success")
        return redirect(url_for('admin.sirketler'))

    return render_template('sirket_form.html')


# ══════════════════════════════════════════════════════════════
# AYARLAR (Settings)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/ayarlar', methods=['GET', 'POST'])
@login_required
@superadmin_required
def ayarlar():
    """Company settings"""
    from app.models import Company

    company = Company.query.get(session.get('sirket_id'))

    if request.method == 'POST' and company:
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
# EXPORT (Data Export)
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/export')
@login_required
def export_data():
    """Export candidates data as CSV"""
    from app.models import Candidate

    sirket_id = session.get('sirket_id')
    
    if sirket_id:
        candidates = Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False).all()
    else:
        candidates = Candidate.query.filter_by(is_deleted=False).all()

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


# ══════════════════════════════════════════════════════════════
# SUPER ADMIN RAPOR
# ══════════════════════════════════════════════════════════════
@admin_bp.route('/super-rapor')
@login_required
@superadmin_required
def super_rapor():
    """Platform-wide report for superadmin"""
    from app.models import Company, Candidate, User

    stats = {
        'total_companies': Company.query.count(),
        'total_users': User.query.count(),
        'total_candidates': Candidate.query.count(),
        'completed_exams': Candidate.query.filter_by(sinav_durumu='tamamlandi').count()
    }

    companies = Company.query.all()

    return render_template('super_rapor.html', stats=stats, companies=companies)


@admin_bp.route('/fraud-heatmap')
@login_required
@superadmin_required
def fraud_heatmap():
    """Fraud detection heatmap"""
    return render_template('fraud_heatmap.html')


@admin_bp.route('/logs')
@login_required
@superadmin_required
def admin_logs():
    """Admin activity logs"""
    from app.models.audit_log import AuditLog

    page = request.args.get('page', 1, type=int)
    
    try:
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50)
    except:
        logs = []

    return render_template('admin_logs.html', logs=logs)

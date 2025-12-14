# -*- coding: utf-8 -*-
"""
Admin Routes - Dashboard and management
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.extensions import db

admin_bp = Blueprint('admin', __name__)


def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def check_role(allowed_roles):
    """Check if user has required role"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('rol') not in allowed_roles:
                flash("Bu işlem için yetkiniz yok.", "danger")
                return redirect(url_for('admin.dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Admin dashboard with statistics
    ---
    tags:
      - Admin
    responses:
      200:
        description: Dashboard page
    """
    from app.models import Candidate, Question, Company, User
    from datetime import datetime, timedelta
    
    sirket_id = session.get('sirket_id')
    
    # Statistics
    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    stats = {
        'total_candidates': Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False).count(),
        'completed_exams': Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='tamamlandi').count(),
        'pending_exams': Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='beklemede').count(),
        'total_questions': Question.query.filter_by(sirket_id=sirket_id, is_active=True).count(),
        'exams_this_week': Candidate.query.filter(
            Candidate.sirket_id == sirket_id,
            Candidate.bitis_tarihi >= week_ago
        ).count()
    }
    
    # Recent candidates
    recent_candidates = Candidate.query.filter_by(
        sirket_id=sirket_id, is_deleted=False
    ).order_by(Candidate.created_at.desc()).limit(10).all()
    
    # Company info
    company = Company.query.get(sirket_id)
    
    return render_template('dashboard.html', 
                          stats=stats, 
                          recent_candidates=recent_candidates,
                          company=company)


@admin_bp.route('/adaylar')
@login_required
def adaylar():
    """
    List all candidates
    ---
    tags:
      - Admin
    """
    from app.models import Candidate
    
    sirket_id = session.get('sirket_id')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    candidates = Candidate.query.filter_by(
        sirket_id=sirket_id, is_deleted=False
    ).order_by(Candidate.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('adaylar.html', adaylar=candidates)


@admin_bp.route('/aday/ekle', methods=['GET', 'POST'])
@login_required
def aday_ekle():
    """
    Add new candidate
    ---
    tags:
      - Admin
    """
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
        
        # Generate unique code
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
        
        # Send invitation email via Celery
        if email:
            from app.tasks.email_tasks import send_exam_invitation
            send_exam_invitation.delay(candidate.id)
        
        flash(f"Aday eklendi. Giriş Kodu: {giris_kodu}", "success")
        return redirect(url_for('admin.adaylar'))
    
    return render_template('aday_form.html')


@admin_bp.route('/aday/<int:id>/detay')
@login_required
def aday_detay(id):
    """
    Candidate detail view
    ---
    tags:
      - Admin
    """
    from app.models import Candidate
    
    candidate = Candidate.query.get_or_404(id)
    
    # Check company access
    if candidate.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu adaya erişim yetkiniz yok.", "danger")
        return redirect(url_for('admin.adaylar'))
    
    return render_template('aday_detay.html', aday=candidate)


@admin_bp.route('/sorular')
@login_required
def sorular():
    """
    Question bank management
    ---
    tags:
      - Admin
    """
    from app.models import Question
    
    sirket_id = session.get('sirket_id')
    kategori = request.args.get('kategori')
    zorluk = request.args.get('zorluk')
    page = request.args.get('page', 1, type=int)
    
    query = Question.query.filter_by(sirket_id=sirket_id, is_active=True)
    
    if kategori:
        query = query.filter_by(kategori=kategori)
    if zorluk:
        query = query.filter_by(zorluk=zorluk)
    
    questions = query.order_by(Question.id.desc()).paginate(page=page, per_page=20)
    
    return render_template('sorular.html', sorular=questions)


@admin_bp.route('/soru/ekle', methods=['GET', 'POST'])
@login_required
def soru_ekle():
    """
    Add new question
    ---
    tags:
      - Admin
    """
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


@admin_bp.route('/kullanicilar')
@login_required
@check_role(['superadmin', 'admin'])
def kullanicilar():
    """
    User management
    ---
    tags:
      - Admin
    """
    from app.models import User
    
    sirket_id = session.get('sirket_id')
    
    if session.get('rol') == 'superadmin':
        users = User.query.all()
    else:
        users = User.query.filter_by(sirket_id=sirket_id).all()
    
    return render_template('kullanicilar.html', kullanicilar=users)


@admin_bp.route('/ayarlar', methods=['GET', 'POST'])
@login_required
def ayarlar():
    """
    Company settings
    ---
    tags:
      - Admin
    """
    from app.models import Company
    
    company = Company.query.get(session.get('sirket_id'))
    
    if request.method == 'POST':
        company.isim = request.form.get('isim')
        company.email = request.form.get('email')
        company.telefon = request.form.get('telefon')
        company.logo_url = request.form.get('logo_url')
        company.primary_color = request.form.get('primary_color')
        company.webhook_url = request.form.get('webhook_url')
        
        # SMTP settings
        company.smtp_host = request.form.get('smtp_host')
        company.smtp_port = int(request.form.get('smtp_port', 587))
        company.smtp_user = request.form.get('smtp_user')
        if request.form.get('smtp_pass'):
            company.smtp_pass = request.form.get('smtp_pass')
        company.smtp_from = request.form.get('smtp_from')
        
        db.session.commit()
        flash("Ayarlar kaydedildi.", "success")
    
    return render_template('ayarlar.html', company=company)

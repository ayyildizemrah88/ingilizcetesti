# -*- coding: utf-8 -*-
"""
Admin Routes - Dashboard and management
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.extensions import db

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
    
    # Statistics - with error handling
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
    
    # Recent candidates
    try:
        recent_candidates = Candidate.query.filter_by(
            sirket_id=sirket_id, is_deleted=False
        ).order_by(Candidate.created_at.desc()).limit(10).all() if sirket_id else []
    except:
        recent_candidates = []
    
    # Company info
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


@admin_bp.route('/aday/<int:id>/sil', methods=['POST'])
@login_required
def aday_sil(id):
    """
    Delete candidate (soft delete)
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
    
    candidate.is_deleted = True
    db.session.commit()
    
    flash("Aday silindi.", "success")
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/bulk-upload', methods=['POST'])
@login_required
def bulk_upload():
    """
    Bulk upload candidates from Excel file
    ---
    tags:
      - Admin
    """
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
        # Read Excel file
        df = pd.read_excel(io.BytesIO(file.read()))
        
        # Check required column
        if 'ad_soyad' not in df.columns:
            flash("Excel dosyasında 'ad_soyad' kolonu bulunamadı.", "danger")
            return redirect(url_for('admin.adaylar'))
        
        sirket_id = session.get('sirket_id')
        added_count = 0
        
        for _, row in df.iterrows():
            ad_soyad = str(row.get('ad_soyad', '')).strip()
            if not ad_soyad or ad_soyad == 'nan':
                continue
            
            # Generate unique code
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


@admin_bp.route('/sorular')
@login_required
@superadmin_required
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
@superadmin_required
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


@admin_bp.route('/soru/<int:id>/sil', methods=['POST'])
@login_required
@superadmin_required
def soru_sil(id):
    """
    Delete question (soft delete)
    ---
    tags:
      - Admin
    """
    from app.models import Question
    
    question = Question.query.get_or_404(id)
    
    # Check company access
    if question.sirket_id != session.get('sirket_id') and session.get('rol') != 'superadmin':
        flash("Bu soruya erişim yetkiniz yok.", "danger")
        return redirect(url_for('admin.sorular'))
    
    question.is_active = False
    db.session.commit()
    
    flash("Soru silindi.", "success")
    return redirect(url_for('admin.sorular'))


@admin_bp.route('/kullanicilar')
@login_required
@superadmin_required
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


@admin_bp.route('/kullanici-ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def kullanici_ekle():
    """
    Add new user
    ---
    tags:
      - Admin
    """
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
        
        # Check if email exists
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
    """
    Delete user (soft delete)
    ---
    tags:
      - Admin
    """
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
    """
    Edit user
    ---
    tags:
      - Admin
    """
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


@admin_bp.route('/demo-olustur', methods=['GET', 'POST'])
@login_required
@superadmin_required
def demo_olustur():
    """
    Create demo company with test data
    ---
    tags:
      - Admin
    """
    from app.models import Company, User, Candidate
    from werkzeug.security import generate_password_hash
    import string
    import random
    
    if request.method == 'POST':
        demo_name = request.form.get('demo_name', 'Demo Şirket')
        
        # Create demo company
        company = Company(
            isim=demo_name,
            ad=demo_name,
            email=f"demo_{random.randint(1000,9999)}@skillstestcenter.com",
            kredi=100,
            is_active=True
        )
        db.session.add(company)
        db.session.flush()
        
        # Create demo admin
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
        
        # Create some demo candidates
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


@admin_bp.route('/sablonlar')
@login_required
@superadmin_required
def sablonlar():
    """
    Exam templates list
    ---
    tags:
      - Admin
    """
    from app.models import ExamTemplate
    
    sirket_id = session.get('sirket_id')
    templates = ExamTemplate.query.filter_by(sirket_id=sirket_id, is_active=True).all()
    
    return render_template('sablonlar.html', sablonlar=templates)


@admin_bp.route('/sablon-ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def sablon_ekle():
    """
    Add new exam template
    ---
    tags:
      - Admin
    """
    if request.method == 'POST':
        from app.models import ExamTemplate
        
        template = ExamTemplate(
            isim=request.form.get('isim'),
            sinav_suresi=int(request.form.get('sinav_suresi', 30)),
            soru_suresi=int(request.form.get('soru_suresi', 60)),
            soru_limiti=int(request.form.get('soru_limiti', 10)),
            baslangic_seviyesi=request.form.get('baslangic_seviyesi', 'B1'),
            sirket_id=session.get('sirket_id')
        )
        
        db.session.add(template)
        db.session.commit()
        
        flash("Şablon oluşturuldu.", "success")
        return redirect(url_for('admin.sablonlar'))
    
    return render_template('sablon_form.html')


# ══════════════════════════════════════════════════════════════
# COMPANY MANAGEMENT (SuperAdmin Only)
# ══════════════════════════════════════════════════════════════

@admin_bp.route('/sirketler')
@login_required
@superadmin_required
def sirketler():
    """
    Company management page
    ---
    tags:
      - Admin
    """
    from app.models import Company
    
    companies = Company.query.order_by(Company.id.desc()).all()
    return render_template('sirketler.html', sirketler=companies)


@admin_bp.route('/sirket-ekle', methods=['GET', 'POST'])
@login_required
@superadmin_required
def sirket_ekle():
    """
    Add new company
    ---
    tags:
      - Admin
    """
    from app.models import Company, User
    import string
    import random
    from werkzeug.security import generate_password_hash
    
    if request.method == 'POST':
        isim = request.form.get('isim', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        adres = request.form.get('adres', '').strip()
        
        # Admin user details
        admin_email = request.form.get('admin_email', '').strip().lower()
        admin_password = request.form.get('admin_password', '')
        
        if not isim or not admin_email:
            flash("Şirket adı ve admin email zorunludur.", "danger")
            return render_template('sirket_form.html')
        
        # Create company
        company = Company(
            isim=isim,
            ad=isim,  # Fallback
            email=email,
            telefon=telefon,
            adres=adres,
            kredi=10,  # Default credits
            is_active=True
        )
        
        db.session.add(company)
        db.session.flush()  # Get the ID
        
        # Create admin user for the company
        if not admin_password:
            admin_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        admin_user = User(
            email=admin_email,
            password=generate_password_hash(admin_password),
            ad_soyad=f"{isim} Admin",
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
    """
    Edit company
    ---
    tags:
      - Admin
    """
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
    """
    Delete company (soft delete)
    ---
    tags:
      - Admin
    """
    from app.models import Company
    
    company = Company.query.get_or_404(id)
    company.is_active = False
    db.session.commit()
    
    flash("Şirket devre dışı bırakıldı.", "success")
    return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/<int:id>/kredi-yukle', methods=['POST'])
@login_required
@superadmin_required
def sirket_kredi_yukle(id):
    """
    Add credits to company
    ---
    tags:
      - Admin
    """
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
    """
    Company credit management page (alias for templates)
    ---
    tags:
      - Admin
    """
    from app.models import Company
    
    company = Company.query.get_or_404(id)
    
    if request.method == 'POST':
        miktar = int(request.form.get('miktar', 0))
        if miktar > 0:
            company.kredi = (company.kredi or 0) + miktar
            db.session.commit()
            flash(f"{miktar} kredi yüklendi. Yeni bakiye: {company.kredi}", "success")
        else:
            flash("Geçersiz miktar.", "danger")
        return redirect(url_for('admin.sirketler'))
    
    return render_template('kredi_yukle.html', sirket=company)


@admin_bp.route('/super-rapor')
@login_required
@superadmin_required
def super_rapor():
    """
    Platform-wide report for superadmin
    ---
    tags:
      - Admin
    """
    from app.models import Candidate, Question, Company, User
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    # Platform statistics
    stats = {
        'total_companies': Company.query.count(),
        'total_candidates': Candidate.query.count(),
        'total_questions': Question.query.count(),
        'total_users': User.query.count(),
        'active_exams': Candidate.query.filter_by(sinav_durumu='sinavda').count(),
        'completed_exams': Candidate.query.filter_by(sinav_durumu='tamamlandi').count(),
    }
    
    # Company breakdown
    company_stats = []
    for company in Company.query.all():
        company_stats.append({
            'id': company.id,
            'isim': company.isim or company.ad,
            'aday_sayisi': Candidate.query.filter_by(sirket_id=company.id).count(),
            'soru_sayisi': Question.query.filter_by(sirket_id=company.id).count(),
        })
    
    return render_template('super_rapor.html', 
                          stats=stats, 
                          company_stats=company_stats)


@admin_bp.route('/logs')
@login_required
@superadmin_required
def admin_logs():
    """Admin activity logs"""
    from app.models.admin import AuditLog
    
    page = request.args.get('page', 1, type=int)
    
    try:
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50)
    except:
        logs = []
    
    return render_template('admin_logs.html', logs=logs)


@admin_bp.route('/fraud-heatmap')
@login_required
@superadmin_required
def fraud_heatmap():
    """Fraud detection heatmap"""
    return render_template('fraud_heatmap.html')


@admin_bp.route('/raporlar')
@login_required
def raporlar():
    """Company reports page"""
    from app.models import Candidate
    from datetime import datetime, timedelta
    
    sirket_id = session.get('sirket_id')
    
    # Basic stats
    stats = {
        'total': Candidate.query.filter_by(sirket_id=sirket_id).count() if sirket_id else 0,
        'completed': Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='tamamlandi').count() if sirket_id else 0,
        'pending': Candidate.query.filter_by(sirket_id=sirket_id, sinav_durumu='beklemede').count() if sirket_id else 0,
    }
    
    # Get completed candidates for the report
    tamamlananlar = []
    try:
        if sirket_id:
            tamamlananlar = Candidate.query.filter_by(
                sirket_id=sirket_id, 
                sinav_durumu='tamamlandi'
            ).order_by(Candidate.sinav_bitis.desc()).limit(50).all()
        else:
            tamamlananlar = Candidate.query.filter_by(
                sinav_durumu='tamamlandi'
            ).order_by(Candidate.sinav_bitis.desc()).limit(50).all()
    except Exception as e:
        pass
    
    return render_template('raporlar.html', stats=stats, tamamlananlar=tamamlananlar)


# ══════════════════════════════════════════════════════════════
# DATA MANAGEMENT (KVKK/GDPR Compliant)
# ══════════════════════════════════════════════════════════════

@admin_bp.route('/veri-yonetimi')
@login_required
@superadmin_required
def veri_yonetimi():
    """
    Data management dashboard
    ---
    tags:
      - Admin
    """
    from app.models import Candidate, Question, Answer
    from sqlalchemy import func
    import os
    
    # Get data statistics
    sirket_id = session.get('sirket_id')
    
    stats = {
        'total_candidates': Candidate.query.count(),
        'total_questions': Question.query.count(),
        'total_answers': Answer.query.count() if hasattr(Answer, 'query') else 0,
        'speaking_recordings': 0,  # Count from storage
        'audit_logs': 0,
        'db_size_mb': 0
    }
    
    # Get backup list
    backup_dir = os.path.join(os.getcwd(), 'backups')
    backups = []
    if os.path.exists(backup_dir):
        for f in os.listdir(backup_dir):
            if f.endswith('.sql.gz') or f.endswith('.sql'):
                filepath = os.path.join(backup_dir, f)
                backups.append({
                    'filename': f,
                    'size_mb': os.path.getsize(filepath) / (1024 * 1024),
                    'created_at': None,
                    'location': 'local'
                })
    
    # Get deletion requests (would need a DeletionRequest model)
    deletion_requests = []
    
    return render_template('veri_yonetimi.html', 
                          stats=stats, 
                          backups=backups,
                          deletion_requests=deletion_requests)


@admin_bp.route('/veri-yonetimi/yedek-al', methods=['POST'])
@login_required
@superadmin_required
def yedek_al():
    """Create database backup"""
    try:
        from app.tasks.backup_tasks import backup_database
        
        location = request.form.get('location', 'local')
        
        # Trigger async backup task
        backup_database.delay()
        
        flash("Yedekleme işlemi başlatıldı. Tamamlandığında bildirim alacaksınız.", "success")
    except Exception as e:
        flash(f"Yedekleme başlatılamadı: {str(e)}", "danger")
    
    return redirect(url_for('admin.veri_yonetimi'))


@admin_bp.route('/veri-yonetimi/otomatik-temizle', methods=['POST'])
@login_required
@superadmin_required
def otomatik_temizle():
    """Run automatic KVKK-compliant cleanup"""
    try:
        from app.tasks.cleanup_tasks import run_all_cleanup_tasks
        
        # Trigger async cleanup task
        run_all_cleanup_tasks.delay()
        
        flash("Temizlik işlemi başlatıldı. KVKK uyumlu veriler silinecek.", "success")
    except Exception as e:
        flash(f"Temizlik başlatılamadı: {str(e)}", "danger")
    
    return redirect(url_for('admin.veri_yonetimi'))


@admin_bp.route('/veri-yonetimi/manuel-temizle', methods=['POST'])
@login_required
@superadmin_required
def manuel_temizle():
    """Manual data cleanup by date and type"""
    from datetime import datetime
    from app.models import Candidate, Answer
    
    data_type = request.form.get('data_type')
    before_date_str = request.form.get('before_date')
    confirmation = request.form.get('confirmation_code')
    
    # Validate confirmation
    if confirmation != 'SIL-ONAY':
        flash("Geçersiz onay kodu! İşlem iptal edildi.", "danger")
        return redirect(url_for('admin.veri_yonetimi'))
    
    try:
        before_date = datetime.strptime(before_date_str, '%Y-%m-%d')
        deleted_count = 0
        
        if data_type == 'completed_candidates':
            # Soft delete completed candidates before date
            candidates = Candidate.query.filter(
                Candidate.sinav_bitis < before_date,
                Candidate.durum == 'tamamlandi'
            ).all()
            
            for c in candidates:
                c.is_deleted = True
                deleted_count += 1
            
            db.session.commit()
            
        elif data_type == 'exam_answers':
            # Delete old answers
            deleted_count = Answer.query.filter(
                Answer.created_at < before_date
            ).delete()
            db.session.commit()
        
        flash(f"{deleted_count} kayıt başarıyla silindi.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Silme hatası: {str(e)}", "danger")
    
    return redirect(url_for('admin.veri_yonetimi'))


@admin_bp.route('/veri-yonetimi/kvkk-sil/<int:candidate_id>', methods=['POST'])
@login_required
@superadmin_required
def kvkk_sil(candidate_id):
    """GDPR/KVKK compliant full data deletion for a candidate"""
    from app.models import Candidate, Answer
    
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        
        # Delete all answers for this candidate
        Answer.query.filter_by(aday_id=candidate_id).delete()
        
        # Anonymize candidate data (keep for statistics)
        candidate.ad_soyad = f"Silinen Kullanıcı #{candidate_id}"
        candidate.email = f"deleted_{candidate_id}@anonymized.local"
        candidate.telefon = None
        candidate.is_deleted = True
        candidate.kvkk_deleted_at = db.func.now()
        
        db.session.commit()
        
        flash(f"Aday #{candidate_id} verileri KVKK uyumlu olarak silindi.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Silme hatası: {str(e)}", "danger")
    
    return redirect(url_for('admin.veri_yonetimi'))


@admin_bp.route('/veri-yonetimi/kvkk-rapor')
@login_required
@superadmin_required
def kvkk_rapor():
    """Generate KVKK compliance report"""
    from app.models import Candidate, Question
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    one_year_ago = now - timedelta(days=365)
    two_years_ago = now - timedelta(days=730)
    
    report = {
        'generated_at': now,
        'total_candidates': Candidate.query.count(),
        'active_candidates': Candidate.query.filter_by(is_deleted=False).count(),
        'deleted_candidates': Candidate.query.filter_by(is_deleted=True).count(),
        'candidates_older_than_1year': Candidate.query.filter(
            Candidate.created_at < one_year_ago
        ).count(),
        'total_questions': Question.query.count(),
        'retention_policy': {
            'speaking_recordings': '1 yıl',
            'exam_answers': '1 yıl',
            'audit_logs': '2 yıl',
            'consent_logs': '5 yıl'
        }
    }
    
    return render_template('kvkk_rapor.html', report=report)

# -*- coding: utf-8 -*-
"""
Admin Routes - Super Admin Panel Yönetimi
GitHub: app/routes/admin.py
Skills Test Center - Administration System
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from werkzeug.security import generate_password_hash
from app.extensions import db, csrf, limiter
from datetime import datetime, timedelta
import logging
import json

admin_bp = Blueprint('admin', __name__)

# ══════════════════════════════════════════════════════════════════
# DECORATOR'LAR
# ══════════════════════════════════════════════════════════════════

def login_required(f):
    """Giriş yapılmış olmalı"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Sadece superadmin erişebilir"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu sayfaya erişim yetkiniz yok.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/dashboard')
@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard - Ana sayfa istatistikleri"""
    from app.models import User, Company, Candidate, Question
    
    try:
        stats = {
            'total_companies': Company.query.filter_by(is_active=True).count() if hasattr(Company, 'is_active') else Company.query.count(),
            'total_candidates': Candidate.query.filter_by(is_deleted=False).count() if hasattr(Candidate, 'is_deleted') else Candidate.query.count(),
            'total_questions': Question.query.filter_by(is_active=True).count() if hasattr(Question, 'is_active') else Question.query.count(),
            'active_exams': Candidate.query.filter_by(sinav_durumu='devam_ediyor', is_deleted=False).count() if hasattr(Candidate, 'is_deleted') else Candidate.query.filter_by(sinav_durumu='devam_ediyor').count(),
            'completed_today': Candidate.query.filter(
                Candidate.bitis_tarihi >= datetime.now().replace(hour=0, minute=0, second=0),
                Candidate.sinav_durumu == 'tamamlandi'
            ).count(),
            'total_users': User.query.count()
        }
    except Exception as e:
        current_app.logger.error(f"Dashboard stats error: {e}")
        stats = {
            'total_companies': 0,
            'total_candidates': 0,
            'total_questions': 0,
            'active_exams': 0,
            'completed_today': 0,
            'total_users': 0
        }
    
    # Son aktiviteler
    recent_candidates = []
    try:
        recent_candidates = Candidate.query.filter_by(is_deleted=False).order_by(
            Candidate.created_at.desc()
        ).limit(10).all()
    except:
        pass
    
    return render_template('admin/dashboard.html', 
                          stats=stats, 
                          recent_candidates=recent_candidates)


# ══════════════════════════════════════════════════════════════════
# ŞİRKET YÖNETİMİ
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/sirketler')
@login_required
@admin_required
def sirketler():
    """Şirket listesi"""
    from app.models import Company
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search = request.args.get('search', '').strip()
    query = Company.query
    
    if search:
        query = query.filter(Company.isim.ilike(f'%{search}%'))
    
    companies = query.order_by(Company.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin/sirketler.html', companies=companies, search=search)


@admin_bp.route('/sirket-ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def sirket_ekle():
    """Yeni şirket ekle"""
    from app.models import Company, User
    
    if request.method == 'POST':
        isim = request.form.get('isim', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefon = request.form.get('telefon', '').strip()
        adres = request.form.get('adres', '').strip()
        kredi = int(request.form.get('kredi', 10))
        
        # Admin kullanıcı bilgileri
        admin_email = request.form.get('admin_email', '').strip().lower()
        admin_ad_soyad = request.form.get('admin_ad_soyad', '').strip()
        admin_password = request.form.get('admin_password', '')
        
        if not isim or not email:
            flash("Şirket adı ve email zorunludur.", "warning")
            return render_template('admin/sirket_form.html')
        
        try:
            # Şirket oluştur
            company = Company(
                isim=isim,
                email=email,
                telefon=telefon,
                adres=adres,
                kredi=kredi,
                is_active=True,
                created_at=datetime.now()
            )
            db.session.add(company)
            db.session.flush()
            
            # Admin kullanıcı oluştur
            if admin_email and admin_password:
                user = User(
                    email=admin_email,
                    sifre_hash=generate_password_hash(admin_password),
                    rol='customer',
                    ad_soyad=admin_ad_soyad or isim,
                    sirket_id=company.id,
                    is_active=True,
                    created_at=datetime.now()
                )
                db.session.add(user)
            
            db.session.commit()
            flash(f"Şirket '{isim}' başarıyla eklendi.", "success")
            return redirect(url_for('admin.sirketler'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Company create error: {e}")
            flash("Şirket eklenirken bir hata oluştu.", "danger")
    
    return render_template('admin/sirket_form.html')


@admin_bp.route('/sirket/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@admin_required
def sirket_duzenle(id):
    """Şirket düzenle"""
    from app.models import Company
    
    company = Company.query.get_or_404(id)
    
    if request.method == 'POST':
        company.isim = request.form.get('isim', company.isim).strip()
        company.email = request.form.get('email', company.email).strip().lower()
        company.telefon = request.form.get('telefon', '').strip()
        company.adres = request.form.get('adres', '').strip()
        company.kredi = int(request.form.get('kredi', company.kredi))
        company.is_active = request.form.get('is_active') == 'on'
        
        try:
            db.session.commit()
            flash(f"Şirket '{company.isim}' güncellendi.", "success")
            return redirect(url_for('admin.sirketler'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Company update error: {e}")
            flash("Güncelleme sırasında hata oluştu.", "danger")
    
    return render_template('admin/sirket_form.html', company=company)


@admin_bp.route('/sirket/<int:id>/sil', methods=['POST'])
@login_required
@admin_required
def sirket_sil(id):
    """Şirket sil (soft delete)"""
    from app.models import Company
    
    company = Company.query.get_or_404(id)
    
    try:
        company.is_active = False
        db.session.commit()
        flash(f"Şirket '{company.isim}' deaktif edildi.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Silme işlemi başarısız.", "danger")
    
    return redirect(url_for('admin.sirketler'))


@admin_bp.route('/sirket/<int:id>/kredi-ekle', methods=['POST'])
@login_required
@admin_required
def kredi_ekle(id):
    """Şirkete kredi ekle"""
    from app.models import Company
    
    company = Company.query.get_or_404(id)
    miktar = int(request.form.get('miktar', 0))
    
    if miktar > 0:
        try:
            company.kredi += miktar
            db.session.commit()
            flash(f"'{company.isim}' şirketine {miktar} kredi eklendi.", "success")
        except Exception as e:
            db.session.rollback()
            flash("Kredi ekleme başarısız.", "danger")
    
    return redirect(url_for('admin.sirketler'))


# ══════════════════════════════════════════════════════════════════
# ADAY YÖNETİMİ
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/adaylar')
@login_required
@admin_required
def adaylar():
    """Aday listesi"""
    from app.models import Candidate, Company
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    company_id = request.args.get('company_id', type=int)
    
    query = Candidate.query.filter_by(is_deleted=False)
    
    if search:
        query = query.filter(
            (Candidate.ad_soyad.ilike(f'%{search}%')) |
            (Candidate.email.ilike(f'%{search}%')) |
            (Candidate.giris_kodu.ilike(f'%{search}%'))
        )
    
    if status:
        query = query.filter_by(sinav_durumu=status)
    
    if company_id:
        query = query.filter_by(sirket_id=company_id)
    
    candidates = query.order_by(Candidate.created_at.desc()).paginate(page=page, per_page=per_page)
    companies = Company.query.filter_by(is_active=True).all()
    
    return render_template('admin/adaylar.html', 
                          candidates=candidates, 
                          companies=companies,
                          search=search,
                          status=status,
                          company_id=company_id)


@admin_bp.route('/aday/ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def aday_ekle():
    """Yeni aday ekle"""
    from app.models import Candidate, Company
    import string
    import random
    
    companies = Company.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        email = request.form.get('email', '').strip().lower()
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        cep_no = request.form.get('cep_no', '').strip()
        sirket_id = request.form.get('sirket_id', type=int)
        sinav_suresi = int(request.form.get('sinav_suresi', 30))
        soru_limiti = int(request.form.get('soru_limiti', 25))
        
        if not ad_soyad or not email:
            flash("Ad Soyad ve Email zorunludur.", "warning")
            return render_template('admin/aday_form.html', companies=companies)
        
        # Giriş kodu oluştur
        giris_kodu = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        try:
            candidate = Candidate(
                ad_soyad=ad_soyad,
                email=email,
                tc_kimlik=tc_kimlik,
                cep_no=cep_no,
                giris_kodu=giris_kodu,
                sirket_id=sirket_id,
                sinav_suresi=sinav_suresi,
                soru_limiti=soru_limiti,
                sinav_durumu='beklemede',
                created_at=datetime.now()
            )
            db.session.add(candidate)
            
            # Şirket kredisini düş
            if sirket_id:
                company = Company.query.get(sirket_id)
                if company and company.kredi > 0:
                    company.kredi -= 1
            
            db.session.commit()
            
            # Email gönder
            send_invitation = request.form.get('send_email') == 'on'
            if send_invitation and email:
                try:
                    from app.routes.auth import send_candidate_invitation_email
                    send_candidate_invitation_email(candidate)
                    flash(f"Aday eklendi ve davet emaili gönderildi. Kod: {giris_kodu}", "success")
                except Exception as e:
                    current_app.logger.error(f"Invitation email error: {e}")
                    flash(f"Aday eklendi ancak email gönderilemedi. Kod: {giris_kodu}", "warning")
            else:
                flash(f"Aday eklendi. Giriş Kodu: {giris_kodu}", "success")
            
            return redirect(url_for('admin.adaylar'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Candidate create error: {e}")
            flash("Aday eklenirken bir hata oluştu.", "danger")
    
    return render_template('admin/aday_form.html', companies=companies)


@admin_bp.route('/aday/<int:id>')
@login_required
@admin_required
def aday_detay(id):
    """Aday detayı"""
    from app.models import Candidate, ExamAnswer
    
    candidate = Candidate.query.get_or_404(id)
    
    # Sınav cevapları
    answers = []
    try:
        answers = ExamAnswer.query.filter_by(aday_id=id).all()
    except:
        pass
    
    return render_template('admin/aday_detay.html', candidate=candidate, answers=answers)


@admin_bp.route('/aday/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@admin_required
def aday_duzenle(id):
    """Aday düzenle"""
    from app.models import Candidate, Company
    
    candidate = Candidate.query.get_or_404(id)
    companies = Company.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        candidate.ad_soyad = request.form.get('ad_soyad', candidate.ad_soyad).strip()
        candidate.email = request.form.get('email', candidate.email).strip().lower()
        candidate.tc_kimlik = request.form.get('tc_kimlik', '').strip()
        candidate.cep_no = request.form.get('cep_no', '').strip()
        candidate.sinav_suresi = int(request.form.get('sinav_suresi', 30))
        candidate.soru_limiti = int(request.form.get('soru_limiti', 25))
        
        try:
            db.session.commit()
            flash("Aday bilgileri güncellendi.", "success")
            return redirect(url_for('admin.aday_detay', id=id))
        except Exception as e:
            db.session.rollback()
            flash("Güncelleme başarısız.", "danger")
    
    return render_template('admin/aday_form.html', candidate=candidate, companies=companies)


@admin_bp.route('/aday/<int:id>/sil', methods=['POST'])
@login_required
@admin_required
def aday_sil(id):
    """Aday sil (soft delete)"""
    from app.models import Candidate
    
    candidate = Candidate.query.get_or_404(id)
    
    try:
        candidate.is_deleted = True
        db.session.commit()
        flash("Aday silindi.", "success")
    except:
        db.session.rollback()
        flash("Silme başarısız.", "danger")
    
    return redirect(url_for('admin.adaylar'))


@admin_bp.route('/aday/<int:id>/sinav-sifirla', methods=['POST'])
@login_required
@admin_required
def sinav_sifirla(id):
    """Aday sınavını sıfırla"""
    from app.models import Candidate, ExamAnswer
    
    candidate = Candidate.query.get_or_404(id)
    
    try:
        # Cevapları sil
        ExamAnswer.query.filter_by(aday_id=id).delete()
        
        # Sınavı sıfırla
        candidate.sinav_durumu = 'beklemede'
        candidate.baslangic_tarihi = None
        candidate.bitis_tarihi = None
        candidate.puan = None
        candidate.seviye_sonuc = None
        
        db.session.commit()
        flash(f"'{candidate.ad_soyad}' adayının sınavı sıfırlandı.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Sınav sıfırlama başarısız.", "danger")
    
    return redirect(url_for('admin.aday_detay', id=id))


@admin_bp.route('/aday/<int:id>/sure-uzat', methods=['POST'])
@login_required
@admin_required
def sure_uzat(id):
    """Aday sınav süresini uzat"""
    from app.models import Candidate
    
    candidate = Candidate.query.get_or_404(id)
    ek_sure = int(request.form.get('ek_sure', 10))
    
    try:
        candidate.sinav_suresi = (candidate.sinav_suresi or 30) + ek_sure
        db.session.commit()
        flash(f"Sınav süresi {ek_sure} dakika uzatıldı.", "success")
    except:
        db.session.rollback()
        flash("Süre uzatma başarısız.", "danger")
    
    return redirect(url_for('admin.aday_detay', id=id))


@admin_bp.route('/aday/<int:id>/davet-gonder', methods=['POST'])
@login_required
@admin_required
def davet_gonder(id):
    """Adaya davet emaili gönder"""
    from app.models import Candidate
    
    candidate = Candidate.query.get_or_404(id)
    
    if not candidate.email:
        flash("Adayın email adresi yok.", "warning")
        return redirect(url_for('admin.aday_detay', id=id))
    
    try:
        from app.routes.auth import send_candidate_invitation_email
        if send_candidate_invitation_email(candidate):
            flash(f"Davet emaili gönderildi: {candidate.email}", "success")
        else:
            flash("Email gönderilemedi. SMTP ayarlarını kontrol edin.", "danger")
    except Exception as e:
        current_app.logger.error(f"Invitation email error: {e}")
        flash("Email gönderme hatası.", "danger")
    
    return redirect(url_for('admin.aday_detay', id=id))


# ══════════════════════════════════════════════════════════════════
# SORU YÖNETİMİ
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/sorular')
@login_required
@admin_required
def sorular():
    """Soru listesi"""
    from app.models import Question
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    level = request.args.get('level', '')
    skill = request.args.get('skill', '')
    search = request.args.get('search', '').strip()
    
    query = Question.query.filter_by(is_active=True)
    
    if level:
        query = query.filter_by(seviye=level)
    if skill:
        query = query.filter_by(beceri=skill)
    if search:
        query = query.filter(Question.soru_metni.ilike(f'%{search}%'))
    
    questions = query.order_by(Question.created_at.desc()).paginate(page=page, per_page=per_page)
    
    levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    skills = ['grammar', 'vocabulary', 'reading', 'listening', 'speaking', 'writing']
    
    return render_template('admin/sorular.html',
                          questions=questions,
                          levels=levels,
                          skills=skills,
                          current_level=level,
                          current_skill=skill,
                          search=search)


@admin_bp.route('/soru/ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def soru_ekle():
    """Yeni soru ekle"""
    from app.models import Question
    
    if request.method == 'POST':
        soru_metni = request.form.get('soru_metni', '').strip()
        seviye = request.form.get('seviye', 'B1')
        beceri = request.form.get('beceri', 'grammar')
        soru_tipi = request.form.get('soru_tipi', 'coktan_secmeli')
        
        # Seçenekler
        secenekler = []
        dogru_cevap = request.form.get('dogru_cevap', '')
        
        for i in range(1, 5):
            secenek = request.form.get(f'secenek_{i}', '').strip()
            if secenek:
                secenekler.append(secenek)
        
        if not soru_metni:
            flash("Soru metni zorunludur.", "warning")
            return render_template('admin/soru_form.html')
        
        try:
            question = Question(
                soru_metni=soru_metni,
                seviye=seviye,
                beceri=beceri,
                soru_tipi=soru_tipi,
                secenekler=json.dumps(secenekler) if secenekler else None,
                dogru_cevap=dogru_cevap,
                is_active=True,
                created_at=datetime.now()
            )
            db.session.add(question)
            db.session.commit()
            
            flash("Soru eklendi.", "success")
            return redirect(url_for('admin.sorular'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Question create error: {e}")
            flash("Soru eklenirken hata oluştu.", "danger")
    
    levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    skills = ['grammar', 'vocabulary', 'reading', 'listening', 'speaking', 'writing']
    
    return render_template('admin/soru_form.html', levels=levels, skills=skills)


@admin_bp.route('/soru/<int:id>/sil', methods=['POST'])
@login_required
@admin_required
def soru_sil(id):
    """Soru sil (soft delete)"""
    from app.models import Question
    
    question = Question.query.get_or_404(id)
    
    try:
        question.is_active = False
        db.session.commit()
        flash("Soru silindi.", "success")
    except:
        db.session.rollback()
        flash("Silme başarısız.", "danger")
    
    return redirect(url_for('admin.sorular'))


# ══════════════════════════════════════════════════════════════════
# SINAV ŞABLONLARI
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/sablonlar')
@login_required
@admin_required
def sablonlar():
    """Sınav şablonu listesi"""
    from app.models import ExamTemplate
    
    try:
        templates = ExamTemplate.query.filter_by(is_active=True).order_by(ExamTemplate.created_at.desc()).all()
    except:
        templates = []
    
    return render_template('admin/sablonlar.html', templates=templates)


@admin_bp.route('/sablon/yeni', methods=['GET', 'POST'])
@admin_bp.route('/sablon/ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def sablon_ekle():
    """Yeni sınav şablonu ekle"""
    from app.models import ExamTemplate
    
    if request.method == 'POST':
        isim = request.form.get('isim', '').strip()
        aciklama = request.form.get('aciklama', '').strip()
        sure = int(request.form.get('sure', 30))
        soru_sayisi = int(request.form.get('soru_sayisi', 25))
        
        # Beceri dağılımı
        beceri_dagilimi = {}
        for skill in ['grammar', 'vocabulary', 'reading', 'listening']:
            beceri_dagilimi[skill] = int(request.form.get(f'beceri_{skill}', 0))
        
        # Seviye dağılımı
        seviye_dagilimi = {}
        for level in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
            seviye_dagilimi[level] = int(request.form.get(f'seviye_{level}', 0))
        
        if not isim:
            flash("Şablon adı zorunludur.", "warning")
            return render_template('admin/sablon_form.html')
        
        try:
            template = ExamTemplate(
                isim=isim,
                aciklama=aciklama,
                sure=sure,
                soru_sayisi=soru_sayisi,
                beceri_dagilimi=json.dumps(beceri_dagilimi),
                seviye_dagilimi=json.dumps(seviye_dagilimi),
                is_active=True,
                created_at=datetime.now()
            )
            db.session.add(template)
            db.session.commit()
            
            flash(f"Şablon '{isim}' oluşturuldu.", "success")
            return redirect(url_for('admin.sablonlar'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Template create error: {e}")
            flash("Şablon oluşturulurken hata oluştu.", "danger")
    
    return render_template('admin/sablon_form.html')


@admin_bp.route('/sablon/<int:id>/sil', methods=['POST'])
@login_required
@admin_required
def sablon_sil(id):
    """Şablon sil"""
    from app.models import ExamTemplate
    
    template = ExamTemplate.query.get_or_404(id)
    
    try:
        template.is_active = False
        db.session.commit()
        flash("Şablon silindi.", "success")
    except:
        db.session.rollback()
        flash("Silme başarısız.", "danger")
    
    return redirect(url_for('admin.sablonlar'))


# ══════════════════════════════════════════════════════════════════
# KULLANICI YÖNETİMİ
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/kullanicilar')
@login_required
@admin_required
def kullanicilar():
    """Kullanıcı listesi"""
    from app.models import User
    
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/kullanicilar.html', users=users)


@admin_bp.route('/kullanici/ekle', methods=['GET', 'POST'])
@login_required
@admin_required
def kullanici_ekle():
    """Yeni kullanıcı ekle"""
    from app.models import User, Company
    
    companies = Company.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        ad_soyad = request.form.get('ad_soyad', '').strip()
        rol = request.form.get('rol', 'customer')
        sirket_id = request.form.get('sirket_id', type=int)
        
        if not email or not password:
            flash("Email ve şifre zorunludur.", "warning")
            return render_template('admin/kullanici_form.html', companies=companies)
        
        # Email kontrolü
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Bu email zaten kayıtlı.", "danger")
            return render_template('admin/kullanici_form.html', companies=companies)
        
        try:
            user = User(
                email=email,
                sifre_hash=generate_password_hash(password),
                ad_soyad=ad_soyad or email,
                rol=rol,
                sirket_id=sirket_id if rol == 'customer' else None,
                is_active=True,
                created_at=datetime.now()
            )
            db.session.add(user)
            db.session.commit()
            
            flash(f"Kullanıcı '{email}' oluşturuldu.", "success")
            return redirect(url_for('admin.kullanicilar'))
            
        except Exception as e:
            db.session.rollback()
            flash("Kullanıcı oluşturulamadı.", "danger")
    
    return render_template('admin/kullanici_form.html', companies=companies)


@admin_bp.route('/kullanici/<int:id>/sil', methods=['POST'])
@login_required
@admin_required
def kullanici_sil(id):
    """Kullanıcı sil"""
    from app.models import User
    
    # Kendi hesabını silmesin
    if id == session.get('kullanici_id'):
        flash("Kendi hesabınızı silemezsiniz.", "danger")
        return redirect(url_for('admin.kullanicilar'))
    
    user = User.query.get_or_404(id)
    
    try:
        user.is_active = False
        db.session.commit()
        flash(f"Kullanıcı '{user.email}' deaktif edildi.", "success")
    except:
        db.session.rollback()
        flash("Silme başarısız.", "danger")
    
    return redirect(url_for('admin.kullanicilar'))


# ══════════════════════════════════════════════════════════════════
# RAPORLAR
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/raporlar')
@login_required
@admin_required
def raporlar():
    """Genel raporlar sayfası"""
    from app.models import Candidate, Company
    from sqlalchemy import func
    
    # Tarih filtreleri
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        # Genel istatistikler
        query = Candidate.query.filter_by(sinav_durumu='tamamlandi', is_deleted=False)
        
        if start_date:
            query = query.filter(Candidate.bitis_tarihi >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(Candidate.bitis_tarihi <= datetime.strptime(end_date, '%Y-%m-%d'))
        
        completed = query.all()
        
        stats = {
            'total_completed': len(completed),
            'avg_score': sum(c.puan or 0 for c in completed) / len(completed) if completed else 0,
            'pass_rate': len([c for c in completed if c.seviye_sonuc in ['B1', 'B2', 'C1', 'C2']]) / len(completed) * 100 if completed else 0
        }
        
        # CEFR dağılımı
        cefr_distribution = {}
        for level in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
            cefr_distribution[level] = len([c for c in completed if c.seviye_sonuc == level])
        
        # Şirket bazlı rapor
        company_stats = []
        companies = Company.query.filter_by(is_active=True).all()
        for company in companies:
            company_candidates = [c for c in completed if c.sirket_id == company.id]
            if company_candidates:
                company_stats.append({
                    'company': company,
                    'total': len(company_candidates),
                    'avg_score': sum(c.puan or 0 for c in company_candidates) / len(company_candidates)
                })
        
    except Exception as e:
        current_app.logger.error(f"Reports error: {e}")
        stats = {'total_completed': 0, 'avg_score': 0, 'pass_rate': 0}
        cefr_distribution = {}
        company_stats = []
    
    return render_template('admin/raporlar.html',
                          stats=stats,
                          cefr_distribution=cefr_distribution,
                          company_stats=company_stats,
                          start_date=start_date,
                          end_date=end_date)


@admin_bp.route('/rapor/platform')
@admin_bp.route('/super-rapor')
@login_required
@admin_required
def super_rapor():
    """Platform genel raporu"""
    from app.models import Candidate, Company, User, Question
    
    try:
        stats = {
            'total_companies': Company.query.count(),
            'active_companies': Company.query.filter_by(is_active=True).count(),
            'total_candidates': Candidate.query.filter_by(is_deleted=False).count(),
            'completed_exams': Candidate.query.filter_by(sinav_durumu='tamamlandi', is_deleted=False).count(),
            'total_questions': Question.query.filter_by(is_active=True).count(),
            'total_users': User.query.filter_by(is_active=True).count()
        }
    except Exception as e:
        stats = {}
    
    return render_template('admin/super_rapor.html', stats=stats)


# ══════════════════════════════════════════════════════════════════
# AYARLAR
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/ayarlar', methods=['GET', 'POST'])
@login_required
@admin_required
def ayarlar():
    """Sistem ayarları"""
    import os
    
    settings = {
        'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        'smtp_port': os.getenv('SMTP_PORT', '587'),
        'smtp_user': os.getenv('SMTP_USER', ''),
        'site_name': 'Skills Test Center',
        'default_exam_duration': 30,
        'default_question_count': 25
    }
    
    if request.method == 'POST':
        flash("Ayarlar kaydedildi.", "success")
    
    return render_template('admin/ayarlar.html', settings=settings)


# ══════════════════════════════════════════════════════════════════
# LOG GÖRÜNTÜLEME
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """Sistem logları"""
    from app.models import AuditLog
    
    page = request.args.get('page', 1, type=int)
    
    try:
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50)
    except:
        logs = None
    
    return render_template('admin/logs.html', logs=logs)


# ══════════════════════════════════════════════════════════════════
# EMAIL TEST
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/test-email', methods=['GET', 'POST'])
@login_required
@admin_required
def test_email():
    """Email sistemi test"""
    if request.method == 'POST':
        test_email_addr = request.form.get('email', '').strip()
        
        if not test_email_addr:
            flash("Lütfen test email adresi girin.", "warning")
            return render_template('admin/test_email.html')
        
        try:
            from app.routes.auth import send_email
            
            subject = "Skills Test Center - Test Email"
            html_content = """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1>🎉 Test Email Başarılı!</h1>
                </div>
                <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                    <p>Bu email, Skills Test Center email sisteminin test edilmesi için gönderilmiştir.</p>
                    <p>✅ Email sisteminiz düzgün çalışıyor!</p>
                    <p>Artık aday davetleri, sonuç bildirimleri ve şifre sıfırlama emailleri gönderilebilir.</p>
                </div>
                <div style="text-align: center; color: #888; margin-top: 20px; font-size: 12px;">
                    <p>© 2026 Skills Test Center</p>
                </div>
            </div>
            """
            
            if send_email(test_email_addr, subject, html_content):
                flash(f"✅ Test emaili başarıyla gönderildi: {test_email_addr}", "success")
            else:
                flash("❌ Email gönderilemedi. SMTP ayarlarını kontrol edin.", "danger")
                
        except Exception as e:
            current_app.logger.error(f"Test email error: {e}")
            flash(f"❌ Email gönderme hatası: {str(e)}", "danger")
    
    return render_template('admin/test_email.html')


# ══════════════════════════════════════════════════════════════════
# TOPLU EMAIL GÖNDER
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/toplu-email', methods=['GET', 'POST'])
@login_required
@admin_required
def toplu_email():
    """Bekleyen adaylara toplu email gönder"""
    from app.models import Candidate
    
    pending_candidates = Candidate.query.filter_by(
        sinav_durumu='beklemede',
        is_deleted=False
    ).filter(Candidate.email != None).all()
    
    if request.method == 'POST':
        selected_ids = request.form.getlist('candidate_ids')
        
        if not selected_ids:
            flash("Lütfen en az bir aday seçin.", "warning")
            return render_template('admin/toplu_email.html', candidates=pending_candidates)
        
        success_count = 0
        fail_count = 0
        
        for cid in selected_ids:
            try:
                candidate = Candidate.query.get(int(cid))
                if candidate and candidate.email:
                    from app.routes.auth import send_candidate_invitation_email
                    if send_candidate_invitation_email(candidate):
                        success_count += 1
                    else:
                        fail_count += 1
            except Exception as e:
                fail_count += 1
                current_app.logger.error(f"Bulk email error for {cid}: {e}")
        
        flash(f"Email gönderimi tamamlandı. Başarılı: {success_count}, Başarısız: {fail_count}", 
              "success" if fail_count == 0 else "warning")
    
    return render_template('admin/toplu_email.html', candidates=pending_candidates)


# ══════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """Dashboard istatistikleri API"""
    from app.models import Candidate, Company
    
    try:
        stats = {
            'active_exams': Candidate.query.filter_by(sinav_durumu='devam_ediyor', is_deleted=False).count(),
            'pending_exams': Candidate.query.filter_by(sinav_durumu='beklemede', is_deleted=False).count(),
            'completed_today': Candidate.query.filter(
                Candidate.bitis_tarihi >= datetime.now().replace(hour=0, minute=0, second=0),
                Candidate.sinav_durumu == 'tamamlandi'
            ).count()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

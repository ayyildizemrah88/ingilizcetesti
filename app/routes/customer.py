# -*- coding: utf-8 -*-
"""
Customer Routes - Kurumsal Müşteri Dashboard ve Yönetim
YENİ DOSYA - /customer/* ve /musteri/* route'ları için
GitHub: app/routes/customer.py

DÜZELTMELER:
- /musteri/aday-ekle rotası eklendi
- Dashboard'da şirket bilgisi yoksa daha anlamlı sayfa gösteriliyor
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.extensions import db
from datetime import datetime, timedelta

customer_bp = Blueprint('customer', __name__)

# ══════════════════════════════════════════════════════════════
def login_required(f):
    """Require login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def customer_required(f):
    """Only customer or superadmin can access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') not in ['customer', 'superadmin']:
            flash("Bu sayfaya erişim yetkiniz yok.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════════════════════════════
@customer_bp.route('/customer/dashboard')
@customer_bp.route('/musteri/dashboard')
@login_required
@customer_required
def dashboard():
    """Customer dashboard with company statistics - DÜZELTME: Şirket yoksa uygun sayfa göster"""
    from app.models import Candidate, Company

    sirket_id = session.get('sirket_id')

    # DÜZELTME: Şirket ID yoksa bile sayfayı göster, uyarı ile
    company = None
    if sirket_id:
        try:
            company = Company.query.get(sirket_id)
        except:
            company = None

    # Şirket yoksa boş istatistiklerle sayfa göster
    if not company:
        return render_template('customer_dashboard.html',
                              company=None,
                              stats={
                                  'total_candidates': 0,
                                  'active_exams': 0,
                                  'completed_exams': 0,
                                  'pending_exams': 0,
                                  'avg_score': 0,
                                  'remaining_credits': 0
                              },
                              recent_candidates=[],
                              cefr_distribution={'A1': 0, 'A2': 0, 'B1': 0, 'B2': 0, 'C1': 0, 'C2': 0},
                              no_company=True)

    # Get statistics
    stats = {
        'total_candidates': 0,
        'active_exams': 0,
        'completed_exams': 0,
        'pending_exams': 0,
        'avg_score': 0,
        'remaining_credits': company.kredi if company else 0
    }

    try:
        stats['total_candidates'] = Candidate.query.filter_by(
            sirket_id=sirket_id, 
            is_deleted=False
        ).count()

        stats['active_exams'] = Candidate.query.filter_by(
            sirket_id=sirket_id,
            sinav_durumu='devam_ediyor',
            is_deleted=False
        ).count()

        stats['completed_exams'] = Candidate.query.filter_by(
            sirket_id=sirket_id,
            sinav_durumu='tamamlandi',
            is_deleted=False
        ).count()

        stats['pending_exams'] = Candidate.query.filter_by(
            sirket_id=sirket_id,
            sinav_durumu='beklemede',
            is_deleted=False
        ).count()

        # Calculate average score
        from sqlalchemy import func
        avg = db.session.query(func.avg(Candidate.puan)).filter(
            Candidate.sirket_id == sirket_id,
            Candidate.sinav_durumu == 'tamamlandi',
            Candidate.is_deleted == False
        ).scalar()
        stats['avg_score'] = round(avg, 1) if avg else 0

    except Exception as e:
        import logging
        logging.error(f"Customer dashboard stats error: {e}")

    # Get recent candidates
    recent_candidates = []
    try:
        recent_candidates = Candidate.query.filter_by(
            sirket_id=sirket_id,
            is_deleted=False
        ).order_by(Candidate.created_at.desc()).limit(10).all()
    except:
        pass

    # CEFR distribution
    cefr_distribution = {}
    try:
        for level in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
            cefr_distribution[level] = Candidate.query.filter_by(
                sirket_id=sirket_id,
                seviye_sonuc=level,
                sinav_durumu='tamamlandi',
                is_deleted=False
            ).count()
    except:
        cefr_distribution = {'A1': 0, 'A2': 0, 'B1': 0, 'B2': 0, 'C1': 0, 'C2': 0}

    return render_template('customer_dashboard.html',
                          company=company,
                          stats=stats,
                          recent_candidates=recent_candidates,
                          cefr_distribution=cefr_distribution,
                          no_company=False)

# ══════════════════════════════════════════════════════════════
@customer_bp.route('/customer/candidates')
@customer_bp.route('/musteri/adaylar')
@login_required
@customer_required
def candidates():
    """List company candidates"""
    from app.models import Candidate

    sirket_id = session.get('sirket_id')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    candidates = Candidate.query.filter_by(
        sirket_id=sirket_id,
        is_deleted=False
    ).order_by(Candidate.created_at.desc()).paginate(page=page, per_page=per_page)

    return render_template('customer_candidates.html', adaylar=candidates)

# ══════════════════════════════════════════════════════════════
# DÜZELTME: /musteri/aday-ekle rotası eklendi
@customer_bp.route('/customer/candidate/add', methods=['GET', 'POST'])
@customer_bp.route('/musteri/aday/ekle', methods=['GET', 'POST'])
@customer_bp.route('/musteri/aday-ekle', methods=['GET', 'POST'])  # YENİ EKLENEN
@login_required
@customer_required
def add_candidate():
    """Add new candidate for company"""
    from app.models import Candidate, Company
    import string
    import random

    sirket_id = session.get('sirket_id')
    company = Company.query.get(sirket_id) if sirket_id else None

    if not company:
        flash("Şirket bilgisi bulunamadı.", "danger")
        return redirect(url_for('customer.dashboard'))

    # Check credits
    if company.kredi <= 0:
        flash("Yetersiz kredi. Lütfen kredi yükleyin.", "danger")
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
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
            sirket_id=sirket_id
        )

        db.session.add(candidate)

        # Deduct credit
        company.kredi -= 1

        db.session.commit()

        # Send invitation email
        if email:
            try:
                from app.tasks.email_tasks import send_exam_invitation
                send_exam_invitation.delay(candidate.id)
            except:
                pass

        flash(f"Aday eklendi. Giriş Kodu: {giris_kodu}", "success")
        return redirect(url_for('customer.candidates'))

    return render_template('customer_candidate_form.html', company=company)

# ══════════════════════════════════════════════════════════════
@customer_bp.route('/customer/candidate/<int:id>')
@customer_bp.route('/musteri/aday/<int:id>')
@login_required
@customer_required
def candidate_detail(id):
    """View candidate details"""
    from app.models import Candidate

    sirket_id = session.get('sirket_id')
    candidate = Candidate.query.get_or_404(id)

    # Security check
    if candidate.sirket_id != sirket_id:
        flash("Bu adaya erişim yetkiniz yok.", "danger")
        return redirect(url_for('customer.candidates'))

    return render_template('customer_candidate_detail.html', aday=candidate)

# ══════════════════════════════════════════════════════════════
@customer_bp.route('/customer/reports')
@customer_bp.route('/musteri/raporlar')
@login_required
@customer_required
def reports():
    """Company reports and analytics"""
    from app.models import Candidate, Company
    from sqlalchemy import func

    sirket_id = session.get('sirket_id')
    company = Company.query.get(sirket_id) if sirket_id else None

    # Date filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Candidate.query.filter_by(
        sirket_id=sirket_id,
        sinav_durumu='tamamlandi',
        is_deleted=False
    )

    if start_date:
        query = query.filter(Candidate.bitis_tarihi >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Candidate.bitis_tarihi <= datetime.strptime(end_date, '%Y-%m-%d'))

    completed_candidates = query.all()

    # Calculate stats
    stats = {
        'total': len(completed_candidates),
        'avg_score': 0,
        'pass_rate': 0  # B1 and above
    }

    if completed_candidates:
        stats['avg_score'] = sum(c.puan or 0 for c in completed_candidates) / len(completed_candidates)
        passing = len([c for c in completed_candidates if c.seviye_sonuc in ['B1', 'B2', 'C1', 'C2']])
        stats['pass_rate'] = round(passing / len(completed_candidates) * 100, 1)

    # CEFR distribution
    cefr_data = {}
    for level in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
        cefr_data[level] = len([c for c in completed_candidates if c.seviye_sonuc == level])

    return render_template('customer_reports.html',
                          company=company,
                          stats=stats,
                          cefr_data=cefr_data,
                          candidates=completed_candidates[:50])

# ══════════════════════════════════════════════════════════════
@customer_bp.route('/customer/results')
@customer_bp.route('/candidate/results')
@login_required
@customer_required
def results():
    """View all completed exam results"""
    from app.models import Candidate

    sirket_id = session.get('sirket_id')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    results = Candidate.query.filter_by(
        sirket_id=sirket_id,
        sinav_durumu='tamamlandi',
        is_deleted=False
    ).order_by(Candidate.bitis_tarihi.desc()).paginate(page=page, per_page=per_page)

    return render_template('customer_results.html', results=results)

# ══════════════════════════════════════════════════════════════
@customer_bp.route('/customer/export')
@customer_bp.route('/musteri/export')
@login_required
@customer_required
def export_data():
    """Export candidate data as CSV"""
    from app.models import Candidate
    import csv
    from io import StringIO
    from flask import Response

    sirket_id = session.get('sirket_id')

    candidates = Candidate.query.filter_by(
        sirket_id=sirket_id,
        sinav_durumu='tamamlandi',
        is_deleted=False
    ).all()

    # Create CSV
    si = StringIO()
    writer = csv.writer(si)

    # Header
    writer.writerow(['Ad Soyad', 'Email', 'Puan', 'Seviye', 'Tamamlanma Tarihi'])

    # Data
    for c in candidates:
        writer.writerow([
            c.ad_soyad,
            c.email,
            c.puan,
            c.seviye_sonuc,
            c.bitis_tarihi.strftime('%Y-%m-%d %H:%M') if c.bitis_tarihi else ''
        ])

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sinav_sonuclari.csv'}
    )

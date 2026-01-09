# -*- coding: utf-8 -*-
"""
Aday Routes - Türkçe URL'ler için ayrı blueprint
/aday/* rotaları için

GitHub: app/routes/aday.py
YENİ DOSYA
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from app.extensions import db

aday_bp = Blueprint('aday', __name__, url_prefix='/aday')


@aday_bp.route('/dashboard')
def dashboard():
    """Aday dashboard - Türkçe URL"""
    from app.models import Candidate

    # Get candidate ID from session
    candidate_id = session.get('candidate_id') or session.get('aday_id')

    # If no session, redirect to exam entry
    if not candidate_id:
        flash("Lütfen giriş yapın.", "warning")
        try:
            return redirect(url_for('candidate_auth.sinav_giris'))
        except:
            try:
                return redirect(url_for('auth.sinav_giris'))
            except:
                return redirect(url_for('auth.login'))

    # Try to get candidate from database
    try:
        candidate = Candidate.query.get(candidate_id)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Aday dashboard query failed: {e}")
        session.clear()
        flash("Bir hata oluştu. Lütfen tekrar giriş yapın.", "danger")
        try:
            return redirect(url_for('candidate_auth.sinav_giris'))
        except:
            return redirect(url_for('auth.login'))

    # If candidate not found, clear session
    if not candidate:
        session.clear()
        flash("Aday bulunamadı. Lütfen tekrar giriş yapın.", "warning")
        try:
            return redirect(url_for('candidate_auth.sinav_giris'))
        except:
            return redirect(url_for('auth.login'))

    return render_template('candidate_dashboard.html', aday=candidate)


@aday_bp.route('/gecmis')
def gecmis():
    """Sınav geçmişi - Türkçe URL"""
    from app.models import Candidate

    email = request.args.get('email') or session.get('candidate_email')
    if not email:
        return render_template('score_history.html', exams=[], avg_score=0, best_level='N/A', improvement=0)

    try:
        exams = Candidate.query.filter_by(
            email=email,
            sinav_durumu='tamamlandi',
            is_practice=False
        ).order_by(Candidate.bitis_tarihi.desc()).all()
    except Exception as e:
        db.session.rollback()
        exams = []

    avg_score = sum(e.puan or 0 for e in exams) / len(exams) if exams else 0

    level_order = {'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2': 6}
    best_level = 'N/A'
    if exams:
        exams_with_level = [e for e in exams if e.seviye_sonuc]
        if exams_with_level:
            best_level = max(exams_with_level, key=lambda e: level_order.get(e.seviye_sonuc, 0)).seviye_sonuc

    improvement = 0
    if len(exams) >= 2:
        improvement = (exams[0].puan or 0) - (exams[1].puan or 0)

    return render_template('score_history.html',
                          exams=exams,
                          avg_score=avg_score,
                          best_level=best_level,
                          improvement=improvement)


# ==================== YÖNLENDİRME ROUTE'LARI ====================
# /aday/sinav ve /aday/sonuc istekleri /exam/* route'larına yönlendirilir

@aday_bp.route('/sinav')
def sinav():
    """Sınav sayfası - /exam/sinav'a yönlendir"""
    return redirect(url_for('exam.sinav'))


@aday_bp.route('/sinav-bitti')
def sinav_bitti():
    """Sınav bitti sayfası - /exam/sinav_bitti'ye yönlendir"""
    return redirect(url_for('exam.sinav_bitti'))


@aday_bp.route('/sonuc')
def sonuc():
    """Sonuç sayfası - session'daki aday bilgisine göre yönlendir"""
    from app.models import Candidate
    
    # Session'dan aday id veya giris kodu al
    aday_id = session.get('aday_id') or session.get('candidate_id')
    
    if aday_id:
        try:
            candidate = Candidate.query.get(aday_id)
            if candidate and candidate.giris_kodu:
                return redirect(url_for('exam.sonuc', giris_kodu=candidate.giris_kodu))
        except:
            pass
    
    # Aday bulunamazsa giriş sayfasına yönlendir
    flash("Sonuç görüntülemek için giriş yapmalısınız.", "warning")
    try:
        return redirect(url_for('candidate_auth.sinav_giris'))
    except:
        return redirect(url_for('auth.sinav_giris'))


@aday_bp.route('/sonuc/<giris_kodu>')
def sonuc_with_code(giris_kodu):
    """Giriş kodu ile sonuç görüntüleme - /exam/sonuc/<giris_kodu>'ya yönlendir"""
    return redirect(url_for('exam.sonuc', giris_kodu=giris_kodu))


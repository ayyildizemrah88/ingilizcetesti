# -*- coding: utf-8 -*-
"""
Candidate Authentication
TC Kimlik + Unique Code based login for candidates
FIXED: Field names aligned with Candidate model
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash

from app.extensions import db
from app.models.candidate import Candidate

candidate_auth_bp = Blueprint('candidate_auth', __name__)


def generate_exam_code(length=8):
    """Generate a unique exam access code."""
    return secrets.token_urlsafe(length).upper()[:length]


def hash_tc_kimlik(tc_kimlik):
    """Hash TC Kimlik for secure storage."""
    return hashlib.sha256(tc_kimlik.encode()).hexdigest()


def validate_tc_kimlik(tc_kimlik):
    """
    Validate Turkish TC Kimlik number.
    Rules:
    - Exactly 11 digits
    - First digit cannot be 0
    - Checksum validation (algorithm)
    """
    if not tc_kimlik or len(tc_kimlik) != 11:
        return False

    if not tc_kimlik.isdigit():
        return False

    if tc_kimlik[0] == '0':
        return False

    # TC Kimlik checksum algorithm
    try:
        digits = [int(d) for d in tc_kimlik]

        # 10th digit check
        odd_sum = sum(digits[0:9:2])  # 1, 3, 5, 7, 9th digits
        even_sum = sum(digits[1:8:2])  # 2, 4, 6, 8th digits
        digit_10 = (odd_sum * 7 - even_sum) % 10

        if digit_10 != digits[9]:
            return False

        # 11th digit check
        total = sum(digits[0:10])
        digit_11 = total % 10

        if digit_11 != digits[10]:
            return False

        return True
    except:
        return False


@candidate_auth_bp.route('/sinav-giris', methods=['GET', 'POST'])
def sinav_giris():
    """
    Candidate exam login page.
    Requires TC Kimlik + Unique Exam Code (giris_kodu).
    FIXED: Using correct field names from Candidate model
    """
    if request.method == 'POST':
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        exam_code = request.form.get('exam_code', '').strip().upper()

        errors = []

        # Validate TC Kimlik
        if not tc_kimlik:
            errors.append('TC Kimlik numarası gereklidir.')
        elif not validate_tc_kimlik(tc_kimlik):
            errors.append('Geçersiz TC Kimlik numarası.')

        # Validate exam code
        if not exam_code:
            errors.append('Sınav kodu gereklidir.')
        elif len(exam_code) < 6:
            errors.append('Sınav kodu en az 6 karakter olmalıdır.')

        if errors:
            return render_template('sinav_giris_tc.html', errors=errors)

        # Find candidate by TC Kimlik and giris_kodu (exam code)
        # FIXED: Using giris_kodu instead of exam_code, removed aktif field
        candidate = Candidate.query.filter_by(
            tc_kimlik=tc_kimlik,
            giris_kodu=exam_code,
            is_deleted=False
        ).first()

        if not candidate:
            errors.append('TC Kimlik veya sınav kodu hatalı. Lütfen kontrol ediniz.')
            return render_template('sinav_giris_tc.html', errors=errors)

        # Check exam status - FIXED: using sinav_durumu instead of durum
        if candidate.sinav_durumu == 'tamamlandi':
            errors.append('Bu sınav daha önce tamamlanmış. Yeniden giriş yapamazsınız.')
            return render_template('sinav_giris_tc.html', errors=errors)

        # Success - create session
        session['aday_id'] = candidate.id  # Use aday_id for consistency with exam.py
        session['candidate_id'] = candidate.id
        session['candidate_name'] = candidate.ad_soyad
        session['sirket_id'] = candidate.sirket_id  # FIXED: firma_id -> sirket_id
        session['exam_status'] = candidate.sinav_durumu  # FIXED: durum -> sinav_durumu
        session['login_time'] = datetime.utcnow().isoformat()

        db.session.commit()

        # Redirect based on status - FIXED: using sinav_durumu
        if candidate.sinav_durumu == 'beklemede':
            return redirect(url_for('candidate.tutorial'))
        elif candidate.sinav_durumu == 'devam_ediyor':
            return redirect(url_for('exam.sinav'))
        else:
            return redirect(url_for('candidate.dashboard'))

    return render_template('sinav_giris_tc.html')


@candidate_auth_bp.route('/api/candidate/generate-code', methods=['POST'])
def generate_candidate_code():
    """
    Generate a new exam code for a candidate.
    Called by admin when creating/resetting candidate access.
    FIXED: Using giris_kodu instead of exam_code
    """
    data = request.get_json()
    candidate_id = data.get('candidate_id')

    candidate = Candidate.query.get_or_404(candidate_id)

    # Generate new code - FIXED: using giris_kodu
    import string
    import random
    new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    candidate.giris_kodu = new_code

    db.session.commit()

    return jsonify({
        'success': True,
        'exam_code': new_code,
        'candidate_email': candidate.email
    })


@candidate_auth_bp.route('/api/candidate/verify-tc', methods=['POST'])
def verify_tc_kimlik():
    """API endpoint to verify TC Kimlik format."""
    data = request.get_json()
    tc_kimlik = data.get('tc_kimlik', '')

    is_valid = validate_tc_kimlik(tc_kimlik)

    return jsonify({
        'valid': is_valid,
        'message': 'Geçerli TC Kimlik' if is_valid else 'Geçersiz TC Kimlik numarası'
    })


@candidate_auth_bp.route('/sinav-cikis', methods=['POST'])
def sinav_cikis():
    """Logout candidate from exam session."""
    candidate_id = session.get('candidate_id')

    if candidate_id:
        # Log the logout
        candidate = Candidate.query.get(candidate_id)
        if candidate:
            # Don't end exam on logout, just clear session
            pass

    # Clear session
    session.pop('aday_id', None)
    session.pop('candidate_id', None)
    session.pop('candidate_name', None)
    session.pop('sirket_id', None)
    session.pop('exam_status', None)

    flash('Oturumunuz sonlandırıldı.', 'info')
    return redirect(url_for('candidate_auth.sinav_giris'))

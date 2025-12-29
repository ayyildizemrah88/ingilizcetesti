# -*- coding: utf-8 -*-
"""
══════════════════════════════════════════════════════════════
INTERNATIONAL FEATURES MODULE - DÜZELTİLMİŞ VERSİYON
══════════════════════════════════════════════════════════════
DEĞİŞİKLİK: Blueprint now registered with '/international' prefix
so accessibility route works at /international/accessibility/toggle

Also, alternative solution: Keep original and change base.html URL to /accessibility/toggle
This file provides BOTH options - see register_international_features function
"""

import os
import io
import json
import base64
import hashlib
import datetime
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for, 
                   session, jsonify, flash, send_file, current_app)

# Create Blueprint
international_bp = Blueprint('international', __name__)

# ══════════════════════════════════════════════════════════════
def get_db_connection():
    """Import from main app - this will be overridden when registered"""
    from app import get_db_connection as app_get_db
    return app_get_db()

def check_role(roles):
    """Import from main app - role check decorator"""
    from app import check_role as app_check_role
    return app_check_role(roles)

# ══════════════════════════════════════════════════════════════
# ACCESSIBILITY ROUTES
# ══════════════════════════════════════════════════════════════
@international_bp.route('/accessibility/toggle', methods=['POST'])
def toggle_accessibility():
    """Toggle accessibility features"""
    data = request.get_json() or {}
    feature = data.get('feature', '')

    accessibility = session.get('accessibility', {
        'high_contrast': False,
        'large_text': False,
        'reduced_motion': False,
        'colorblind_mode': None,
        'dyslexia_friendly': False
    })

    if feature == 'high_contrast':
        accessibility['high_contrast'] = not accessibility['high_contrast']
    elif feature == 'large_text':
        accessibility['large_text'] = not accessibility['large_text']
    elif feature == 'reduced_motion':
        accessibility['reduced_motion'] = not accessibility['reduced_motion']
    elif feature == 'dyslexia_friendly':
        accessibility['dyslexia_friendly'] = not accessibility['dyslexia_friendly']
    elif feature.startswith('colorblind_'):
        mode = feature.replace('colorblind_', '')
        if accessibility['colorblind_mode'] == mode:
            accessibility['colorblind_mode'] = None
        else:
            accessibility['colorblind_mode'] = mode

    session['accessibility'] = accessibility

    return jsonify(accessibility)

@international_bp.route('/accessibility/settings')
def accessibility_settings():
    """Get current accessibility settings"""
    return jsonify(session.get('accessibility', {}))

# ══════════════════════════════════════════════════════════════
# LISTENING EXAM ROUTES
# ══════════════════════════════════════════════════════════════
@international_bp.route('/exam/listening/<int:audio_id>')
def sinav_listening(audio_id):
    """Listening comprehension exam page"""
    aday_id = session.get('aday_id')
    if not aday_id:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for('sinav_giris'))

    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None

    conn, is_pg = get_db_connection()
    if is_pg and RealDictCursor:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()

    # Get audio
    q = "SELECT * FROM listening_audio WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (audio_id,))
    audio = c.fetchone()

    if not audio:
        flash("Dinleme kaydı bulunamadı.", "danger")
        return redirect(url_for('sinav'))

    # Get questions for this audio
    q = "SELECT * FROM listening_questions WHERE audio_id=? ORDER BY soru_sirasi"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (audio_id,))
    questions = c.fetchall()

    # Get play count from session
    plays_key = f'listening_plays_{audio_id}'
    plays_used = session.get(plays_key, 0)
    max_plays = 2  # Standard: 2 plays allowed

    # Get remaining time
    remaining_time = session.get('listening_time', 30 * 60)  # 30 minutes default

    conn.close()

    if is_pg:
        audio_dict = dict(audio)
        questions_list = [dict(q) for q in questions]
    else:
        audio_dict = {
            'id': audio[0],
            'title': audio[1],
            'audio_url': audio[2],
            'transcript': audio[3],
            'duration_seconds': audio[4],
            'difficulty': audio[5]
        }
        questions_list = []
        for q in questions:
            questions_list.append({
                'id': q[0],
                'soru_metni': q[2],
                'secenek_a': q[3],
                'secenek_b': q[4],
                'secenek_c': q[5],
                'secenek_d': q[6],
                'dogru_cevap': q[7]
            })

    return render_template('listening_exam.html',
                          audio=audio_dict,
                          questions=questions_list,
                          plays_used=plays_used,
                          max_plays=max_plays,
                          remaining_time=remaining_time,
                          current_question=1,
                          total_questions=len(questions_list))

# ══════════════════════════════════════════════════════════════
# CERTIFICATE ROUTES
# ══════════════════════════════════════════════════════════════
def generate_qr_code(data):
    """Generate QR code as base64 string"""
    try:
        import qrcode
        from PIL import Image

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except ImportError:
        return None

@international_bp.route('/cert/verify/<cert_hash>')
def cert_verify(cert_hash):
    """Public certificate verification page"""
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None

    conn, is_pg = get_db_connection()
    if is_pg and RealDictCursor:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()

    q = """SELECT ad_soyad, puan, seviye_sonuc, bitis_tarihi, band_score,
                  ielts_reading, ielts_writing, ielts_speaking, ielts_listening
           FROM adaylar WHERE certificate_hash=?"""
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (cert_hash,))
    cert = c.fetchone()
    conn.close()

    certificate = None
    qr_image = None

    if cert:
        if is_pg:
            certificate = dict(cert)
        else:
            certificate = {
                'ad_soyad': cert[0],
                'puan': cert[1],
                'seviye_sonuc': cert[2],
                'bitis_tarihi': cert[3],
                'band_score': cert[4],
                'ielts_reading': cert[5],
                'ielts_writing': cert[6],
                'ielts_speaking': cert[7],
                'ielts_listening': cert[8]
            }

        certificate['certificate_hash'] = cert_hash

        # Check expiry (2 years validity)
        if certificate['bitis_tarihi']:
            try:
                issue_date = datetime.datetime.strptime(str(certificate['bitis_tarihi'])[:10], '%Y-%m-%d')
                expiry_date = issue_date + datetime.timedelta(days=730)  # 2 years
                certificate['expiry_date'] = expiry_date.strftime('%Y-%m-%d')
                certificate['is_expired'] = datetime.datetime.now() > expiry_date
                certificate['validity_years'] = 2
            except:
                certificate['is_expired'] = False

        # Generate QR code
        verify_url = url_for('international.cert_verify', cert_hash=cert_hash, _external=True)
        qr_image = generate_qr_code(verify_url)

    return render_template('cert_verify.html',
                          certificate=certificate,
                          qr_image=qr_image,
                          verified_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# ══════════════════════════════════════════════════════════════
# REGISTER FUNCTION - DÜZELTİLDİ
# ══════════════════════════════════════════════════════════════
def register_international_features(app):
    """
    Register this blueprint with the Flask app
    
    DEĞİŞİKLİK: Blueprint artık '/international' prefix ile register ediliyor
    Bu sayede /international/accessibility/toggle çalışacak
    """
    # DÜZELTİLDİ: url_prefix='/international' eklendi
    app.register_blueprint(international_bp, url_prefix='/international')

    # Add accessibility context processor
    @app.context_processor
    def inject_accessibility():
        return {
            'accessibility': session.get('accessibility', {
                'high_contrast': False,
                'large_text': False,
                'reduced_motion': False,
                'colorblind_mode': None,
                'dyslexia_friendly': False
            })
        }

    return app

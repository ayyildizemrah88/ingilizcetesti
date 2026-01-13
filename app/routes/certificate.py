# -*- coding: utf-8 -*-
"""
Certificate Routes - Download and verify certificates
FIXED: Added /sertifika/generate route
GitHub: app/routes/certificate.py
"""
import os
from functools import wraps
from flask import Blueprint, send_file, jsonify, render_template, abort, current_app, request, redirect, url_for, flash, session
from app.extensions import db
from app.models.candidate import Candidate

# FIXED: Changed url_prefix to '/sertifika' for Turkish URL structure
certificate_bp = Blueprint('certificate', __name__, url_prefix='/sertifika')


def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════
# CERTIFICATE DOWNLOAD
# ══════════════════════════════════════════════════════════════
@certificate_bp.route('/download/<int:candidate_id>')
def download_certificate(candidate_id):
    """Download PDF certificate for a candidate."""
    candidate = Candidate.query.get_or_404(candidate_id)

    # Check exam status
    exam_status = getattr(candidate, 'durum', None) or getattr(candidate, 'sinav_durumu', None)
    if exam_status != 'tamamlandi':
        return jsonify({'error': 'Sınav henüz tamamlanmamış'}), 400

    try:
        from app.utils.certificate_generator import CertificateGenerator

        generator = CertificateGenerator()

        candidate_data = {
            'id': candidate.id,
            'ad_soyad': candidate.ad_soyad,
            'puan': candidate.puan or 0,
            'sinav_bitis': candidate.sinav_bitis or candidate.bitis_tarihi,
            'skills': {
                'grammar': getattr(candidate, 'grammar_puan', 0) or getattr(candidate, 'p_grammar', 0) or 0,
                'vocabulary': getattr(candidate, 'vocabulary_puan', 0) or getattr(candidate, 'p_vocabulary', 0) or 0,
                'reading': getattr(candidate, 'reading_puan', 0) or getattr(candidate, 'p_reading', 0) or 0,
                'listening': getattr(candidate, 'listening_puan', 0) or getattr(candidate, 'p_listening', 0) or 0,
                'writing': getattr(candidate, 'writing_puan', 0) or getattr(candidate, 'p_writing', 0) or 0,
                'speaking': getattr(candidate, 'speaking_puan', 0) or getattr(candidate, 'p_speaking', 0) or 0
            }
        }

        base_url = os.getenv('APP_BASE_URL', 'https://skillstestcenter.com')
        filepath, cert_hash = generator.create_certificate(candidate_data, base_url)

        if not candidate.certificate_hash:
            candidate.certificate_hash = cert_hash
            db.session.commit()

        filename = f"Certificate_{candidate.ad_soyad.replace(' ', '_')}_{cert_hash}.pdf"

        return send_file(
            filepath,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except ImportError as e:
        current_app.logger.error(f"Certificate generation dependencies missing: {e}")
        return jsonify({'error': 'pip install reportlab qrcode pillow'}), 500
    except Exception as e:
        current_app.logger.error(f"Certificate generation error: {e}")
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# CERTIFICATE VERIFICATION
# ══════════════════════════════════════════════════════════════
@certificate_bp.route('/verify', methods=['GET', 'POST'])
def verify_form():
    """Certificate verification form page - allows users to input hash."""
    if request.method == 'POST':
        cert_hash = request.form.get('cert_hash', '').strip()
        if cert_hash:
            return redirect(url_for('certificate.verify_certificate', cert_hash=cert_hash))
        flash("Lütfen sertifika kodunu girin.", "warning")
    return render_template('cert_verify_form.html')


@certificate_bp.route('/verify/<cert_hash>')
def verify_certificate(cert_hash):
    """Verify a certificate by its hash."""
    candidate = Candidate.query.filter_by(certificate_hash=cert_hash).first()

    if not candidate:
        return render_template('cert_verify.html', valid=False, cert_hash=cert_hash)

    return render_template('cert_verify.html', 
        valid=True,
        cert_hash=cert_hash,
        candidate_name=candidate.ad_soyad,
        score=candidate.puan,
        cefr_level=candidate.cefr_seviye or candidate.seviye_sonuc,
        exam_date=candidate.sinav_bitis or candidate.bitis_tarihi,
        company=candidate.company.ad if candidate.company else None
    )


# ══════════════════════════════════════════════════════════════
# CERTIFICATE GENERATION PAGE - FIXED: Was returning 404
# ══════════════════════════════════════════════════════════════
@certificate_bp.route('/generate', methods=['GET'])
@login_required
def generate_page():
    """Certificate generation page - shows candidates eligible for certificates"""
    sirket_id = session.get('sirket_id')
    rol = session.get('rol')
    
    # Get completed candidates without certificates
    query = Candidate.query.filter(
        Candidate.sinav_durumu == 'tamamlandi',
        Candidate.is_deleted == False
    )
    
    if sirket_id and rol != 'superadmin':
        query = query.filter_by(sirket_id=sirket_id)
    
    candidates = query.order_by(Candidate.bitis_tarihi.desc()).limit(50).all()
    
    # Separate candidates with and without certificates
    with_cert = [c for c in candidates if c.certificate_hash]
    without_cert = [c for c in candidates if not c.certificate_hash]
    
    return render_template('cert_generate.html',
                          candidates_with_cert=with_cert,
                          candidates_without_cert=without_cert)


@certificate_bp.route('/generate/<int:candidate_id>', methods=['POST'])
@login_required
def generate_certificate(candidate_id):
    """Generate certificate for a candidate"""
    import hashlib
    from datetime import datetime
    
    candidate = Candidate.query.get_or_404(candidate_id)
    sirket_id = session.get('sirket_id')
    rol = session.get('rol')
    
    # Security check
    if rol not in ['super_admin', 'superadmin']:
        if sirket_id and candidate.sirket_id != sirket_id:
            return jsonify({'success': False, 'message': 'Yetkiniz yok'}), 403
    
    # Check exam completed
    if candidate.sinav_durumu != 'tamamlandi':
        return jsonify({'success': False, 'message': 'Sınav tamamlanmamış'}), 400
    
    # Generate certificate hash if not exists
    if not candidate.certificate_hash:
        cert_data = f"{candidate.id}-{candidate.ad_soyad}-{datetime.utcnow().isoformat()}"
        candidate.certificate_hash = hashlib.sha256(cert_data.encode()).hexdigest()[:16]
        db.session.commit()
    
    return jsonify({
        'success': True,
        'certificate_hash': candidate.certificate_hash,
        'download_url': url_for('certificate.download_certificate', candidate_id=candidate_id, _external=True),
        'verify_url': url_for('certificate.verify_certificate', cert_hash=candidate.certificate_hash, _external=True)
    })


# ══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════
@certificate_bp.route('/api/generate/<int:candidate_id>', methods=['POST'])
def api_generate_certificate(candidate_id):
    """API endpoint to generate certificate."""
    candidate = Candidate.query.get_or_404(candidate_id)

    # Check exam status
    exam_status = getattr(candidate, 'durum', None) or getattr(candidate, 'sinav_durumu', None)
    if exam_status != 'tamamlandi':
        return jsonify({'error': 'Sınav tamamlanmamış'}), 400

    try:
        from app.utils.certificate_generator import CertificateGenerator

        generator = CertificateGenerator()

        candidate_data = {
            'id': candidate.id,
            'ad_soyad': candidate.ad_soyad,
            'puan': candidate.puan or 0,
            'cefr_seviye': candidate.cefr_seviye or candidate.seviye_sonuc or 'B1',
            'sinav_bitis': candidate.sinav_bitis or candidate.bitis_tarihi,
            'skills': {
                'grammar': getattr(candidate, 'grammar_puan', 0) or getattr(candidate, 'p_grammar', 0) or 0,
                'vocabulary': getattr(candidate, 'vocabulary_puan', 0) or getattr(candidate, 'p_vocabulary', 0) or 0,
                'reading': getattr(candidate, 'reading_puan', 0) or getattr(candidate, 'p_reading', 0) or 0,
                'listening': getattr(candidate, 'listening_puan', 0) or getattr(candidate, 'p_listening', 0) or 0,
                'writing': getattr(candidate, 'writing_puan', 0) or getattr(candidate, 'p_writing', 0) or 0,
                'speaking': getattr(candidate, 'speaking_puan', 0) or getattr(candidate, 'p_speaking', 0) or 0
            }
        }

        base_url = os.getenv('APP_BASE_URL', 'https://skillstestcenter.com')
        filepath, cert_hash = generator.create_certificate(candidate_data, base_url)

        if not candidate.certificate_hash:
            candidate.certificate_hash = cert_hash
            db.session.commit()

        return jsonify({
            'success': True,
            'certificate_hash': cert_hash,
            'download_url': url_for('certificate.download_certificate', candidate_id=candidate_id, _external=True),
            'verify_url': url_for('certificate.verify_certificate', cert_hash=cert_hash, _external=True)
        })

    except ImportError as e:
        current_app.logger.error(f"Certificate generation dependencies missing: {e}")
        return jsonify({'error': 'Gerekli paketler eksik: pip install reportlab qrcode pillow'}), 500
    except Exception as e:
        current_app.logger.error(f"Certificate generation error: {e}")
        return jsonify({'error': str(e)}), 500


@certificate_bp.route('/api/verify/<cert_hash>')
def api_verify_certificate(cert_hash):
    """API endpoint to verify a certificate"""
    candidate = Candidate.query.filter_by(certificate_hash=cert_hash).first()
    
    if not candidate:
        return jsonify({
            'valid': False,
            'message': 'Sertifika bulunamadı'
        })
    
    return jsonify({
        'valid': True,
        'candidate_name': candidate.ad_soyad,
        'score': candidate.puan,
        'cefr_level': candidate.cefr_seviye or candidate.seviye_sonuc,
        'exam_date': (candidate.sinav_bitis or candidate.bitis_tarihi).isoformat() if (candidate.sinav_bitis or candidate.bitis_tarihi) else None,
        'certificate_hash': cert_hash
    })

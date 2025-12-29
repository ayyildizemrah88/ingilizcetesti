# -*- coding: utf-8 -*-
"""
Certificate Routes - Download and verify certificates
FIXED: Added /sertifika prefix for Turkish URL structure
"""
import os
from flask import Blueprint, send_file, jsonify, render_template, abort, current_app

from app.extensions import db
from app.models.candidate import Candidate

# FIXED: Changed url_prefix to '/sertifika' for Turkish URL structure
certificate_bp = Blueprint('certificate', __name__, url_prefix='/sertifika')


@certificate_bp.route('/download/<int:candidate_id>')
def download_certificate(candidate_id):
    """Download PDF certificate for a candidate."""
    candidate = Candidate.query.get_or_404(candidate_id)

    # Check exam status - handle both 'durum' and 'sinav_durumu' fields
    exam_status = getattr(candidate, 'durum', None) or getattr(candidate, 'sinav_durumu', None)
    if exam_status != 'tamamlandi':
        return jsonify({'error': 'Sinav henuz tamamlanmamis'}), 400

    try:
        from app.utils.certificate_generator import CertificateGenerator

        generator = CertificateGenerator()

        candidate_data = {
            'id': candidate.id,
            'ad_soyad': candidate.ad_soyad,
            'puan': candidate.toplam_puan or candidate.puan or 0,
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
        score=candidate.toplam_puan or candidate.puan,
        cefr_level=candidate.cefr_seviye or candidate.seviye_sonuc,
        exam_date=candidate.sinav_bitis or candidate.bitis_tarihi,
        company=candidate.company.ad if candidate.company else None
    )


@certificate_bp.route('/api/generate/<int:candidate_id>', methods=['POST'])
def api_generate_certificate(candidate_id):
    """API endpoint to generate certificate."""
    candidate = Candidate.query.get_or_404(candidate_id)

    # Check exam status
    exam_status = getattr(candidate, 'durum', None) or getattr(candidate, 'sinav_durumu', None)
    if exam_status != 'tamamlandi':
        return jsonify({'error': 'Sinav tamamlanmamis'}), 400

    try:
        from app.utils.certificate_generator import CertificateGenerator

        generator = CertificateGenerator()

        candidate_data = {
            'id': candidate.id,
            'ad_soyad': candidate.ad_soyad,
            'puan': candidate.toplam_puan or candidate.puan or 0,
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

        candidate.certificate_hash = cert_hash
        db.session.commit()

        return jsonify({
            'success': True,
            'certificate_hash': cert_hash,
            'download_url': f'/sertifika/download/{candidate_id}',
            'verify_url': f'{base_url}/sertifika/verify/{cert_hash}'
        })

    except Exception as e:
        current_app.logger.error(f"API certificate generation error: {e}")
        return jsonify({'error': str(e)}), 500

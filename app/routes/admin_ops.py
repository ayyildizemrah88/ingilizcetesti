# -*- coding: utf-8 -*-
"""
Admin Operations Routes
SuperAdmin-only operations for managing exams and users
"""
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, session

from app.extensions import db
from app.models.candidate import Candidate
from app.models.admin import AuditLog

admin_ops_bp = Blueprint('admin_ops', __name__)


def superadmin_required(f):
    """Decorator to require superadmin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('rol') != 'superadmin':
            flash('Bu işlem için SuperAdmin yetkisi gereklidir.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def log_admin_action(action, target_type, target_id, details=None):
    """Log admin actions for audit trail."""
    try:
        log = AuditLog(
            user_id=session.get('user_id'),
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")


# ====================
# EXAM RESET FEATURE
# ====================

@admin_ops_bp.route('/admin/candidate/<int:candidate_id>/reset-exam', methods=['POST'])
@superadmin_required
def reset_candidate_exam(candidate_id):
    """
    Reset a candidate's exam status to allow retake.
    SuperAdmin only operation.
    """
    candidate = Candidate.query.get_or_404(candidate_id)
    
    # Get reset reason
    reason = request.form.get('reason', 'Admin tarafından sıfırlandı')
    
    # Store old values for audit
    old_status = candidate.durum
    old_score = candidate.toplam_puan
    
    # Reset exam fields
    candidate.durum = 'beklemede'
    candidate.sinav_baslama = None
    candidate.sinav_bitis = None
    candidate.toplam_puan = None
    candidate.cefr_seviye = None
    candidate.grammar_puan = None
    candidate.vocabulary_puan = None
    candidate.reading_puan = None
    candidate.listening_puan = None
    candidate.speaking_puan = None
    candidate.writing_puan = None
    candidate.is_paused = False
    candidate.pause_count = 0
    
    db.session.commit()
    
    # Log the action
    log_admin_action(
        action='exam_reset',
        target_type='candidate',
        target_id=candidate_id,
        details={
            'reason': reason,
            'old_status': old_status,
            'old_score': old_score,
            'reset_by': session.get('user_id')
        }
    )
    
    flash(f'{candidate.ad_soyad} adlı adayın sınav hakkı sıfırlandı.', 'success')
    return redirect(url_for('admin.aday_detay', id=candidate_id))


@admin_ops_bp.route('/api/admin/candidate/<int:candidate_id>/reset-exam', methods=['POST'])
@superadmin_required
def api_reset_candidate_exam(candidate_id):
    """API endpoint for resetting exam."""
    candidate = Candidate.query.get_or_404(candidate_id)
    
    data = request.get_json() or {}
    reason = data.get('reason', 'API üzerinden sıfırlandı')
    
    # Store old values
    old_data = {
        'status': candidate.durum,
        'score': candidate.toplam_puan,
        'cefr': candidate.cefr_seviye
    }
    
    # Reset
    candidate.durum = 'beklemede'
    candidate.sinav_baslama = None
    candidate.sinav_bitis = None
    candidate.toplam_puan = None
    candidate.cefr_seviye = None
    candidate.grammar_puan = None
    candidate.vocabulary_puan = None
    candidate.reading_puan = None
    candidate.listening_puan = None
    candidate.speaking_puan = None
    candidate.writing_puan = None
    candidate.is_paused = False
    candidate.pause_count = 0
    
    db.session.commit()
    
    log_admin_action(
        action='exam_reset',
        target_type='candidate',
        target_id=candidate_id,
        details={'reason': reason, 'old_data': old_data}
    )
    
    return jsonify({
        'success': True,
        'message': f'{candidate.ad_soyad} adlı adayın sınav hakkı sıfırlandı.',
        'candidate_id': candidate_id
    })


# ====================
# BULK OPERATIONS
# ====================

@admin_ops_bp.route('/api/admin/candidates/bulk-reset', methods=['POST'])
@superadmin_required
def bulk_reset_exams():
    """Reset multiple candidates' exams at once."""
    data = request.get_json()
    candidate_ids = data.get('candidate_ids', [])
    reason = data.get('reason', 'Toplu sıfırlama')
    
    if not candidate_ids:
        return jsonify({'success': False, 'error': 'Aday seçilmedi'}), 400
    
    reset_count = 0
    for cid in candidate_ids:
        candidate = Candidate.query.get(cid)
        if candidate:
            candidate.durum = 'beklemede'
            candidate.sinav_baslama = None
            candidate.sinav_bitis = None
            candidate.toplam_puan = None
            candidate.cefr_seviye = None
            reset_count += 1
    
    db.session.commit()
    
    log_admin_action(
        action='bulk_exam_reset',
        target_type='candidates',
        target_id=None,
        details={'candidate_ids': candidate_ids, 'reason': reason, 'count': reset_count}
    )
    
    return jsonify({
        'success': True,
        'reset_count': reset_count,
        'message': f'{reset_count} adayın sınav hakkı sıfırlandı.'
    })


# ====================
# EXTEND EXAM TIME
# ====================

@admin_ops_bp.route('/api/admin/candidate/<int:candidate_id>/extend-time', methods=['POST'])
@superadmin_required
def extend_exam_time(candidate_id):
    """Extend a candidate's exam time (for technical issues)."""
    candidate = Candidate.query.get_or_404(candidate_id)
    
    data = request.get_json() or {}
    extra_minutes = data.get('minutes', 15)
    reason = data.get('reason', 'Teknik sorun nedeniyle süre uzatıldı')
    
    if candidate.durum != 'sinavda':
        return jsonify({
            'success': False,
            'error': 'Aday şu anda sınavda değil'
        }), 400
    
    # Extend time
    from datetime import timedelta
    if candidate.sinav_bitis:
        candidate.sinav_bitis = candidate.sinav_bitis + timedelta(minutes=extra_minutes)
    
    db.session.commit()
    
    log_admin_action(
        action='extend_exam_time',
        target_type='candidate',
        target_id=candidate_id,
        details={'extra_minutes': extra_minutes, 'reason': reason}
    )
    
    return jsonify({
        'success': True,
        'message': f'{candidate.ad_soyad} adlı adayın süresi {extra_minutes} dakika uzatıldı.',
        'new_end_time': candidate.sinav_bitis.isoformat() if candidate.sinav_bitis else None
    })

# -*- coding: utf-8 -*-
"""
Data Management Routes - Backup, GDPR, cleanup operations
FIXED: /data/cleanup 500 error - added proper error handling
GitHub: app/routes/data_management.py
"""
import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response, current_app
from app.extensions import db
data_bp = Blueprint('data', __name__, url_prefix='/data')
def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lutfen giris yapin.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
def superadmin_required(f):
    """Only superadmin can access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu islem sadece super admin tarafindan yapilabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated
@data_bp.route('/backup')
@login_required
@superadmin_required
def backup():
    """Show backup page and options"""
    backups = []
    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    try:
        if os.path.exists(backup_dir):
            for f in sorted(os.listdir(backup_dir), reverse=True):
                if f.endswith('.sql') or f.endswith('.json') or f.endswith('.zip'):
                    filepath = os.path.join(backup_dir, f)
                    backups.append({
                        'filename': f,
                        'size': os.path.getsize(filepath),
                        'size_mb': round(os.path.getsize(filepath) / (1024 * 1024), 2),
                        'created': datetime.fromtimestamp(os.path.getctime(filepath))
                    })
    except Exception as e:
        current_app.logger.error(f"Backup list error: {e}")
    return render_template('data_backup.html', backups=backups)
@data_bp.route('/backup/create', methods=['POST'])
@login_required
@superadmin_required
def create_backup():
    """Create a new database backup"""
    from app.models import Candidate, Company, Question
    try:
        backup_dir = os.path.join(current_app.root_path, '..', 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.json'
        filepath = os.path.join(backup_dir, filename)
        backup_data = {
            'created_at': datetime.now().isoformat(),
            'version': '1.0',
            'tables': {}
        }
        companies = Company.query.all()
        backup_data['tables']['companies'] = [
            {'id': c.id, 'isim': c.isim, 'email': c.email, 'kredi': c.kredi, 'is_active': c.is_active}
            for c in companies
        ]
        candidates = Candidate.query.filter_by(is_deleted=False).all()
        backup_data['tables']['candidates'] = [
            {'id': c.id, 'ad_soyad': c.ad_soyad, 'email': c.email, 'sirket_id': c.sirket_id, 
             'puan': c.puan, 'seviye_sonuc': c.seviye_sonuc, 'sinav_durumu': c.sinav_durumu}
            for c in candidates
        ]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        flash(f"Yedek basariyla olusturuldu: {filename}", "success")
    except Exception as e:
        flash(f"Yedekleme sirasinda hata olustu: {str(e)}", "danger")
    return redirect(url_for('data.backup'))
@data_bp.route('/backup/download/<filename>')
@login_required
@superadmin_required
def download_backup(filename):
    """Download a backup file"""
    from flask import send_file
    if '..' in filename or '/' in filename or '\\' in filename:
        flash("Gecersiz dosya adi.", "danger")
        return redirect(url_for('data.backup'))
    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    filepath = os.path.join(backup_dir, filename)
    if not os.path.exists(filepath):
        flash("Dosya bulunamadi.", "danger")
        return redirect(url_for('data.backup'))
    return send_file(filepath, as_attachment=True)
@data_bp.route('/cleanup')
@login_required
@superadmin_required
def cleanup():
    """Data cleanup page - FIXED: Added proper error handling"""
    stats = {
        'old_candidates': 0, 
        'old_logs': 0,
        'deleted_candidates': 0
    }
    try:
        from app.models import Candidate
        
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        # Count old completed exams
        try:
            stats['old_candidates'] = Candidate.query.filter(
                Candidate.sinav_durumu == 'tamamlandi',
                Candidate.bitis_tarihi < cutoff_date
            ).count()
        except Exception as e:
            current_app.logger.warning(f"Old candidates count error: {e}")
            stats['old_candidates'] = 0
        
        # Count soft-deleted candidates
        try:
            stats['deleted_candidates'] = Candidate.query.filter_by(is_deleted=True).count()
        except Exception as e:
            current_app.logger.warning(f"Deleted candidates count error: {e}")
            stats['deleted_candidates'] = 0
            
    except ImportError as e:
        current_app.logger.error(f"Import error in cleanup: {e}")
    except Exception as e:
        current_app.logger.error(f"Cleanup stats error: {e}")
    # Count old audit logs
    try:
        from app.models import AuditLog
        log_cutoff = datetime.utcnow() - timedelta(days=180)
        stats['old_logs'] = AuditLog.query.filter(AuditLog.created_at < log_cutoff).count()
    except Exception as e:
        current_app.logger.warning(f"Old logs count error: {e}")
        stats['old_logs'] = 0
    return render_template('data_cleanup.html', stats=stats)
@data_bp.route('/cleanup/execute', methods=['POST'])
@login_required
@superadmin_required
def execute_cleanup():
    """Execute data cleanup operations"""
    cleanup_type = request.form.get('cleanup_type', 'logs')
    
    try:
        if cleanup_type == 'logs':
            from app.models import AuditLog
            log_cutoff = datetime.utcnow() - timedelta(days=180)
            deleted = AuditLog.query.filter(AuditLog.created_at < log_cutoff).delete()
            db.session.commit()
            flash(f"{deleted} eski log kaydı silindi.", "success")
            
        elif cleanup_type == 'deleted_candidates':
            from app.models import Candidate, ExamAnswer
            
            # Get IDs of deleted candidates
            deleted_candidates = Candidate.query.filter_by(is_deleted=True).all()
            count = 0
            
            for candidate in deleted_candidates:
                try:
                    # Delete related records first
                    db.session.execute(
                        db.text("DELETE FROM kredi_hareketleri WHERE aday_id = :aday_id"),
                        {"aday_id": candidate.id}
                    )
                    db.session.execute(
                        db.text("DELETE FROM yazili_cevaplar WHERE aday_id = :aday_id"),
                        {"aday_id": candidate.id}
                    )
                    ExamAnswer.query.filter_by(aday_id=candidate.id).delete()
                    db.session.delete(candidate)
                    count += 1
                except Exception as e:
                    current_app.logger.error(f"Error deleting candidate {candidate.id}: {e}")
                    continue
                    
            db.session.commit()
            flash(f"{count} silinmiş aday kalıcı olarak temizlendi.", "success")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Temizleme hatası: {str(e)}", "danger")
    
    return redirect(url_for('data.cleanup'))
@data_bp.route('/gdpr')
@login_required
@superadmin_required
def gdpr():
    """GDPR compliance page"""
    pending_deletions = []
    
    try:
        from app.models import Candidate
        pending_deletions = Candidate.query.filter_by(is_deleted=True).limit(50).all()
    except Exception as e:
        current_app.logger.error(f"GDPR page error: {e}")
    return render_template('data_gdpr.html', pending_deletions=pending_deletions)
@data_bp.route('/gdpr/delete/<int:candidate_id>', methods=['POST'])
@login_required
@superadmin_required
def gdpr_delete(candidate_id):
    """Permanently delete a candidate for GDPR compliance"""
    from app.models import Candidate, ExamAnswer
    
    try:
        candidate = Candidate.query.get_or_404(candidate_id)
        candidate_name = candidate.ad_soyad
        
        # Delete related records
        db.session.execute(
            db.text("DELETE FROM kredi_hareketleri WHERE aday_id = :aday_id"),
            {"aday_id": candidate_id}
        )
        db.session.execute(
            db.text("DELETE FROM yazili_cevaplar WHERE aday_id = :aday_id"),
            {"aday_id": candidate_id}
        )
        ExamAnswer.query.filter_by(aday_id=candidate_id).delete()
        db.session.delete(candidate)
        db.session.commit()
        
        flash(f"'{candidate_name}' GDPR kapsamında kalıcı olarak silindi.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Silme hatası: {str(e)}", "danger")
    
    return redirect(url_for('data.gdpr'))

# -*- coding: utf-8 -*-
"""
Data Management Routes - Backup, GDPR, cleanup operations
NEW FILE: Implements /data/* routes for data management
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
    """Data cleanup page"""
    from app.models import Candidate, AuditLog
    
    stats = {'old_candidates': 0, 'old_logs': 0}
    
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    try:
        stats['old_candidates'] = Candidate.query.filter(
            Candidate.sinav_durumu == 'tamamlandi',
            Candidate.bitis_tarihi < cutoff_date
        ).count()
    except:
        pass
    
    log_cutoff = datetime.utcnow() - timedelta(days=180)
    try:
        stats['old_logs'] = AuditLog.query.filter(AuditLog.created_at < log_cutoff).count()
    except:
        pass
    
    return render_template('data_cleanup.html', stats=stats)


@data_bp.route('/gdpr')
@login_required
@superadmin_required
def gdpr():
    """GDPR compliance page"""
    from app.models import Candidate
    
    pending_deletions = []
    try:
        pending_deletions = Candidate.query.filter_by(is_deleted=True).limit(50).all()
    except:
        pass
    
    return render_template('data_gdpr.html', pending_deletions=pending_deletions)

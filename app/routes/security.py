# -*- coding: utf-8 -*-
"""
Security Routes - Log and manage security events during exams
NEW FILE: Implements security event logging for fraud detection
GitHub: app/routes/security.py
"""
import os
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Blueprint, request, session, jsonify, current_app

from app.extensions import db

# Türkiye saat dilimi (UTC+3)
TURKEY_TZ = timezone(timedelta(hours=3))

security_bp = Blueprint('security', __name__, url_prefix='/api/security')

def get_turkey_time():
    """Türkiye saatini döndür"""
    return datetime.now(TURKEY_TZ)



def exam_required(f):
    """Require active exam session"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'aday_id' not in session:
            return jsonify({'error': 'No active exam session'}), 401
        return f(*args, **kwargs)
    return decorated


def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ==================== SECURITY EVENT LOGGING ====================
@security_bp.route('/log', methods=['POST'])
@exam_required
def log_security_event():
    """
    Log security events during exam (tab switches, blur events, etc.)
    Events are stored for Super Admin review
    """
    try:
        from app.models import Candidate
        
        aday_id = session.get('aday_id')
        candidate = Candidate.query.get(aday_id)
        
        if not candidate:
            return jsonify({'error': 'Candidate not found'}), 404
        
        data = request.get_json()
        event_type = data.get('event_type', 'unknown')
        event_data = data.get('data', {})
        timestamp = data.get('timestamp', get_turkey_time().isoformat())
        
        # Create security logs directory
        logs_dir = os.path.join(current_app.root_path, '..', 'security_logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create candidate-specific log file
        log_file = os.path.join(logs_dir, f'candidate_{aday_id}.log')
        
        # Append event to log file
        log_entry = {
            'event_type': event_type,
            'data': event_data,
            'timestamp': timestamp,
            'aday_id': aday_id,
            'candidate_name': candidate.ad_soyad
        }
        
        with open(log_file, 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        # Update candidate security counters
        if event_type == 'tab_switch':
            if not hasattr(candidate, 'tab_switch_count') or candidate.tab_switch_count is None:
                candidate.tab_switch_count = 0
            candidate.tab_switch_count = (candidate.tab_switch_count or 0) + 1
            db.session.commit()
            current_app.logger.warning(f"Tab switch detected for candidate {aday_id}: count={candidate.tab_switch_count}")
        
        elif event_type == 'window_blur':
            if not hasattr(candidate, 'blur_count') or candidate.blur_count is None:
                candidate.blur_count = 0
            candidate.blur_count = (candidate.blur_count or 0) + 1
            db.session.commit()
        
        current_app.logger.info(f"Security event logged: {event_type} for candidate {aday_id}")
        
        return jsonify({
            'status': 'ok',
            'event_type': event_type,
            'logged': True
        })
        
    except Exception as e:
        current_app.logger.error(f"Security log error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@security_bp.route('/logs/<int:aday_id>')
@login_required
def get_security_logs(aday_id):
    """
    Get security logs for a candidate (Super Admin only)
    """
    import json
    from app.models import Candidate, User
    
    # Check permissions
    user_role = session.get('rol')
    user_id = session.get('kullanici_id')
    
    candidate = Candidate.query.get_or_404(aday_id)
    
    # SuperAdmin can see all, company admin can only see their candidates
    if user_role not in ['superadmin', 'super_admin']:
        user = User.query.get(user_id)
        if user and user.sirket_id != candidate.sirket_id:
            return jsonify({'error': 'Access denied'}), 403
    
    # Read log file
    logs_dir = os.path.join(current_app.root_path, '..', 'security_logs')
    log_file = os.path.join(logs_dir, f'candidate_{aday_id}.log')
    
    events = []
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    events.append(json.loads(line.strip()))
                except:
                    pass
    
    # Count by event type
    event_counts = {}
    for event in events:
        event_type = event.get('event_type', 'unknown')
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    return jsonify({
        'aday_id': aday_id,
        'candidate_name': candidate.ad_soyad,
        'total_events': len(events),
        'event_counts': event_counts,
        'events': events[-50:]  # Return last 50 events
    })


@security_bp.route('/summary')
@login_required
def get_security_summary():
    """
    Get overall security summary for all candidates (Super Admin dashboard)
    """
    import json
    from app.models import Candidate
    
    user_role = session.get('rol')
    if user_role not in ['superadmin', 'super_admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get all candidates with security issues
    logs_dir = os.path.join(current_app.root_path, '..', 'security_logs')
    
    summary = {
        'total_violations': 0,
        'tab_switches': 0,
        'blur_events': 0,
        'flagged_candidates': []
    }
    
    if os.path.exists(logs_dir):
        for filename in os.listdir(logs_dir):
            if filename.endswith('.log'):
                aday_id = filename.replace('candidate_', '').replace('.log', '')
                try:
                    aday_id = int(aday_id)
                    candidate = Candidate.query.get(aday_id)
                    if not candidate:
                        continue
                    
                    log_file = os.path.join(logs_dir, filename)
                    events = []
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                events.append(json.loads(line.strip()))
                            except:
                                pass
                    
                    tab_switches = sum(1 for e in events if e.get('event_type') == 'tab_switch')
                    blur_events = sum(1 for e in events if e.get('event_type') == 'window_blur')
                    
                    summary['tab_switches'] += tab_switches
                    summary['blur_events'] += blur_events
                    summary['total_violations'] += len(events)
                    
                    # Flag candidates with significant violations
                    if tab_switches >= 2 or blur_events >= 5:
                        summary['flagged_candidates'].append({
                            'aday_id': aday_id,
                            'candidate_name': candidate.ad_soyad,
                            'tab_switches': tab_switches,
                            'blur_events': blur_events,
                            'total_events': len(events)
                        })
                        
                except Exception as e:
                    current_app.logger.error(f"Error processing log {filename}: {e}")
    
    # Sort by violation count
    summary['flagged_candidates'].sort(key=lambda x: x['total_events'], reverse=True)
    
    return jsonify(summary)

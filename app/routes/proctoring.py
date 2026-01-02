# -*- coding: utf-8 -*-
"""
Proctoring Routes - Exam monitoring and photo capture
NEW FILE: Implements proctoring snapshot storage and viewing
GitHub: app/routes/proctoring.py
"""
import os
import base64
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app, send_file

from app.extensions import db

proctoring_bp = Blueprint('proctoring', __name__, url_prefix='/api/proctoring')


def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


def exam_required(f):
    """Require active exam session"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'aday_id' not in session:
            return jsonify({'error': 'No active exam session'}), 401
        return f(*args, **kwargs)
    return decorated


@proctoring_bp.route('/snapshot', methods=['POST'])
@exam_required
def save_snapshot():
    """
    Save proctoring snapshot from webcam
    Receives base64 image data and stores it
    """
    try:
        from app.models import Candidate
        
        aday_id = session.get('aday_id')
        candidate = Candidate.query.get(aday_id)
        
        if not candidate:
            return jsonify({'error': 'Candidate not found'}), 404
        
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No image data'}), 400
        
        # Create proctoring directory if not exists
        proctoring_dir = os.path.join(current_app.root_path, '..', 'proctoring_images')
        os.makedirs(proctoring_dir, exist_ok=True)
        
        # Create candidate-specific directory
        candidate_dir = os.path.join(proctoring_dir, str(aday_id))
        os.makedirs(candidate_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'snapshot_{timestamp}.png'
        filepath = os.path.join(candidate_dir, filename)
        
        # Save image
        if image_data.startswith('data:image'):
            # Remove base64 header
            image_data = image_data.split(',')[1]
        
        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(image_data))
        
        # Update candidate proctoring count
        if not hasattr(candidate, 'proctoring_count'):
            candidate.proctoring_count = 0
        candidate.proctoring_count = (candidate.proctoring_count or 0) + 1
        db.session.commit()
        
        current_app.logger.info(f"Proctoring snapshot saved for candidate {aday_id}: {filename}")
        
        return jsonify({
            'status': 'ok',
            'filename': filename,
            'count': candidate.proctoring_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Proctoring snapshot error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@proctoring_bp.route('/snapshots/<int:aday_id>')
@login_required
def get_snapshots(aday_id):
    """
    Get list of proctoring snapshots for a candidate
    Accessible by SuperAdmin and the candidate's company admin
    """
    from app.models import Candidate, User
    
    # Check permissions
    user_id = session.get('kullanici_id')
    user_role = session.get('rol')
    
    candidate = Candidate.query.get_or_404(aday_id)
    
    # SuperAdmin can see all, company admin can only see their candidates
    if user_role != 'superadmin':
        user = User.query.get(user_id)
        if user and user.sirket_id != candidate.sirket_id:
            return jsonify({'error': 'Access denied'}), 403
    
    # Get snapshots from directory
    proctoring_dir = os.path.join(current_app.root_path, '..', 'proctoring_images', str(aday_id))
    
    snapshots = []
    if os.path.exists(proctoring_dir):
        for filename in sorted(os.listdir(proctoring_dir), reverse=True):
            if filename.endswith('.png') or filename.endswith('.jpg'):
                filepath = os.path.join(proctoring_dir, filename)
                snapshots.append({
                    'filename': filename,
                    'timestamp': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
                    'size': os.path.getsize(filepath),
                    'url': url_for('proctoring.view_snapshot', aday_id=aday_id, filename=filename)
                })
    
    return jsonify({
        'aday_id': aday_id,
        'candidate_name': candidate.ad_soyad,
        'count': len(snapshots),
        'snapshots': snapshots
    })


@proctoring_bp.route('/snapshots/<int:aday_id>/<filename>')
@login_required
def view_snapshot(aday_id, filename):
    """
    View a specific proctoring snapshot image
    """
    from app.models import Candidate, User
    
    # Security: validate filename
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    # Check permissions
    user_id = session.get('kullanici_id')
    user_role = session.get('rol')
    
    candidate = Candidate.query.get_or_404(aday_id)
    
    # SuperAdmin can see all, company admin can only see their candidates
    if user_role != 'superadmin':
        user = User.query.get(user_id)
        if user and user.sirket_id != candidate.sirket_id:
            return jsonify({'error': 'Access denied'}), 403
    
    # Serve the image
    proctoring_dir = os.path.join(current_app.root_path, '..', 'proctoring_images', str(aday_id))
    filepath = os.path.join(proctoring_dir, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filepath, mimetype='image/png')


@proctoring_bp.route('/snapshots/<int:aday_id>/delete', methods=['POST'])
@login_required
def delete_snapshots(aday_id):
    """
    Delete all proctoring snapshots for a candidate (GDPR compliance)
    Only SuperAdmin can delete
    """
    if session.get('rol') != 'superadmin':
        return jsonify({'error': 'Access denied'}), 403
    
    import shutil
    
    proctoring_dir = os.path.join(current_app.root_path, '..', 'proctoring_images', str(aday_id))
    
    if os.path.exists(proctoring_dir):
        shutil.rmtree(proctoring_dir)
        current_app.logger.info(f"Deleted proctoring snapshots for candidate {aday_id}")
        return jsonify({'status': 'ok', 'message': 'Snapshots deleted'})
    
    return jsonify({'status': 'ok', 'message': 'No snapshots found'})

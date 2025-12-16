# -*- coding: utf-8 -*-
"""
WebSocket Support with Flask-SocketIO
Real-time communication for exam proctoring and live updates.

Features:
- Exam session monitoring
- Live timer sync
- Connection status tracking
- Proctor notifications
- Token-based auth fallback for CORS
"""
import os
import logging
from datetime import datetime
from flask import session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
# SOCKETIO CONFIGURATION
# ══════════════════════════════════════════════════════════════════

# Initialize SocketIO with explicit session management
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='eventlet',  # or 'gevent'
    ping_timeout=60,
    ping_interval=25,
    manage_session=True,  # Explicitly enable Flask session in SocketIO
    cookie='io_session'   # Custom cookie name for WebSocket session
)

# In-memory session store for token-based auth (fallback)
# Use Redis in production for multi-server deployment
_ws_sessions = {}


def init_socketio(app):
    """Initialize SocketIO with Flask app."""
    socketio.init_app(app)
    logger.info("Flask-SocketIO initialized with manage_session=True")
    return socketio


def get_ws_user_id():
    """
    Get user ID from WebSocket connection.
    Checks both Flask session and token-based auth.
    
    Returns:
        tuple: (aday_id, sirket_id, kullanici_id)
    """
    # Try Flask session first
    aday_id = session.get('aday_id')
    sirket_id = session.get('sirket_id')
    kullanici_id = session.get('kullanici_id')
    
    # Fallback to token-based auth (for CORS scenarios)
    if not aday_id and not kullanici_id:
        # Check query params or auth header
        token = request.args.get('token')
        if token and token in _ws_sessions:
            ws_session = _ws_sessions[token]
            aday_id = ws_session.get('aday_id')
            sirket_id = ws_session.get('sirket_id')
            kullanici_id = ws_session.get('kullanici_id')
    
    return aday_id, sirket_id, kullanici_id


def create_ws_token(aday_id=None, sirket_id=None, kullanici_id=None):
    """
    Create a WebSocket authentication token.
    Call this after HTTP login success.
    
    Returns:
        str: Token to use in WebSocket connection
    """
    import secrets
    token = secrets.token_urlsafe(32)
    _ws_sessions[token] = {
        'aday_id': aday_id,
        'sirket_id': sirket_id,
        'kullanici_id': kullanici_id,
        'created_at': datetime.utcnow()
    }
    return token


# ══════════════════════════════════════════════════════════════════
# EXAM NAMESPACE - Real-time exam features
# ══════════════════════════════════════════════════════════════════

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {session.get('aday_id') or session.get('kullanici_id')}")
    emit('connection_status', {'status': 'connected', 'timestamp': datetime.utcnow().isoformat()})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    aday_id = session.get('aday_id')
    if aday_id:
        # Notify proctors about candidate disconnection
        emit('candidate_disconnected', {
            'aday_id': aday_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'proctor_{session.get("sirket_id")}', broadcast=True)
    
    logger.info(f"Client disconnected: {aday_id}")


@socketio.on('join_exam')
def handle_join_exam(data):
    """
    Candidate joins exam room.
    
    Args:
        data: {exam_id, aday_id}
    """
    exam_id = data.get('exam_id')
    aday_id = session.get('aday_id')
    
    if not aday_id:
        emit('error', {'message': 'Not authenticated'})
        return
    
    # Join exam-specific room
    room = f'exam_{exam_id}'
    join_room(room)
    
    # Notify room about new participant
    emit('candidate_joined', {
        'aday_id': aday_id,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)
    
    logger.info(f"Candidate {aday_id} joined exam {exam_id}")


@socketio.on('leave_exam')
def handle_leave_exam(data):
    """Candidate leaves exam room."""
    exam_id = data.get('exam_id')
    room = f'exam_{exam_id}'
    leave_room(room)
    
    emit('candidate_left', {
        'aday_id': session.get('aday_id'),
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)


@socketio.on('heartbeat')
def handle_heartbeat(data):
    """
    Periodic heartbeat from candidate.
    Used for connection monitoring.
    """
    aday_id = session.get('aday_id')
    if not aday_id:
        return
    
    # Update last seen timestamp (could store in Redis)
    emit('heartbeat_ack', {
        'status': 'alive',
        'server_time': datetime.utcnow().isoformat()
    })
    
    # Broadcast to proctor room
    sirket_id = session.get('sirket_id')
    if sirket_id:
        emit('candidate_heartbeat', {
            'aday_id': aday_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'proctor_{sirket_id}', broadcast=True)


@socketio.on('timer_sync')
def handle_timer_sync(data):
    """
    Sync exam timer with server.
    Prevents client-side timer manipulation.
    """
    aday_id = session.get('aday_id')
    if not aday_id:
        emit('error', {'message': 'Not authenticated'})
        return
    
    from app.models import Candidate
    from app.extensions import db
    
    candidate = Candidate.query.get(aday_id)
    if not candidate or not candidate.baslama_tarihi:
        emit('timer_sync_response', {'remaining': 0})
        return
    
    # Calculate remaining time server-side
    elapsed = (datetime.utcnow() - candidate.baslama_tarihi).total_seconds()
    remaining = max(0, (candidate.sinav_suresi * 60) - elapsed)
    
    emit('timer_sync_response', {
        'remaining': int(remaining),
        'server_time': datetime.utcnow().isoformat()
    })


# ══════════════════════════════════════════════════════════════════
# PROCTOR NAMESPACE - Exam monitoring for admins
# ══════════════════════════════════════════════════════════════════

@socketio.on('join_proctor')
def handle_join_proctor(data):
    """Admin joins proctor room to monitor exams."""
    sirket_id = session.get('sirket_id')
    if not sirket_id:
        emit('error', {'message': 'Not authorized'})
        return
    
    room = f'proctor_{sirket_id}'
    join_room(room)
    
    emit('proctor_joined', {
        'user_id': session.get('kullanici_id'),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    logger.info(f"Proctor joined room: {room}")


@socketio.on('pause_candidate')
def handle_pause_candidate(data):
    """
    Proctor pauses a candidate's exam.
    
    Args:
        data: {aday_id, reason}
    """
    if not session.get('kullanici_id'):
        emit('error', {'message': 'Not authorized'})
        return
    
    aday_id = data.get('aday_id')
    reason = data.get('reason', 'Paused by proctor')
    
    # Emit to specific candidate
    emit('exam_paused', {
        'reason': reason,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'candidate_{aday_id}')
    
    logger.info(f"Exam paused for candidate {aday_id}: {reason}")


@socketio.on('resume_candidate')
def handle_resume_candidate(data):
    """Proctor resumes a paused exam."""
    aday_id = data.get('aday_id')
    
    emit('exam_resumed', {
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'candidate_{aday_id}')


# ══════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS (can be called from routes)
# ══════════════════════════════════════════════════════════════════

def notify_exam_completed(aday_id: int, sirket_id: int, score: float):
    """
    Notify proctors when a candidate completes exam.
    Call this from exam completion route.
    """
    socketio.emit('candidate_completed', {
        'aday_id': aday_id,
        'score': score,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'proctor_{sirket_id}')


def notify_suspicious_activity(aday_id: int, sirket_id: int, activity_type: str, details: str):
    """
    Alert proctors about suspicious activity.
    
    Args:
        activity_type: 'tab_switch', 'copy_paste', 'multiple_faces', etc.
    """
    socketio.emit('suspicious_activity', {
        'aday_id': aday_id,
        'activity_type': activity_type,
        'details': details,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'proctor_{sirket_id}')


def broadcast_to_exam(exam_id: str, event: str, data: dict):
    """Broadcast message to all participants in an exam."""
    socketio.emit(event, data, room=f'exam_{exam_id}')

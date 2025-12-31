# -*- coding: utf-8 -*-
"""
Health Check Endpoints
System monitoring for Skills Test Center
"""
import os
import time
import logging
from datetime import datetime
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint for load balancers and monitoring.
    Returns quick status without deep checks.
    """
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'skills-test-center'
    }), 200


@health_bp.route('/api/health', methods=['GET'])
def api_health_check():
        """
            API health check endpoint for /api/health route.
                Alias for main health check.
                    """
        return jsonify({
                    'status': 'ok',
                    'timestamp': datetime.utcnow().isoformat(),
                    'service': 'skills-test-center'
        }), 200
    
@health_bp.route('/health/detailed', methods=['GET'])
def detailed_health_check():
    """
    Detailed health check with all service statuses.
    Use this for comprehensive monitoring (UptimeRobot, Datadog, etc.)
    """
    health_status = {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'skills-test-center',
        'version': os.getenv('APP_VERSION', '2.0.0'),
        'checks': {}
    }
    
    all_ok = True
    
    # ====================
    # DATABASE CHECK
    # ====================
    try:
        from app.extensions import db
        start = time.time()
        db.session.execute('SELECT 1')
        db.session.commit()
        response_time = round((time.time() - start) * 1000, 2)
        
        health_status['checks']['database'] = {
            'status': 'ok',
            'response_time_ms': response_time
        }
    except Exception as e:
        all_ok = False
        health_status['checks']['database'] = {
            'status': 'error',
            'error': str(e)
        }
        logger.error(f"Health check - Database error: {str(e)}")
    
    # ====================
    # REDIS CHECK
    # ====================
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        start = time.time()
        r = redis.from_url(redis_url)
        r.ping()
        response_time = round((time.time() - start) * 1000, 2)
        
        health_status['checks']['redis'] = {
            'status': 'ok',
            'response_time_ms': response_time
        }
    except Exception as e:
        all_ok = False
        health_status['checks']['redis'] = {
            'status': 'error',
            'error': str(e)
        }
        logger.error(f"Health check - Redis error: {str(e)}")
    
    # ====================
    # CELERY CHECK
    # ====================
    try:
        from app.celery_app import celery
        start = time.time()
        
        # Check if at least one worker is available
        inspector = celery.control.inspect()
        active_workers = inspector.ping()
        response_time = round((time.time() - start) * 1000, 2)
        
        if active_workers:
            health_status['checks']['celery'] = {
                'status': 'ok',
                'workers': len(active_workers),
                'response_time_ms': response_time
            }
        else:
            all_ok = False
            health_status['checks']['celery'] = {
                'status': 'warning',
                'message': 'No active workers found'
            }
    except Exception as e:
        # Celery being down is a warning, not critical
        health_status['checks']['celery'] = {
            'status': 'warning',
            'error': str(e)
        }
        logger.warning(f"Health check - Celery warning: {str(e)}")
    
    # ====================
    # AI SERVICE CHECK
    # ====================
    try:
        gemini_key = os.getenv('GEMINI_API_KEY', '')
        if gemini_key:
            health_status['checks']['ai_service'] = {
                'status': 'ok',
                'provider': 'gemini',
                'configured': True
            }
        else:
            health_status['checks']['ai_service'] = {
                'status': 'warning',
                'configured': False,
                'message': 'GEMINI_API_KEY not set'
            }
    except Exception as e:
        health_status['checks']['ai_service'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # ====================
    # DISK SPACE CHECK
    # ====================
    try:
        import shutil
        total, used, free = shutil.disk_usage('/')
        free_gb = round(free / (1024 ** 3), 2)
        usage_percent = round((used / total) * 100, 1)
        
        if usage_percent > 90:
            all_ok = False
            disk_status = 'critical'
        elif usage_percent > 80:
            disk_status = 'warning'
        else:
            disk_status = 'ok'
        
        health_status['checks']['disk'] = {
            'status': disk_status,
            'free_gb': free_gb,
            'usage_percent': usage_percent
        }
    except Exception as e:
        health_status['checks']['disk'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    # ====================
    # FINAL STATUS
    # ====================
    if not all_ok:
        health_status['status'] = 'degraded'
        return jsonify(health_status), 503
    
    return jsonify(health_status), 200


@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """
    Kubernetes-style readiness probe.
    Returns 200 only if the service is ready to handle traffic.
    """
    try:
        from app.extensions import db
        db.session.execute('SELECT 1')
        db.session.commit()
        return jsonify({'ready': True}), 200
    except Exception:
        return jsonify({'ready': False}), 503


@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """
    Kubernetes-style liveness probe.
    Returns 200 if the process is alive.
    """
    return jsonify({'alive': True}), 200

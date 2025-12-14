# -*- coding: utf-8 -*-
"""
Webhook Tasks - Async webhook triggers with retry
"""
from app.celery_app import celery
import requests
import json
import hmac
import hashlib
import os


@celery.task(bind=True, max_retries=3, default_retry_delay=30)
def send_webhook(self, webhook_url, event_type, payload, secret=None):
    """
    Send webhook notification with retry
    
    Args:
        webhook_url: Target URL
        event_type: Event type (exam.completed, candidate.created, etc.)
        payload: Event data dictionary
        secret: HMAC secret for signature
    """
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-Event-Type': event_type,
            'User-Agent': 'SkillsTestCenter-Webhook/1.0'
        }
        
        # Sign payload if secret provided
        if secret:
            payload_str = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                secret.encode('utf-8'),
                payload_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            headers['X-Signature'] = f'sha256={signature}'
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        response.raise_for_status()
        
        return {
            'status': 'delivered',
            'status_code': response.status_code,
            'event_type': event_type
        }
        
    except requests.exceptions.RequestException as e:
        # Retry on network errors
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3)
def trigger_exam_completed(self, candidate_id):
    """
    Trigger webhook when exam is completed
    
    Args:
        candidate_id: Candidate ID
    """
    try:
        from app.models import Candidate, Company
        
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return {'status': 'skipped', 'reason': 'candidate not found'}
        
        company = Company.query.get(candidate.sirket_id)
        if not company or not company.webhook_url:
            return {'status': 'skipped', 'reason': 'no webhook configured'}
        
        payload = {
            'event': 'exam.completed',
            'timestamp': candidate.bitis_tarihi.isoformat() if candidate.bitis_tarihi else None,
            'candidate': {
                'id': candidate.id,
                'name': candidate.ad_soyad,
                'email': candidate.email,
                'code': candidate.giris_kodu
            },
            'results': {
                'score': candidate.puan,
                'cefr_level': candidate.seviye_sonuc,
                'band_score': candidate.band_score,
                'skills': {
                    'grammar': candidate.p_grammar,
                    'vocabulary': candidate.p_vocabulary,
                    'reading': candidate.p_reading,
                    'listening': candidate.p_listening,
                    'writing': candidate.p_writing,
                    'speaking': candidate.p_speaking
                }
            },
            'certificate_hash': candidate.certificate_hash
        }
        
        return send_webhook(
            company.webhook_url,
            'exam.completed',
            payload,
            secret=company.api_key
        )
        
    except Exception as e:
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3)
def trigger_candidate_created(self, candidate_id):
    """
    Trigger webhook when candidate is created
    """
    try:
        from app.models import Candidate, Company
        
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return {'status': 'skipped'}
        
        company = Company.query.get(candidate.sirket_id)
        if not company or not company.webhook_url:
            return {'status': 'skipped'}
        
        payload = {
            'event': 'candidate.created',
            'timestamp': candidate.created_at.isoformat() if candidate.created_at else None,
            'candidate': {
                'id': candidate.id,
                'name': candidate.ad_soyad,
                'email': candidate.email,
                'code': candidate.giris_kodu,
                'exam_duration': candidate.sinav_suresi,
                'question_limit': candidate.soru_limiti
            }
        }
        
        return send_webhook(
            company.webhook_url,
            'candidate.created',
            payload,
            secret=company.api_key
        )
        
    except Exception as e:
        raise self.retry(exc=e)


@celery.task
def send_test_webhook(sirket_id):
    """
    Send test webhook to verify configuration
    """
    from app.models import Company
    
    company = Company.query.get(sirket_id)
    if not company or not company.webhook_url:
        return {'status': 'error', 'reason': 'no webhook configured'}
    
    payload = {
        'event': 'webhook.test',
        'message': 'This is a test webhook from Skills Test Center',
        'company_id': sirket_id
    }
    
    return send_webhook(
        company.webhook_url,
        'webhook.test',
        payload,
        secret=company.api_key
    )

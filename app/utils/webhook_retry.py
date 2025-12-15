# -*- coding: utf-8 -*-
"""
Webhook Retry Mechanism
Automatic retry for failed webhook deliveries with exponential backoff
"""
import json
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests

from app.extensions import db

logger = logging.getLogger(__name__)


class WebhookDelivery(db.Model):
    """Track webhook delivery attempts."""
    
    __tablename__ = 'webhook_deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Webhook config
    webhook_id = db.Column(db.Integer, db.ForeignKey('webhooks.id'), nullable=False)
    
    # Event data
    event_type = db.Column(db.String(50), nullable=False)  # exam_completed, credit_low, etc.
    payload = db.Column(db.Text, nullable=False)  # JSON payload
    
    # Delivery status
    status = db.Column(db.String(20), default='pending')  # pending, success, failed, exhausted
    attempts = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=5)
    
    # Response tracking
    last_response_code = db.Column(db.Integer, nullable=True)
    last_response_body = db.Column(db.Text, nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    
    # Timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_attempt_at = db.Column(db.DateTime, nullable=True)
    next_retry_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<WebhookDelivery {self.id} - {self.event_type}: {self.status}>'


class WebhookRetryManager:
    """
    Manage webhook delivery with automatic retries and exponential backoff.
    """
    
    # Retry configuration
    MAX_ATTEMPTS = 5
    BASE_DELAY_SECONDS = 60  # 1 minute
    MAX_DELAY_SECONDS = 3600  # 1 hour
    BACKOFF_MULTIPLIER = 2
    
    # HTTP configuration
    TIMEOUT_SECONDS = 30
    SUCCESS_CODES = [200, 201, 202, 204]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'SkillsTestCenter-Webhook/2.0'
        })
    
    def calculate_next_retry(self, attempt_number: int) -> datetime:
        """
        Calculate next retry time with exponential backoff.
        
        Attempt 1: 1 minute
        Attempt 2: 2 minutes
        Attempt 3: 4 minutes
        Attempt 4: 8 minutes
        Attempt 5: 16 minutes (capped at 1 hour)
        """
        delay = min(
            self.BASE_DELAY_SECONDS * (self.BACKOFF_MULTIPLIER ** (attempt_number - 1)),
            self.MAX_DELAY_SECONDS
        )
        return datetime.utcnow() + timedelta(seconds=delay)
    
    def generate_signature(self, payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.
        """
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def send_webhook(
        self,
        url: str,
        event_type: str,
        payload: Dict[str, Any],
        secret: Optional[str] = None,
        webhook_id: Optional[int] = None
    ) -> WebhookDelivery:
        """
        Send a webhook with automatic retry scheduling on failure.
        
        Args:
            url: Webhook endpoint URL
            event_type: Type of event (exam_completed, etc.)
            payload: Event data dictionary
            secret: Optional signing secret
            webhook_id: Optional webhook configuration ID
        
        Returns:
            WebhookDelivery: Delivery record
        """
        # Serialize payload
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        
        # Create delivery record
        delivery = WebhookDelivery(
            webhook_id=webhook_id or 0,
            event_type=event_type,
            payload=payload_json,
            status='pending',
            attempts=0,
            max_attempts=self.MAX_ATTEMPTS
        )
        
        db.session.add(delivery)
        db.session.commit()
        
        # Attempt delivery
        self._attempt_delivery(delivery, url, secret)
        
        return delivery
    
    def _attempt_delivery(
        self,
        delivery: WebhookDelivery,
        url: str,
        secret: Optional[str] = None
    ) -> bool:
        """
        Attempt to deliver a webhook.
        
        Returns:
            bool: True if successful, False otherwise
        """
        delivery.attempts += 1
        delivery.last_attempt_at = datetime.utcnow()
        
        try:
            # Prepare headers
            headers = {
                'X-Webhook-Event': delivery.event_type,
                'X-Webhook-Delivery': str(delivery.id),
                'X-Webhook-Timestamp': datetime.utcnow().isoformat()
            }
            
            # Add signature if secret provided
            if secret:
                signature = self.generate_signature(delivery.payload, secret)
                headers['X-Webhook-Signature'] = f'sha256={signature}'
            
            # Send request
            response = self.session.post(
                url,
                data=delivery.payload,
                headers=headers,
                timeout=self.TIMEOUT_SECONDS
            )
            
            delivery.last_response_code = response.status_code
            delivery.last_response_body = response.text[:1000]  # Truncate
            
            if response.status_code in self.SUCCESS_CODES:
                # Success!
                delivery.status = 'success'
                delivery.delivered_at = datetime.utcnow()
                delivery.next_retry_at = None
                
                logger.info(f"Webhook {delivery.id} delivered successfully to {url}")
                
                db.session.commit()
                return True
            else:
                # Non-success status code
                raise requests.exceptions.HTTPError(f"Status code: {response.status_code}")
                
        except requests.exceptions.Timeout:
            delivery.last_error = "Request timed out"
            logger.warning(f"Webhook {delivery.id} timed out")
            
        except requests.exceptions.ConnectionError as e:
            delivery.last_error = f"Connection error: {str(e)}"
            logger.warning(f"Webhook {delivery.id} connection error")
            
        except requests.exceptions.HTTPError as e:
            delivery.last_error = str(e)
            logger.warning(f"Webhook {delivery.id} HTTP error: {e}")
            
        except Exception as e:
            delivery.last_error = f"Unexpected error: {str(e)}"
            logger.error(f"Webhook {delivery.id} unexpected error: {e}")
        
        # Handle failure
        if delivery.attempts >= delivery.max_attempts:
            delivery.status = 'exhausted'
            delivery.next_retry_at = None
            logger.error(f"Webhook {delivery.id} exhausted all retry attempts")
        else:
            delivery.status = 'failed'
            delivery.next_retry_at = self.calculate_next_retry(delivery.attempts)
            logger.info(f"Webhook {delivery.id} scheduled for retry at {delivery.next_retry_at}")
        
        db.session.commit()
        return False
    
    def retry_pending(self, url_getter=None):
        """
        Retry all pending webhooks that are due.
        
        Args:
            url_getter: Callable that takes webhook_id and returns URL
        
        Returns:
            dict: Statistics about retry attempts
        """
        now = datetime.utcnow()
        
        # Find deliveries ready for retry
        pending = WebhookDelivery.query.filter(
            WebhookDelivery.status == 'failed',
            WebhookDelivery.next_retry_at <= now
        ).all()
        
        stats = {
            'total': len(pending),
            'success': 0,
            'failed': 0,
            'exhausted': 0
        }
        
        for delivery in pending:
            # Get URL (need to implement based on your webhook config)
            if url_getter:
                url = url_getter(delivery.webhook_id)
            else:
                # Default: query from webhooks table
                from app.models.admin import Webhook
                webhook = Webhook.query.get(delivery.webhook_id)
                if not webhook:
                    delivery.status = 'exhausted'
                    delivery.last_error = "Webhook configuration not found"
                    db.session.commit()
                    stats['exhausted'] += 1
                    continue
                url = webhook.url
                secret = webhook.secret
            
            success = self._attempt_delivery(delivery, url, secret)
            
            if success:
                stats['success'] += 1
            elif delivery.status == 'exhausted':
                stats['exhausted'] += 1
            else:
                stats['failed'] += 1
        
        return stats
    
    def get_delivery_stats(self, webhook_id: int = None, days: int = 7) -> Dict:
        """
        Get webhook delivery statistics.
        
        Args:
            webhook_id: Optional filter by webhook
            days: Number of days to look back
        
        Returns:
            dict: Delivery statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = WebhookDelivery.query.filter(
            WebhookDelivery.created_at >= cutoff
        )
        
        if webhook_id:
            query = query.filter(WebhookDelivery.webhook_id == webhook_id)
        
        deliveries = query.all()
        
        stats = {
            'total': len(deliveries),
            'success': sum(1 for d in deliveries if d.status == 'success'),
            'failed': sum(1 for d in deliveries if d.status == 'failed'),
            'exhausted': sum(1 for d in deliveries if d.status == 'exhausted'),
            'pending': sum(1 for d in deliveries if d.status == 'pending'),
            'success_rate': 0,
            'avg_attempts': 0,
            'by_event_type': {}
        }
        
        if stats['total'] > 0:
            stats['success_rate'] = round(stats['success'] / stats['total'] * 100, 1)
            stats['avg_attempts'] = round(sum(d.attempts for d in deliveries) / stats['total'], 1)
        
        # Group by event type
        for d in deliveries:
            if d.event_type not in stats['by_event_type']:
                stats['by_event_type'][d.event_type] = {'total': 0, 'success': 0}
            stats['by_event_type'][d.event_type]['total'] += 1
            if d.status == 'success':
                stats['by_event_type'][d.event_type]['success'] += 1
        
        return stats


# Global instance
webhook_manager = WebhookRetryManager()


def send_webhook_with_retry(url, event_type, payload, secret=None, webhook_id=None):
    """
    Convenience function to send a webhook with automatic retry.
    """
    return webhook_manager.send_webhook(url, event_type, payload, secret, webhook_id)

# -*- coding: utf-8 -*-
"""
Admin Models - LoginAttempt and CreditTransaction
"""
from app.extensions import db
from datetime import datetime
class LoginAttempt(db.Model):
    """Track login attempts for security monitoring"""
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    success = db.Column(db.Boolean, default=False)
    failure_reason = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class CreditTransaction(db.Model):
    """Track credit transactions for companies"""
    __tablename__ = 'credit_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    reference_id = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    company = db.relationship('Company', backref='credit_transactions')
    creator = db.relationship('User', foreign_keys=[created_by])
def log_action(user_id, action, entity_type, entity_id=None, details=None, ip_address=None):
    """Log admin action to AuditLog"""
    try:
        from app.models.audit_log import AuditLog
        import json
        
        if isinstance(details, dict):
            details = json.dumps(details, ensure_ascii=False)
        
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Failed to log action: {e}")
        db.session.rollback()

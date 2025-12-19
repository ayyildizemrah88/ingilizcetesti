# -*- coding: utf-8 -*-
"""
Audit Log Model - Track all admin actions for compliance
"""
from datetime import datetime
from app.extensions import db

class AuditLog(db.Model):
    """Audit trail for all admin actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Who
    user_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), index=True, nullable=True)
    user_email = db.Column(db.String(255))
    user_role = db.Column(db.String(50))
    
    # What
    action = db.Column(db.String(50), index=True)  # CREATE, UPDATE, DELETE, VIEW, EXPORT
    entity_type = db.Column(db.String(50), index=True)  # candidate, question, company
    entity_id = db.Column(db.Integer)
    
    # Details
    old_value = db.Column(db.Text)  # JSON of old values
    new_value = db.Column(db.Text)  # JSON of new values
    description = db.Column(db.Text)
    
    # Where
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    # When
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'description': self.description,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type}/{self.entity_id}>'


class FraudCase(db.Model):
    """Track flagged fraud/cheating cases"""
    __tablename__ = 'fraud_cases'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Linked candidate
    candidate_id = db.Column(db.Integer, db.ForeignKey('adaylar.id'), index=True)
    
    # Detection details
    similarity_score = db.Column(db.Float)
    similar_to_id = db.Column(db.Integer)  # ID of similar candidate
    ai_probability = db.Column(db.Float)
    proctoring_violations = db.Column(db.Integer, default=0)
    
    # Reasons (JSON array)
    reasons = db.Column(db.Text)  # JSON array of reason strings
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, cleared, confirmed
    reviewed_by = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    reviewed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    candidate = db.relationship('Candidate', backref='fraud_cases')
    reviewer = db.relationship('User', backref='reviewed_cases', foreign_keys=[reviewed_by])
    
    def __repr__(self):
        return f'<FraudCase {self.id} - {self.status}>'

class ExamSchedule(db.Model):
    """Scheduled exams for candidates"""
    __tablename__ = 'exam_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    
    candidate_id = db.Column(db.Integer, db.ForeignKey('adaylar.id'), index=True)
    template_id = db.Column(db.Integer, db.ForeignKey('sinav_sablonlari.id'))
    
    scheduled_at = db.Column(db.DateTime, nullable=False)
    reminder_sent = db.Column(db.Boolean, default=False)
    reminder_sent_at = db.Column(db.DateTime)
    
    # Status
    status = db.Column(db.String(20), default='scheduled')  # scheduled, started, completed, missed
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    
    # Relationships
    candidate = db.relationship('Candidate', backref='schedules')
    template = db.relationship('ExamTemplate', backref='schedules')
    creator = db.relationship('User', backref='created_schedules', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<ExamSchedule {self.id} - {self.scheduled_at}>'

class LearningResource(db.Model):
    """Learning resources for study plan recommendations"""
    __tablename__ = 'learning_resources'
    
    id = db.Column(db.Integer, primary_key=True)
    
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    url = db.Column(db.String(500))
    
    # Categorization
    skill = db.Column(db.String(50), index=True)  # grammar, vocabulary, reading, etc.
    cefr_level = db.Column(db.String(10), index=True)  # A1-C2
    resource_type = db.Column(db.String(50))  # video, article, quiz, book
    topic = db.Column(db.String(100))  # specific topic like "present_perfect"
    
    # Metadata
    duration_minutes = db.Column(db.Integer)
    difficulty_rating = db.Column(db.Float)  # 1-5 stars
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LearningResource {self.title}>'

class BulkImport(db.Model):
    """Track bulk CSV imports"""
    __tablename__ = 'bulk_imports'
    
    id = db.Column(db.Integer, primary_key=True)
    
    company_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    
    # File info
    filename = db.Column(db.String(255))
    
    # Results
    total_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    errors = db.Column(db.Text)  # JSON array of error messages
    
    # Status
    status = db.Column(db.String(20), default='processing')  # processing, completed, failed
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    company = db.relationship('Company', backref='imports')
    creator = db.relationship('User', backref='imports', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<BulkImport {self.id} - {self.status}>'

def log_action(user, action, entity_type, entity_id, description=None, 
               old_value=None, new_value=None, request=None):
    """Helper function to log an admin action"""
    import json
    
    log = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else 'system',
        user_role=user.rol if user else 'system',
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        old_value=json.dumps(old_value) if old_value else None,
        new_value=json.dumps(new_value) if new_value else None,
        ip_address=request.remote_addr if request else None,
        user_agent=request.user_agent.string if request else None
    )
    
    db.session.add(log)
    db.session.commit()
    
    return log

class CreditTransaction(db.Model):
    """Track credit purchases and usage"""
    __tablename__ = 'credit_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    
    amount = db.Column(db.Integer, nullable=False)  # Positive = add, negative = use
    transaction_type = db.Column(db.String(20), index=True)  # purchase, usage, refund, bonus
    
    payment_id = db.Column(db.String(255))  # External payment reference
    description = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    
    # Relationships
    company = db.relationship('Company', backref='credit_transactions')
    creator = db.relationship('User', backref='credit_transactions', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<CreditTransaction {self.id}: {self.amount}>'

class LoginAttempt(db.Model):
    """Track login attempts for security"""
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), index=True)
    ip_address = db.Column(db.String(45))
    
    success = db.Column(db.Boolean, default=False)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<LoginAttempt {self.email}: {"success" if self.success else "failed"}>'

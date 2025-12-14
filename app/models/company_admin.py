# -*- coding: utf-8 -*-
"""
Company Admin Model
Supports multiple admin users per company
"""
from datetime import datetime
from app.extensions import db


class CompanyAdmin(db.Model):
    """
    Maps users to companies with specific roles.
    Allows multiple admins per company.
    """
    __tablename__ = 'company_admins'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Role within company
    role = db.Column(db.String(50), default='admin')  # 'owner', 'admin', 'viewer'
    
    # Permissions (JSON or boolean flags)
    can_invite_candidates = db.Column(db.Boolean, default=True)
    can_view_reports = db.Column(db.Boolean, default=True)
    can_manage_templates = db.Column(db.Boolean, default=False)
    can_manage_users = db.Column(db.Boolean, default=False)  # Can add/remove company admins
    can_purchase_credits = db.Column(db.Boolean, default=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    company = db.relationship('Company', backref=db.backref('admins', lazy='dynamic'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('company_memberships', lazy='dynamic'))
    inviter = db.relationship('User', foreign_keys=[invited_by])
    
    # Unique constraint: one user can have one role per company
    __table_args__ = (
        db.UniqueConstraint('company_id', 'user_id', name='unique_company_user'),
    )
    
    def __repr__(self):
        return f'<CompanyAdmin {self.user_id} @ Company {self.company_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'role': self.role,
            'permissions': {
                'can_invite_candidates': self.can_invite_candidates,
                'can_view_reports': self.can_view_reports,
                'can_manage_templates': self.can_manage_templates,
                'can_manage_users': self.can_manage_users,
                'can_purchase_credits': self.can_purchase_credits
            },
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @classmethod
    def get_company_for_user(cls, user_id):
        """Get the company for a user (returns first active membership)."""
        membership = cls.query.filter_by(
            user_id=user_id,
            is_active=True
        ).first()
        return membership.company if membership else None
    
    @classmethod
    def get_admins_for_company(cls, company_id):
        """Get all active admins for a company."""
        return cls.query.filter_by(
            company_id=company_id,
            is_active=True
        ).all()
    
    @classmethod
    def user_has_permission(cls, user_id, company_id, permission):
        """Check if a user has a specific permission for a company."""
        membership = cls.query.filter_by(
            user_id=user_id,
            company_id=company_id,
            is_active=True
        ).first()
        
        if not membership:
            return False
        
        # Owner has all permissions
        if membership.role == 'owner':
            return True
        
        return getattr(membership, permission, False)


class CompanyInvitation(db.Model):
    """
    Pending invitations for company admins.
    """
    __tablename__ = 'company_invitations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='admin')
    
    # Invitation token
    token = db.Column(db.String(100), unique=True, nullable=False)
    
    # Who invited
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, accepted, expired
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    accepted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    company = db.relationship('Company')
    inviter = db.relationship('User')
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'email': self.email,
            'role': self.role,
            'status': self.status,
            'invited_by': self.invited_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired()
        }

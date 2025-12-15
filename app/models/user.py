# -*- coding: utf-8 -*-
"""
User Model - Admin users and system users
"""
from datetime import datetime
from app.extensions import db
import bcrypt


class User(db.Model):
    """User model for admin panel access"""
    __tablename__ = 'kullanicilar'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    sifre_hash = db.Column(db.String(255), nullable=False)
    ad_soyad = db.Column(db.String(255))
    rol = db.Column(db.String(50), default='customer')  # superadmin, customer
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Two-Factor Authentication fields
    totp_secret = db.Column(db.String(32))  # TOTP secret for authenticator apps
    totp_verified = db.Column(db.Boolean, default=False)  # Has 2FA been verified/enabled
    backup_codes = db.Column(db.Text)  # Comma-separated hashed backup codes
    
    # User preferences
    language = db.Column(db.String(10), default='tr')  # Preferred language
    
    # Relationships
    company = db.relationship('Company', backref='users')
    
    # ══════════════════════════════════════════════════════════════
    # ROLE HELPERS
    # ══════════════════════════════════════════════════════════════
    
    def is_superadmin(self):
        """Check if user is superadmin"""
        return self.rol == 'superadmin'
    
    def is_customer(self):
        """Check if user is customer"""
        return self.rol == 'customer'
    
    def can_manage_questions(self):
        """Only superadmin can manage questions"""
        return self.is_superadmin()
    
    def can_manage_users(self):
        """Only superadmin can manage users"""
        return self.is_superadmin()
    
    def can_manage_templates(self):
        """Only superadmin can manage exam templates"""
        return self.is_superadmin()
    
    def can_invite_candidates(self):
        """Superadmin and customer can invite candidates"""
        return self.rol in ['superadmin', 'customer']
    
    def can_view_reports(self):
        """Superadmin and customer can view reports"""
        return self.rol in ['superadmin', 'customer']
    
    def can_download_reports(self):
        """Superadmin and customer can download reports"""
        return self.rol in ['superadmin', 'customer']
    
    def set_password(self, password):
        """Hash and set password"""
        self.sifre_hash = bcrypt.hashpw(
            password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
    
    def check_password(self, password):
        """Verify password"""
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            self.sifre_hash.encode('utf-8')
        )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'ad_soyad': self.ad_soyad,
            'rol': self.rol,
            'sirket_id': self.sirket_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<User {self.email}>'

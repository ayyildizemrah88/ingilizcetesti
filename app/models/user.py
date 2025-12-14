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
    rol = db.Column(db.String(50), default='admin')  # superadmin, admin, viewer
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    company = db.relationship('Company', backref='users')
    
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

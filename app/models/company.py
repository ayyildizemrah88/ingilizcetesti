# -*- coding: utf-8 -*-
"""
Company Model - Multi-tenant support
"""
from datetime import datetime
from app.extensions import db


class Company(db.Model):
    """Company model for multi-tenant support"""
    __tablename__ = 'sirketler'
    
    id = db.Column(db.Integer, primary_key=True)
    isim = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    telefon = db.Column(db.String(20))
    adres = db.Column(db.Text)
    
    # Branding
    logo_url = db.Column(db.Text)
    primary_color = db.Column(db.String(10), default='#0d6efd')
    
    # Credits & Billing
    kredi = db.Column(db.Integer, default=100)
    plan_type = db.Column(db.String(50), default='free')  # free, starter, pro, enterprise
    
    # Settings
    is_active = db.Column(db.Boolean, default=True)
    api_key = db.Column(db.String(64), unique=True)
    webhook_url = db.Column(db.Text)
    
    # SMTP settings
    smtp_host = db.Column(db.String(255))
    smtp_port = db.Column(db.Integer)
    smtp_user = db.Column(db.String(255))
    smtp_pass = db.Column(db.String(255))
    smtp_from = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def deduct_credit(self, amount=1):
        """Deduct credits for usage"""
        if self.kredi >= amount:
            self.kredi -= amount
            return True
        return False
    
    def to_dict(self):
        return {
            'id': self.id,
            'isim': self.isim,
            'email': self.email,
            'kredi': self.kredi,
            'plan_type': self.plan_type,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<Company {self.isim}>'


class CreditTransaction(db.Model):
    """Credit usage tracking"""
    __tablename__ = 'kredi_hareketleri'
    
    id = db.Column(db.Integer, primary_key=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    
    islem_tipi = db.Column(db.String(50))  # exam, email, api, purchase
    miktar = db.Column(db.Integer)  # positive for add, negative for deduct
    aciklama = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='credit_transactions')
    
    def __repr__(self):
        return f'<CreditTransaction {self.sirket_id}: {self.miktar}>'

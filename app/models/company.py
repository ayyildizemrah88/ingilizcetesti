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
    
    def deduct_credit(self, amount=1, transaction_type='exam', description=None, 
                      candidate_id=None, user_id=None):
        """
        Deduct credits with ATOMIC update and transaction logging.
        
        Args:
            amount: Number of credits to deduct
            transaction_type: Type of transaction (exam, email, api, refund)
            description: Detailed description of the transaction
            candidate_id: Related candidate ID (if applicable)
            user_id: User who triggered the action
            
        Returns:
            True if successful, False if insufficient credits
        """
        # Check if sufficient credits
        if self.kredi < amount:
            return False
        
        # ATOMIC UPDATE - prevents race condition
        # Uses database-level update instead of Python-level
        from sqlalchemy import text
        
        result = db.session.execute(
            text("""
                UPDATE sirketler 
                SET kredi = kredi - :amount 
                WHERE id = :company_id AND kredi >= :amount
            """),
            {'amount': amount, 'company_id': self.id}
        )
        
        # Check if update was successful (affected 1 row)
        if result.rowcount == 0:
            return False
        
        # Refresh the object to get updated kredi value
        db.session.refresh(self)
        
        # Create transaction record for audit trail
        transaction = CreditTransaction(
            sirket_id=self.id,
            islem_tipi=transaction_type,
            miktar=-amount,  # Negative for deduction
            aciklama=description or f'{transaction_type} için {amount} kredi düşüldü',
            onceki_bakiye=self.kredi + amount,  # Balance before deduction
            sonraki_bakiye=self.kredi,          # Balance after deduction
            aday_id=candidate_id,
            kullanici_id=user_id,
            created_at=datetime.utcnow()
        )
        db.session.add(transaction)
        
        return True
    
    def add_credit(self, amount, transaction_type='purchase', description=None, 
                   payment_ref=None, user_id=None):
        """
        Add credits with transaction logging.
        
        Args:
            amount: Number of credits to add
            transaction_type: Type of transaction (purchase, refund, bonus)
            description: Detailed description
            payment_ref: Payment reference ID
            user_id: User who triggered the action
            
        Returns:
            True if successful
        """
        old_balance = self.kredi
        self.kredi += amount
        
        # Create transaction record
        transaction = CreditTransaction(
            sirket_id=self.id,
            islem_tipi=transaction_type,
            miktar=amount,  # Positive for addition
            aciklama=description or f'{amount} kredi yüklendi',
            onceki_bakiye=old_balance,
            sonraki_bakiye=self.kredi,
            odeme_referans=payment_ref,
            kullanici_id=user_id,
            created_at=datetime.utcnow()
        )
        db.session.add(transaction)
        
        return True
    
    def get_credit_history(self, limit=50):
        """Get recent credit transactions."""
        return CreditTransaction.query.filter_by(sirket_id=self.id)\
            .order_by(CreditTransaction.created_at.desc())\
            .limit(limit).all()
    
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
    """Credit usage tracking with full audit trail"""
    __tablename__ = 'kredi_hareketleri'
    
    id = db.Column(db.Integer, primary_key=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    
    # Transaction details
    islem_tipi = db.Column(db.String(50))  # exam, email, api, purchase, refund, bonus
    miktar = db.Column(db.Integer)  # positive for add, negative for deduct
    aciklama = db.Column(db.Text)
    
    # Balance tracking (for audit)
    onceki_bakiye = db.Column(db.Integer)  # Balance before transaction
    sonraki_bakiye = db.Column(db.Integer)  # Balance after transaction
    
    # Reference IDs (for traceability)
    aday_id = db.Column(db.Integer, db.ForeignKey('adaylar.id'), nullable=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=True)
    odeme_referans = db.Column(db.String(100), nullable=True)  # Payment reference
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='transactions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'sirket_id': self.sirket_id,
            'islem_tipi': self.islem_tipi,
            'miktar': self.miktar,
            'aciklama': self.aciklama,
            'onceki_bakiye': self.onceki_bakiye,
            'sonraki_bakiye': self.sonraki_bakiye,
            'aday_id': self.aday_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<CreditTransaction {self.sirket_id}: {self.miktar}>'

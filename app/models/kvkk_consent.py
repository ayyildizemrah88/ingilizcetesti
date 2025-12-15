# -*- coding: utf-8 -*-
"""
KVKK Consent Model and Mixin
Turkish Personal Data Protection Law (KVKK) compliance
Tracks user consent for foreign data transfer (AI services)
"""
from datetime import datetime
from app.extensions import db


class KVKKConsentMixin:
    """
    Mixin to add KVKK consent fields to any model.
    
    Usage:
        class Candidate(db.Model, KVKKConsentMixin):
            ...
    """
    # Foreign data transfer consent (AI services like OpenAI, Google)
    foreign_data_consent = db.Column(db.Boolean, default=False)
    foreign_data_consent_date = db.Column(db.DateTime)
    foreign_data_consent_ip = db.Column(db.String(45))  # IPv6 support
    
    # General KVKK consent
    kvkk_consent = db.Column(db.Boolean, default=False)
    kvkk_consent_date = db.Column(db.DateTime)
    
    # Marketing consent (optional)
    marketing_consent = db.Column(db.Boolean, default=False)
    marketing_consent_date = db.Column(db.DateTime)
    
    def record_foreign_data_consent(self, ip_address: str = None):
        """Record consent for foreign data transfer."""
        self.foreign_data_consent = True
        self.foreign_data_consent_date = datetime.utcnow()
        self.foreign_data_consent_ip = ip_address
    
    def record_kvkk_consent(self):
        """Record general KVKK consent."""
        self.kvkk_consent = True
        self.kvkk_consent_date = datetime.utcnow()
    
    def has_ai_consent(self) -> bool:
        """Check if user has consented to AI processing."""
        return self.foreign_data_consent == True
    
    def revoke_consent(self):
        """Revoke all consents (KVKK right to be forgotten)."""
        self.foreign_data_consent = False
        self.kvkk_consent = False
        self.marketing_consent = False


class ConsentLog(db.Model):
    """
    Immutable log of all consent actions.
    Required by KVKK for audit purposes.
    """
    __tablename__ = 'consent_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Who gave consent
    user_type = db.Column(db.String(50))  # 'user' or 'candidate'
    user_id = db.Column(db.Integer, index=True)
    email = db.Column(db.String(255))
    
    # What consent
    consent_type = db.Column(db.String(50))  # 'foreign_data', 'kvkk', 'marketing'
    consent_given = db.Column(db.Boolean)  # True = granted, False = revoked
    
    # When and where
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Legal text version (important for audit)
    consent_text_version = db.Column(db.String(20), default='1.0')
    
    def __repr__(self):
        return f'<ConsentLog {self.user_type}:{self.user_id} {self.consent_type}>'
    
    @classmethod
    def log_consent(cls, user_type: str, user_id: int, email: str, 
                   consent_type: str, consent_given: bool,
                   ip_address: str = None, user_agent: str = None):
        """Create immutable consent log entry."""
        log = cls(
            user_type=user_type,
            user_id=user_id,
            email=email,
            consent_type=consent_type,
            consent_given=consent_given,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log)
        return log


# KVKK consent text (Turkish)
KVKK_CONSENT_TEXTS = {
    'foreign_data': {
        'tr': """
Verilerinizin Yurtdışı Aktarımı Hakkında Açık Rıza

Sınav sürecinde yapay zeka teknolojileri kullanılmaktadır. Bu kapsamda:
- Ses kayıtlarınız OpenAI (ABD) sunucularında işlenmektedir
- Yazılı cevaplarınız Google (ABD) sunucularında değerlendirilmektedir

6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) gereğince, kişisel 
verilerinizin yurtdışındaki bu sunuculara aktarılması için açık rızanız 
gerekmektedir.

Bu onayı vererek, yukarıda belirtilen verilerin yurtdışındaki servis 
sağlayıcılarla paylaşılmasını kabul ediyorsunuz.
""",
        'en': """
Consent for International Data Transfer

AI technologies are used during the examination process:
- Your voice recordings are processed on OpenAI (USA) servers
- Your written answers are evaluated on Google (USA) servers

In accordance with Turkish Personal Data Protection Law (KVKK), your 
explicit consent is required for transferring your personal data to 
these foreign servers.

By giving this consent, you agree to the sharing of the above data 
with foreign service providers.
"""
    },
    'kvkk': {
        'tr': """
Kişisel Verilerin İşlenmesi Hakkında Aydınlatma Metni

6698 sayılı KVKK kapsamında kişisel verileriniz; sınav hizmeti sunmak, 
sonuçları raporlamak ve yasal yükümlülükleri yerine getirmek amacıyla 
işlenmektedir.

Verileriniz, sınav süresince ve sonrasında en fazla 1 yıl süreyle 
saklanacaktır.
""",
        'en': """
Personal Data Processing Information Notice

Under KVKK Law No. 6698, your personal data is processed for the 
purposes of providing examination services, reporting results, and 
fulfilling legal obligations.

Your data will be stored during the examination and for up to 1 year 
thereafter.
"""
    }
}

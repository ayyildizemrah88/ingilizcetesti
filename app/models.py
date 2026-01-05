# -*- coding: utf-8 -*-
"""
Database Models - Skills Test Center
GitHub: app/models.py
"""
from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    """Kullanıcı modeli - Admin ve Müşteri kullanıcıları"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    sifre_hash = db.Column(db.String(256), nullable=False)
    ad_soyad = db.Column(db.String(100))
    rol = db.Column(db.String(20), default='customer')  # superadmin, customer
    sirket_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    son_giris = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # İki faktörlü doğrulama
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    
    # İlişkiler
    company = db.relationship('Company', backref='users', lazy=True)
    
    def set_password(self, password):
        self.sifre_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.sifre_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Company(db.Model):
    """Şirket modeli - Kurumsal müşteriler"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    isim = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), index=True)
    telefon = db.Column(db.String(20))
    adres = db.Column(db.Text)
    vergi_no = db.Column(db.String(20))
    kredi = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # İlişkiler
    candidates = db.relationship('Candidate', backref='company', lazy='dynamic')
    
    def __repr__(self):
        return f'<Company {self.isim}>'


class Candidate(db.Model):
    """Aday modeli - Sınav adayları"""
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    ad_soyad = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), index=True)
    tc_kimlik = db.Column(db.String(11), index=True)
    cep_no = db.Column(db.String(20))
    giris_kodu = db.Column(db.String(20), unique=True, index=True)
    
    # Şirket ilişkisi
    sirket_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    
    # Sınav bilgileri
    sinav_suresi = db.Column(db.Integer, default=30)  # Dakika
    soru_limiti = db.Column(db.Integer, default=25)
    sinav_durumu = db.Column(db.String(20), default='beklemede')  # beklemede, devam_ediyor, tamamlandi
    baslangic_tarihi = db.Column(db.DateTime)
    bitis_tarihi = db.Column(db.DateTime)
    
    # Sonuçlar
    puan = db.Column(db.Float)
    seviye_sonuc = db.Column(db.String(5))  # A1, A2, B1, B2, C1, C2
    
    # Beceri puanları
    p_grammar = db.Column(db.Float)
    p_vocabulary = db.Column(db.Float)
    p_reading = db.Column(db.Float)
    p_listening = db.Column(db.Float)
    p_speaking = db.Column(db.Float)
    p_writing = db.Column(db.Float)
    
    # Ek bilgiler
    is_practice = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    admin_notes = db.Column(db.Text)
    
    # Sertifika
    certificate_hash = db.Column(db.String(64))
    certificate_generated_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # İlişkiler
    answers = db.relationship('ExamAnswer', backref='candidate', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Candidate {self.ad_soyad}>'


class Question(db.Model):
    """Soru modeli"""
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    soru_metni = db.Column(db.Text, nullable=False)
    seviye = db.Column(db.String(5), index=True)  # A1, A2, B1, B2, C1, C2
    beceri = db.Column(db.String(20), index=True)  # grammar, vocabulary, reading, listening, speaking, writing
    soru_tipi = db.Column(db.String(30), default='coktan_secmeli')  # coktan_secmeli, dogru_yanlis, bosluk_doldurma, yazili
    
    # Seçenekler ve cevap
    secenekler = db.Column(db.Text)  # JSON formatında
    dogru_cevap = db.Column(db.String(500))
    
    # Medya
    resim_url = db.Column(db.String(500))
    ses_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    kullanim_sayisi = db.Column(db.Integer, default=0)
    dogru_cevap_orani = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Question {self.id} - {self.seviye}/{self.beceri}>'


class ExamAnswer(db.Model):
    """Sınav cevabı modeli"""
    __tablename__ = 'exam_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    aday_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False, index=True)
    soru_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    verilen_cevap = db.Column(db.Text)
    dogru_mu = db.Column(db.Boolean)
    puan = db.Column(db.Float)
    sure = db.Column(db.Integer)  # Saniye cinsinden
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # İlişkiler
    question = db.relationship('Question', backref='answers', lazy=True)
    
    def __repr__(self):
        return f'<ExamAnswer {self.aday_id}-{self.soru_id}>'


class ExamTemplate(db.Model):
    """Sınav şablonu modeli"""
    __tablename__ = 'exam_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    isim = db.Column(db.String(100), nullable=False)
    aciklama = db.Column(db.Text)
    sure = db.Column(db.Integer, default=30)
    soru_sayisi = db.Column(db.Integer, default=25)
    
    # Dağılım ayarları (JSON)
    beceri_dagilimi = db.Column(db.Text)  # {"grammar": 5, "vocabulary": 5, ...}
    seviye_dagilimi = db.Column(db.Text)  # {"A1": 2, "A2": 3, ...}
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<ExamTemplate {self.isim}>'


class PasswordResetToken(db.Model):
    """Şifre sıfırlama token modeli"""
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # İlişki
    user = db.relationship('User', backref='reset_tokens', lazy=True)
    
    def is_expired(self):
        return datetime.now() > self.expires_at
    
    def __repr__(self):
        return f'<PasswordResetToken {self.token[:10]}...>'


class AuditLog(db.Model):
    """Denetim logu modeli"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # JSON formatında detaylar
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    
    # İlişki
    user = db.relationship('User', backref='audit_logs', lazy=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} - {self.created_at}>'


class EmailLog(db.Model):
    """Email log modeli"""
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200))
    email_type = db.Column(db.String(50))  # invitation, result, reset, etc.
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    error_message = db.Column(db.Text)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    sent_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<EmailLog {self.recipient} - {self.status}>'


class SystemSetting(db.Model):
    """Sistem ayarları modeli"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    value_type = db.Column(db.String(20), default='string')  # string, int, bool, json
    description = db.Column(db.String(500))
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<SystemSetting {self.key}>'

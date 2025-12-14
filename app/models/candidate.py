# -*- coding: utf-8 -*-
"""
Candidate Model - Exam takers
"""
from datetime import datetime
from app.extensions import db


class Candidate(db.Model):
    """Candidate model for exam takers"""
    __tablename__ = 'adaylar'
    
    id = db.Column(db.Integer, primary_key=True)
    ad_soyad = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), index=True)
    tc_kimlik = db.Column(db.String(11))
    cep_no = db.Column(db.String(20))
    giris_kodu = db.Column(db.String(20), unique=True, index=True)
    
    # Exam settings
    sinav_suresi = db.Column(db.Integer, default=30)
    soru_limiti = db.Column(db.Integer, default=25)
    current_difficulty = db.Column(db.String(10), default='B1')
    
    # Scores
    puan = db.Column(db.Float, default=0)
    seviye_sonuc = db.Column(db.String(10))
    band_score = db.Column(db.Float)
    
    # Per-skill scores
    p_grammar = db.Column(db.Float, default=0)
    p_vocabulary = db.Column(db.Float, default=0)
    p_reading = db.Column(db.Float, default=0)
    p_listening = db.Column(db.Float, default=0)
    p_writing = db.Column(db.Float, default=0)
    p_speaking = db.Column(db.Float, default=0)
    
    # IELTS equivalents
    ielts_reading = db.Column(db.Float)
    ielts_writing = db.Column(db.Float)
    ielts_speaking = db.Column(db.Float)
    ielts_listening = db.Column(db.Float)
    
    # Status
    sinav_durumu = db.Column(db.String(20), default='beklemede')
    baslama_tarihi = db.Column(db.DateTime)
    bitis_tarihi = db.Column(db.DateTime)
    
    # Certificate
    certificate_hash = db.Column(db.String(64), unique=True)
    
    # Company
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    
    # Metadata
    is_practice = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    admin_notes = db.Column(db.Text)
    tags = db.Column(db.Text)  # JSON tags
    consent_given = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='candidates')
    answers = db.relationship('ExamAnswer', backref='candidate', lazy='dynamic')
    recordings = db.relationship('SpeakingRecording', backref='candidate', lazy='dynamic')
    
    def calculate_total_score(self):
        """Calculate weighted total score"""
        weights = {
            'grammar': 0.15,
            'vocabulary': 0.15,
            'reading': 0.20,
            'listening': 0.20,
            'writing': 0.15,
            'speaking': 0.15
        }
        
        total = (
            (self.p_grammar or 0) * weights['grammar'] +
            (self.p_vocabulary or 0) * weights['vocabulary'] +
            (self.p_reading or 0) * weights['reading'] +
            (self.p_listening or 0) * weights['listening'] +
            (self.p_writing or 0) * weights['writing'] +
            (self.p_speaking or 0) * weights['speaking']
        )
        
        self.puan = round(total, 2)
        return self.puan
    
    def get_cefr_level(self):
        """Get CEFR level from score"""
        from app.services.cefr_mapper import score_to_cefr
        return score_to_cefr(self.puan)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'ad_soyad': self.ad_soyad,
            'email': self.email,
            'giris_kodu': self.giris_kodu,
            'puan': self.puan,
            'seviye_sonuc': self.seviye_sonuc,
            'band_score': self.band_score,
            'sinav_durumu': self.sinav_durumu,
            'skills': {
                'grammar': self.p_grammar,
                'vocabulary': self.p_vocabulary,
                'reading': self.p_reading,
                'listening': self.p_listening,
                'writing': self.p_writing,
                'speaking': self.p_speaking
            }
        }
    
    def __repr__(self):
        return f'<Candidate {self.ad_soyad}>'

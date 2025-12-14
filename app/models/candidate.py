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

    # ====================
    # NEW: TC Kimlik Authentication Fields
    # ====================
    tc_kimlik_hash = db.Column(db.String(64), nullable=True, index=True)  # SHA256 hash of TC
    exam_code = db.Column(db.String(20), unique=True, nullable=True, index=True)  # Unique exam access code
    exam_code_expires = db.Column(db.DateTime, nullable=True)  # Code expiration
    exam_code_sent = db.Column(db.Boolean, default=False)  # Email sent flag
    login_count = db.Column(db.Integer, default=0)  # Login tracking
    last_login = db.Column(db.DateTime, nullable=True)  # Last login time
    aktif = db.Column(db.Boolean, default=True)  # Active status

    # Exam settings
    sinav_suresi = db.Column(db.Integer, default=30)  # minutes (total exam)
    soru_suresi = db.Column(db.Integer, default=60)  # seconds per question (0 = unlimited)
    soru_limiti = db.Column(db.Integer, default=25)
    current_difficulty = db.Column(db.String(10), default='B1')

    # Scores
    puan = db.Column(db.Float, default=0)
    toplam_puan = db.Column(db.Float, default=0)
    seviye_sonuc = db.Column(db.String(10))
    cefr_seviye = db.Column(db.String(10))
    band_score = db.Column(db.Float)

    # Per-skill scores
    p_grammar = db.Column(db.Float, default=0)
    p_vocabulary = db.Column(db.Float, default=0)
    p_reading = db.Column(db.Float, default=0)
    p_listening = db.Column(db.Float, default=0)
    p_writing = db.Column(db.Float, default=0)
    p_speaking = db.Column(db.Float, default=0)
    
    # Alternative score column names (for compatibility)
    grammar_puan = db.Column(db.Float, default=0)
    vocabulary_puan = db.Column(db.Float, default=0)
    reading_puan = db.Column(db.Float, default=0)
    listening_puan = db.Column(db.Float, default=0)
    writing_puan = db.Column(db.Float, default=0)
    speaking_puan = db.Column(db.Float, default=0)

    # IELTS equivalents
    ielts_reading = db.Column(db.Float)
    ielts_writing = db.Column(db.Float)
    ielts_speaking = db.Column(db.Float)
    ielts_listening = db.Column(db.Float)

    # Status
    durum = db.Column(db.String(20), default='beklemede')  # beklemede, sinavda, tamamlandi
    sinav_durumu = db.Column(db.String(20), default='beklemede')
    sinav_baslama = db.Column(db.DateTime)
    sinav_bitis = db.Column(db.DateTime)
    baslama_tarihi = db.Column(db.DateTime)
    bitis_tarihi = db.Column(db.DateTime)

    # ====================
    # Pause/Resume support
    # ====================
    is_paused = db.Column(db.Boolean, default=False)
    paused_at = db.Column(db.DateTime)
    total_paused_seconds = db.Column(db.Integer, default=0)
    pause_count = db.Column(db.Integer, default=0)
    last_question_id = db.Column(db.Integer)  # Resume from this question

    # Certificate
    certificate_hash = db.Column(db.String(64), unique=True)

    # Company
    firma_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)

    # Metadata
    is_practice = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    admin_notes = db.Column(db.Text)
    tags = db.Column(db.Text)  # JSON tags
    consent_given = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Analytics
    reading_wpm = db.Column(db.Float)  # Words per minute for reading
    listening_replays_used = db.Column(db.Integer, default=0)  # Number of replay uses
    benchmark_percentile = db.Column(db.Float)  # Compared to other candidates

    # Trust/Fraud detection
    trust_score = db.Column(db.Float, default=100.0)

    # Relationships
    company = db.relationship('Company', foreign_keys=[sirket_id], backref='candidates')
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

        # Use whichever score columns are populated
        grammar = self.p_grammar or self.grammar_puan or 0
        vocabulary = self.p_vocabulary or self.vocabulary_puan or 0
        reading = self.p_reading or self.reading_puan or 0
        listening = self.p_listening or self.listening_puan or 0
        writing = self.p_writing or self.writing_puan or 0
        speaking = self.p_speaking or self.speaking_puan or 0

        total = (
            grammar * weights['grammar'] +
            vocabulary * weights['vocabulary'] +
            reading * weights['reading'] +
            listening * weights['listening'] +
            writing * weights['writing'] +
            speaking * weights['speaking']
        )

        self.puan = round(total, 2)
        self.toplam_puan = self.puan
        return self.puan

    def get_cefr_level(self):
        """Get CEFR level from score - inline to avoid circular import"""
        score = self.puan or self.toplam_puan or 0
        if score >= 90:
            return 'C2'
        elif score >= 75:
            return 'C1'
        elif score >= 60:
            return 'B2'
        elif score >= 40:
            return 'B1'
        elif score >= 20:
            return 'A2'
        else:
            return 'A1'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'ad_soyad': self.ad_soyad,
            'email': self.email,
            'giris_kodu': self.giris_kodu,
            'exam_code': self.exam_code,
            'puan': self.puan,
            'toplam_puan': self.toplam_puan,
            'seviye_sonuc': self.seviye_sonuc,
            'cefr_seviye': self.cefr_seviye,
            'band_score': self.band_score,
            'durum': self.durum,
            'sinav_durumu': self.sinav_durumu,
            'is_paused': self.is_paused,
            'pause_count': self.pause_count,
            'skills': {
                'grammar': self.p_grammar or self.grammar_puan,
                'vocabulary': self.p_vocabulary or self.vocabulary_puan,
                'reading': self.p_reading or self.reading_puan,
                'listening': self.p_listening or self.listening_puan,
                'writing': self.p_writing or self.writing_puan,
                'speaking': self.p_speaking or self.speaking_puan
            }
        }

    def __repr__(self):
        return f'<Candidate {self.ad_soyad}>'

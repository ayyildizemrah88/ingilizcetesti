# -*- coding: utf-8 -*-
"""
Question Models - All question types
"""
from datetime import datetime
from app.extensions import db


class Question(db.Model):
    """Main question model for MCQ and open-ended questions"""
    __tablename__ = 'sorular'
    
    id = db.Column(db.Integer, primary_key=True)
    soru_metni = db.Column(db.Text, nullable=False)
    secenek_a = db.Column(db.Text)
    secenek_b = db.Column(db.Text)
    secenek_c = db.Column(db.Text)
    secenek_d = db.Column(db.Text)
    dogru_cevap = db.Column(db.String(1))  # A, B, C, D
    
    # Categorization
    kategori = db.Column(db.String(50), index=True)  # grammar, vocabulary, reading
    zorluk = db.Column(db.String(10), default='B1', index=True)  # A1-C2
    soru_tipi = db.Column(db.String(20), default='SECMELI')  # SECMELI, YAZILI, KONUSMA
    
    # Metadata
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # IRT parameters for CAT
    irt_discrimination = db.Column(db.Float, default=1.0)  # 'a' parameter
    irt_difficulty = db.Column(db.Float)  # 'b' parameter
    irt_guessing = db.Column(db.Float, default=0.25)  # 'c' parameter
    
    # Calibration Analytics
    times_answered = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)
    calculated_difficulty = db.Column(db.Float)  # Actual measured difficulty
    calibration_warning = db.Column(db.Boolean, default=False)  # Mismatch flag
    last_calibrated = db.Column(db.DateTime)
    
    # Relationships
    company = db.relationship('Company', backref='questions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'soru_metni': self.soru_metni,
            'secenek_a': self.secenek_a,
            'secenek_b': self.secenek_b,
            'secenek_c': self.secenek_c,
            'secenek_d': self.secenek_d,
            'kategori': self.kategori,
            'zorluk': self.zorluk,
            'soru_tipi': self.soru_tipi
        }
    
    def __repr__(self):
        return f'<Question {self.id}: {self.kategori}/{self.zorluk}>'


class ListeningAudio(db.Model):
    """Audio files for listening comprehension"""
    __tablename__ = 'listening_audio'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    audio_url = db.Column(db.Text)
    transcript = db.Column(db.Text)
    duration_seconds = db.Column(db.Integer)
    difficulty = db.Column(db.String(10), default='B1')
    
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('ListeningQuestion', backref='audio', lazy='dynamic')
    
    def __repr__(self):
        return f'<ListeningAudio {self.title}>'


class ListeningQuestion(db.Model):
    """Questions linked to listening audio"""
    __tablename__ = 'listening_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    audio_id = db.Column(db.Integer, db.ForeignKey('listening_audio.id'), index=True)
    soru_metni = db.Column(db.Text)
    secenek_a = db.Column(db.Text)
    secenek_b = db.Column(db.Text)
    secenek_c = db.Column(db.Text)
    secenek_d = db.Column(db.Text)
    dogru_cevap = db.Column(db.String(1))
    soru_sirasi = db.Column(db.Integer, default=1)
    
    def __repr__(self):
        return f'<ListeningQuestion {self.id}>'


class ReadingPassage(db.Model):
    """Reading comprehension passages"""
    __tablename__ = 'reading_passages_bank'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    passage_text = db.Column(db.Text, nullable=False)
    word_count = db.Column(db.Integer)
    topic = db.Column(db.String(100))
    difficulty = db.Column(db.String(10), default='B1')
    
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('ReadingQuestion', backref='passage', lazy='dynamic')
    
    def __repr__(self):
        return f'<ReadingPassage {self.title}>'


class ReadingQuestion(db.Model):
    """Questions linked to reading passages"""
    __tablename__ = 'reading_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    passage_id = db.Column(db.Integer, db.ForeignKey('reading_passages_bank.id'), index=True)
    soru_metni = db.Column(db.Text)
    soru_tipi = db.Column(db.String(20), default='MCQ')  # MCQ, TRUE_FALSE, FILL_BLANK, MATCHING
    secenek_a = db.Column(db.Text)
    secenek_b = db.Column(db.Text)
    secenek_c = db.Column(db.Text)
    secenek_d = db.Column(db.Text)
    dogru_cevap = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<ReadingQuestion {self.id}>'

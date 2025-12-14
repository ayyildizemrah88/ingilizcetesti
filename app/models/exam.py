# -*- coding: utf-8 -*-
"""
Exam Models - Templates, answers, recordings
"""
from datetime import datetime
from app.extensions import db


class ExamTemplate(db.Model):
    """Exam template/configuration"""
    __tablename__ = 'sinav_sablonlari'
    
    id = db.Column(db.Integer, primary_key=True)
    isim = db.Column(db.String(255), nullable=False)
    sinav_suresi = db.Column(db.Integer, default=30)  # minutes
    soru_limiti = db.Column(db.Integer, default=25)
    baslangic_seviyesi = db.Column(db.String(10), default='B1')
    
    # Section configuration (JSON)
    sections_config = db.Column(db.Text)  # JSON: {grammar: 10, vocabulary: 10, ...}
    
    # Settings
    is_adaptive = db.Column(db.Boolean, default=False)  # Use CAT
    randomize_questions = db.Column(db.Boolean, default=True)
    show_results = db.Column(db.Boolean, default=True)
    
    sirket_id = db.Column(db.Integer, db.ForeignKey('sirketler.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sections = db.relationship('ExamSection', backref='template', lazy='dynamic')
    
    def __repr__(self):
        return f'<ExamTemplate {self.isim}>'


class ExamSection(db.Model):
    """Exam sections configuration"""
    __tablename__ = 'sinav_bolum_ayarlari'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('sinav_sablonlari.id'), index=True)
    
    section_name = db.Column(db.String(50))  # grammar, vocabulary, reading, etc.
    section_order = db.Column(db.Integer, default=1)
    question_count = db.Column(db.Integer, default=5)
    time_limit = db.Column(db.Integer)  # seconds, per section
    
    def __repr__(self):
        return f'<ExamSection {self.section_name}>'


class ExamAnswer(db.Model):
    """Candidate answers"""
    __tablename__ = 'cevaplar'
    
    id = db.Column(db.Integer, primary_key=True)
    aday_id = db.Column(db.Integer, db.ForeignKey('adaylar.id'), index=True)
    soru_id = db.Column(db.Integer, db.ForeignKey('sorular.id'), index=True)
    
    verilen_cevap = db.Column(db.Text)
    dogru_mu = db.Column(db.Boolean, default=False)
    
    # Timing
    response_time_ms = db.Column(db.Integer)  # Time to answer in milliseconds
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    question = db.relationship('Question', backref='answers')
    
    def __repr__(self):
        return f'<ExamAnswer {self.aday_id}:{self.soru_id}>'


class SpeakingRecording(db.Model):
    """Speaking test recordings with AI analysis"""
    __tablename__ = 'speaking_recordings'
    
    id = db.Column(db.Integer, primary_key=True)
    aday_id = db.Column(db.Integer, db.ForeignKey('adaylar.id'), index=True)
    soru_id = db.Column(db.Integer)
    
    audio_blob = db.Column(db.Text)  # Base64 encoded audio
    duration_seconds = db.Column(db.Integer)
    transcript = db.Column(db.Text)
    
    # AI scores (JSON)
    ai_score_json = db.Column(db.Text)  # {fluency, pronunciation, grammar, vocabulary, overall}
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_scores(self):
        """Parse AI scores from JSON"""
        import json
        if self.ai_score_json:
            return json.loads(self.ai_score_json)
        return {}
    
    def __repr__(self):
        return f'<SpeakingRecording {self.id}>'


class WritingAnswer(db.Model):
    """Written answers with AI evaluation"""
    __tablename__ = 'yazili_cevaplar'
    
    id = db.Column(db.Integer, primary_key=True)
    aday_id = db.Column(db.Integer, db.ForeignKey('adaylar.id'), index=True)
    soru_id = db.Column(db.Integer)
    
    essay_text = db.Column(db.Text)
    word_count = db.Column(db.Integer)
    
    # AI evaluation
    ai_score = db.Column(db.Float)
    ai_feedback = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WritingAnswer {self.id}>'

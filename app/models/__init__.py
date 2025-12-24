# -*- coding: utf-8 -*-
"""
SQLAlchemy Models Package
"""
from app.extensions import db

# Import all models for easy access
from app.models.user import User
from app.models.candidate import Candidate
from app.models.question import Question, ListeningAudio, ListeningQuestion, ReadingPassage, ReadingQuestion
from app.models.exam import ExamTemplate, ExamSection, ExamAnswer, SpeakingRecording
from app.models.company import Company
from app.models.audit_log import AuditLog

# Create alias for Answer (commonly used name for ExamAnswer)
Answer = ExamAnswer

__all__ = [
    'db',
    'User',
    'Candidate', 
    'Question',
    'ListeningAudio',
    'ListeningQuestion',
    'ReadingPassage',
    'ReadingQuestion',
    'ExamTemplate',
    'ExamSection',
    'ExamAnswer',
    'Answer',  # Alias for ExamAnswer
    'SpeakingRecording',
    'Company',
    'AuditLog'
]

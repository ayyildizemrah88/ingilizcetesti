# -*- coding: utf-8 -*-
"""
AI Tasks Module - Modular AI evaluation system
"""
from app.tasks.ai.transcription import transcribe_audio
from app.tasks.ai.speaking import evaluate_speaking, evaluate_with_gemini
from app.tasks.ai.writing import evaluate_writing, evaluate_writing_with_gemini
from app.tasks.ai.study_plan import generate_study_plan
from app.tasks.ai.plagiarism import check_plagiarism, check_ai_generated
from app.tasks.ai.audio_analysis import analyze_audio_environment, detect_multiple_speakers
from app.tasks.ai.utils import capture_ai_error, default_scores

__all__ = [
    # Celery Tasks
    'evaluate_speaking',
    'evaluate_writing', 
    'generate_study_plan',
    # Helper functions
    'transcribe_audio',
    'evaluate_with_gemini',
    'evaluate_writing_with_gemini',
    'check_plagiarism',
    'check_ai_generated',
    'analyze_audio_environment',
    'detect_multiple_speakers',
    'capture_ai_error',
    'default_scores',
]

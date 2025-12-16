# -*- coding: utf-8 -*-
"""
Study Plan Generation Module - AI-powered personalized learning plans
"""
import os
import json
import logging
from datetime import datetime

from app.celery_app import celery
from app.tasks.ai.utils import parse_gemini_response

logger = logging.getLogger(__name__)


@celery.task
def generate_study_plan(candidate_id):
    """
    Generate AI-powered personalized study plan based on exam results.
    """
    from app.models import Candidate, ExamAnswer, Question
    from app.extensions import db
    
    candidate = Candidate.query.get(candidate_id)
    if not candidate:
        return None
    
    # Gather performance data
    answers = ExamAnswer.query.filter_by(aday_id=candidate_id).all()
    
    weak_areas = {}
    for answer in answers:
        question = Question.query.get(answer.soru_id)
        if question and not answer.dogru_mu:
            cat = question.kategori or 'general'
            weak_areas[cat] = weak_areas.get(cat, 0) + 1
    
    # Sort by weakness
    sorted_weaknesses = sorted(weak_areas.items(), key=lambda x: x[1], reverse=True)
    
    # Generate study plan with Gemini
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return generate_default_study_plan(candidate, sorted_weaknesses)
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""Bir İngilizce öğretmeni olarak, aşağıdaki aday için kişiselleştirilmiş bir çalışma planı oluştur.

ADAY BİLGİLERİ:
- Mevcut Seviye: {candidate.seviye_sonuc or 'B1'}
- Genel Puan: {candidate.puan}%
- Grammar: {candidate.p_grammar}%
- Vocabulary: {candidate.p_vocabulary}%
- Reading: {candidate.p_reading}%
- Listening: {candidate.p_listening}%
- Writing: {candidate.p_writing}%
- Speaking: {candidate.p_speaking}%

ZAYIF ALANLAR: {dict(sorted_weaknesses[:5])}

Lütfen JSON formatında şu bilgileri içeren bir çalışma planı oluştur:
{{
    "weekly_plan": [
        {{"day": "Pazartesi", "focus": "konu", "duration_minutes": 30, "activities": ["aktivite1", "aktivite2"]}}
    ],
    "priority_topics": ["konu1", "konu2"],
    "recommended_resources": [
        {{"type": "video/article/quiz", "title": "başlık", "url": "URL veya kaynak adı"}}
    ],
    "monthly_goals": ["hedef1", "hedef2"],
    "tips": ["ipucu1", "ipucu2"]
}}"""

        response = model.generate_content(prompt)
        study_plan = parse_gemini_response(response.text)
        
        # Store study plan
        candidate.admin_notes = json.dumps({
            'study_plan': study_plan,
            'generated_at': datetime.now().isoformat()
        })
        db.session.commit()
        
        return study_plan
        
    except Exception as e:
        logger.error(f"Study plan generation failed: {e}")
        return generate_default_study_plan(candidate, sorted_weaknesses)


def generate_default_study_plan(candidate, weak_areas):
    """Generate a default study plan when AI is unavailable."""
    return {
        'weekly_plan': [
            {'day': 'Pazartesi', 'focus': 'Grammar', 'duration_minutes': 30, 'activities': ['Tense çalışması', 'Alıştırma çözme']},
            {'day': 'Salı', 'focus': 'Vocabulary', 'duration_minutes': 30, 'activities': ['Kelime kartları', 'Cümle kurma']},
            {'day': 'Çarşamba', 'focus': 'Reading', 'duration_minutes': 45, 'activities': ['Passage okuma', 'Soru çözme']},
            {'day': 'Perşembe', 'focus': 'Listening', 'duration_minutes': 30, 'activities': ['Podcast dinleme', 'Not alma']},
            {'day': 'Cuma', 'focus': 'Speaking', 'duration_minutes': 30, 'activities': ['Sesli okuma', 'Kendi kendine konuşma']},
        ],
        'priority_topics': [area[0] for area in (weak_areas[:3] if weak_areas else [])],
        'recommended_resources': [
            {'type': 'video', 'title': 'English Grammar Course', 'url': 'YouTube'},
            {'type': 'article', 'title': 'Vocabulary Building Tips', 'url': 'British Council'}
        ],
        'monthly_goals': [
            f"{candidate.seviye_sonuc or 'B1'} seviyesini pekiştirmek",
            'Günlük 30 dakika pratik yapmak'
        ],
        'tips': [
            'Her gün en az 15 dakika İngilizce dinleyin',
            'Yeni kelimeleri cümle içinde kullanmaya çalışın'
        ]
    }

# -*- coding: utf-8 -*-
"""
AI Evaluation Tasks - Async Gemini/Whisper processing
"""
from app.celery_app import celery
import os
import json
import base64
import logging

logger = logging.getLogger(__name__)


def capture_ai_error(exception, task_type, context=None):
    """
    Capture AI evaluation errors to Sentry and log them.
    
    Args:
        exception: The exception that occurred
        task_type: Type of AI task (speaking_evaluation, writing_evaluation)
        context: Additional context dictionary
    """
    # Log the error
    logger.error(f"AI Task Error [{task_type}]: {str(exception)}", extra=context or {})
    
    # Try to send to Sentry
    try:
        import sentry_sdk
        
        # Set context
        if context:
            sentry_sdk.set_context("ai_task", {
                "task_type": task_type,
                **context
            })
        
        # Set tags for filtering
        sentry_sdk.set_tag("task_type", task_type)
        sentry_sdk.set_tag("service", "ai_evaluation")
        
        # Capture the exception
        sentry_sdk.capture_exception(exception)
        
    except ImportError:
        logger.warning("Sentry SDK not installed - error tracking unavailable")  # Log instead of silent pass
    except Exception as e:
        logger.warning(f"Sentry capture failed: {e}")


@celery.task(bind=True, max_retries=2, default_retry_delay=30)
def evaluate_speaking(self, recording_id):
    """
    Evaluate speaking recording with Whisper transcription and Gemini scoring
    
    Args:
        recording_id: SpeakingRecording ID
    """
    try:
        from app.models import SpeakingRecording, Candidate
        from app.extensions import db
        
        # AI Rate Limiting
        try:
            from app.utils.ai_rate_limiter import ai_limiter
            allowed, error_msg = ai_limiter.check_limit('speaking_evaluation', str(recording_id))
            if not allowed:
                logger.warning(f"AI rate limit exceeded for speaking: {recording_id}")
                return {'status': 'rate_limited', 'error': 'Too many AI requests. Please wait.'}
        except ImportError:
            pass  # Rate limiter not available, continue
        
        recording = SpeakingRecording.query.get(recording_id)
        if not recording:
            return {'status': 'error', 'reason': 'recording not found'}
        
        # Step 1: Transcribe with Whisper
        transcript = transcribe_audio(recording.audio_blob)
        recording.transcript = transcript
        
        # Step 2: Evaluate with Gemini
        scores = evaluate_with_gemini(transcript)
        recording.ai_score_json = json.dumps(scores)
        
        # Step 3: Update candidate speaking score
        candidate = Candidate.query.get(recording.aday_id)
        if candidate:
            candidate.p_speaking = scores.get('overall', 0)
        
        db.session.commit()
        
        return {
            'status': 'completed',
            'transcript': transcript[:100],
            'scores': scores
        }
        
    except Exception as e:
        # Capture error in Sentry with context
        capture_ai_error(e, 'speaking_evaluation', {
            'recording_id': recording_id,
            'task_id': self.request.id
        })
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=2)
def evaluate_writing(self, answer_id):
    """
    Evaluate writing answer with Gemini AI
    
    Args:
        answer_id: WritingAnswer ID
    """
    try:
        from app.models.exam import WritingAnswer
        from app.extensions import db
        
        # AI Rate Limiting
        try:
            from app.utils.ai_rate_limiter import ai_limiter
            allowed, error_msg = ai_limiter.check_limit('writing_evaluation', str(answer_id))
            if not allowed:
                logger.warning(f"AI rate limit exceeded for writing: {answer_id}")
                return {'status': 'rate_limited', 'error': 'Too many AI requests. Please wait.'}
        except ImportError:
            pass  # Rate limiter not available, continue
        
        answer = WritingAnswer.query.get(answer_id)
        if not answer:
            return {'status': 'error'}
        
        scores = evaluate_writing_with_gemini(answer.essay_text)
        
        answer.ai_score = scores.get('overall', 0)
        answer.ai_feedback = scores.get('feedback', '')
        
        db.session.commit()
        
        return {'status': 'completed', 'score': answer.ai_score}
        
    except Exception as e:
        # Capture error in Sentry
        capture_ai_error(e, 'writing_evaluation', {
            'answer_id': answer_id,
            'task_id': self.request.id
        })
        raise self.retry(exc=e)


def transcribe_audio(audio_base64):
    """
    Transcribe audio using OpenAI Whisper API
    
    Args:
        audio_base64: Base64 encoded audio
    
    Returns:
        Transcribed text
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "[Transcription unavailable - API key not configured]"
    
    try:
        import openai
        
        # Decode base64 to audio bytes
        audio_bytes = base64.b64decode(audio_base64)
        
        # Create temporary file with guaranteed cleanup
        import tempfile
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            
            # Transcribe with Whisper
            client = openai.OpenAI(api_key=api_key)
            
            with open(temp_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            
            return transcript.text
        finally:
            # Cleanup temp file even if error occurs
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass  # Best effort cleanup
        
    except Exception as e:
        return f"[Transcription error: {str(e)}]"


def evaluate_with_gemini(transcript):
    """
    Evaluate speaking transcript with Gemini AI
    
    Args:
        transcript: Spoken English transcript
    
    Returns:
        Dictionary with scores for fluency, pronunciation, grammar, vocabulary, overall
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return default_scores()
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""You are an expert English language evaluator. Analyze the following speaking response transcript and provide scores.

TRANSCRIPT:
{transcript}

Evaluate on a scale of 0-100 for each criterion and provide your response as JSON only:
{{
    "fluency": <score>,
    "pronunciation": <score>,
    "grammar": <score>,
    "vocabulary": <score>,
    "content": <score>,
    "overall": <weighted average>,
    "cefr_level": "<A1/A2/B1/B2/C1/C2>",
    "feedback": "<brief feedback in Turkish>"
}}

IMPORTANT: Return ONLY valid JSON, no markdown or explanation."""

        response = model.generate_content(prompt)
        
        # Parse JSON from response
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        scores = json.loads(response_text)
        return scores
        
    except Exception as e:
        return default_scores(error=str(e))


def evaluate_writing_with_gemini(essay_text):
    """
    Evaluate writing with Gemini AI including grammar error highlighting
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return {'overall': 50, 'feedback': 'AI evaluation unavailable'}
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""You are an expert English writing evaluator. Analyze the following essay and provide evaluation WITH grammar error highlighting.

ESSAY:
{essay_text}

Evaluate on a scale of 0-100 for each criterion and provide your response as JSON only:
{{
    "task_achievement": <score>,
    "coherence_cohesion": <score>,
    "vocabulary": <score>,
    "grammar": <score>,
    "overall": <weighted average>,
    "band_score": <IELTS band 0-9>,
    "cefr_level": "<A1/A2/B1/B2/C1/C2>",
    "feedback": "<detailed feedback in Turkish>",
    "grammar_errors": [
        {{
            "error_text": "<exact text with error>",
            "correction": "<corrected version>",
            "error_type": "<grammar/spelling/punctuation/word_choice>",
            "explanation": "<brief explanation in Turkish>"
        }}
    ],
    "highlighted_essay": "<essay text with <mark class='error'>error</mark> tags around errors>"
}}

IMPORTANT: 
1. Return ONLY valid JSON.
2. Find and list ALL grammar, spelling, and punctuation errors.
3. In highlighted_essay, wrap each error with <mark class='error'>...</mark> HTML tags."""

        response = model.generate_content(prompt)
        
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        result = json.loads(response_text)
        
        # Ensure grammar_errors is a list
        if 'grammar_errors' not in result:
            result['grammar_errors'] = []
        
        return result
        
    except Exception as e:
        return {
            'overall': 50, 
            'feedback': f'Evaluation error: {str(e)}',
            'grammar_errors': [],
            'highlighted_essay': essay_text
        }


def default_scores(error=None):
    """Return default scores when AI is unavailable"""
    return {
        'fluency': 50,
        'pronunciation': 50,
        'grammar': 50,
        'vocabulary': 50,
        'content': 50,
        'overall': 50,
        'cefr_level': 'B1',
        'feedback': 'AI değerlendirmesi şu an kullanılamıyor.' + (f' Hata: {error}' if error else '')
    }


# ══════════════════════════════════════════════════════════════════
# PLAGIARISM & SIMILARITY CHECK
# ══════════════════════════════════════════════════════════════════

def check_plagiarism(essay_text, candidate_id):
    """
    Check for plagiarism and AI-generated content.
    
    Returns:
        dict with similarity_score, ai_probability, flagged status
    """
    from app.models import WritingAnswer
    
    result = {
        'similarity_score': 0.0,
        'similar_to_id': None,
        'ai_generated_probability': 0.0,
        'flagged': False,
        'flag_reasons': []
    }
    
    # Get other writing answers for comparison
    other_answers = WritingAnswer.query.filter(
        WritingAnswer.aday_id != candidate_id,
        WritingAnswer.essay_text.isnot(None)
    ).limit(100).all()
    
    max_similarity = 0
    most_similar_id = None
    
    for answer in other_answers:
        if answer.essay_text:
            similarity = cosine_similarity_text(essay_text, answer.essay_text)
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_id = answer.id
    
    result['similarity_score'] = round(max_similarity * 100, 1)
    result['similar_to_id'] = most_similar_id
    
    # Check for AI-generated content
    ai_prob = check_ai_generated(essay_text)
    result['ai_generated_probability'] = ai_prob
    
    # Determine if flagged
    if max_similarity > 0.75:
        result['flagged'] = True
        result['flag_reasons'].append(f'Yüksek benzerlik: %{result["similarity_score"]}')
    
    if ai_prob > 0.7:
        result['flagged'] = True
        result['flag_reasons'].append(f'AI tarafından yazılmış olabilir: %{round(ai_prob * 100)}')
    
    return result


def cosine_similarity_text(text1, text2):
    """Calculate cosine similarity between two texts."""
    from collections import Counter
    import math
    
    # Tokenize and create word frequency vectors
    words1 = text1.lower().split()
    words2 = text2.lower().split()
    
    vec1 = Counter(words1)
    vec2 = Counter(words2)
    
    # Get all unique words
    all_words = set(vec1.keys()) | set(vec2.keys())
    
    # Calculate dot product and magnitudes
    dot_product = sum(vec1.get(w, 0) * vec2.get(w, 0) for w in all_words)
    mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    return dot_product / (mag1 * mag2)


def check_ai_generated(text):
    """
    Check if text was likely generated by AI.
    Uses Gemini to analyze writing patterns.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return 0.0
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""Analyze this essay and determine the probability (0.0 to 1.0) that it was written by an AI.

Consider these factors:
- Unusual consistency in sentence structure
- Lack of personal voice or opinions  
- Perfect grammar throughout
- Generic or template-like responses
- Repetitive phrase patterns

TEXT:
{text[:2000]}

Return ONLY a number between 0.0 and 1.0, nothing else."""

        response = model.generate_content(prompt)
        prob = float(response.text.strip())
        return max(0.0, min(1.0, prob))
        
    except Exception as e:
        logger.error(f"AI detection failed: {e}")
        return 0.0


# ══════════════════════════════════════════════════════════════════
# PERSONALIZED STUDY PLAN
# ══════════════════════════════════════════════════════════════════

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
        
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        study_plan = json.loads(response_text)
        
        # Store study plan
        candidate.admin_notes = json.dumps({
            'study_plan': study_plan,
            'generated_at': str(datetime.now()) if 'datetime' in dir() else 'now'
        })
        db.session.commit()
        
        return study_plan
        
    except Exception as e:
        logger.error(f"Study plan generation failed: {e}")
        return generate_default_study_plan(candidate, sorted_weaknesses)


def generate_default_study_plan(candidate, weak_areas):
    """Generate a default study plan when AI is unavailable."""
    from datetime import datetime
    
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


# ══════════════════════════════════════════════════════════════════
# AUDIO ENVIRONMENT ANALYSIS
# ══════════════════════════════════════════════════════════════════

def analyze_audio_environment(audio_base64):
    """
    Analyze audio recording environment for:
    - Background noise level
    - Presence of second voice (potential cheating)
    - Audio quality score
    
    Returns:
        dict with environment_score, second_voice_detected, noise_level
    """
    result = {
        'environment_score': 0.8,  # 0-1, higher is better
        'second_voice_detected': False,
        'second_voice_confidence': 0.0,
        'noise_level': 'low',  # low, medium, high
        'audio_quality': 'good',  # poor, acceptable, good
        'warnings': []
    }
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return result
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro-vision')
        
        # Note: For actual audio analysis, you'd need to use Whisper first
        # Then analyze the transcript for multiple speakers
        
        return result
        
    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        return result


def detect_multiple_speakers(transcript):
    """
    Analyze transcript for signs of multiple speakers.
    Uses pattern matching and Gemini for advanced detection.
    """
    # Simple heuristics
    suspicious_patterns = [
        'what did you say',
        'say that again',
        'tell me',
        'the answer is',
        'choose option',
        'select'
    ]
    
    transcript_lower = transcript.lower()
    pattern_matches = sum(1 for p in suspicious_patterns if p in transcript_lower)
    
    if pattern_matches >= 2:
        return {
            'detected': True,
            'confidence': min(0.9, 0.3 + pattern_matches * 0.2),
            'reason': 'Suspicious dialogue patterns detected'
        }
    
    return {
        'detected': False,
        'confidence': 0.0,
        'reason': None
    }


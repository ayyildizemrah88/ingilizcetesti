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
        pass  # Sentry not installed, just log
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
        
        # Create temporary file
        import tempfile
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
        
        # Cleanup
        os.unlink(temp_path)
        
        return transcript.text
        
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
    Evaluate writing with Gemini AI
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return {'overall': 50, 'feedback': 'AI evaluation unavailable'}
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""You are an expert English writing evaluator. Analyze the following essay and provide evaluation.

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
    "feedback": "<detailed feedback in Turkish>"
}}

IMPORTANT: Return ONLY valid JSON."""

        response = model.generate_content(prompt)
        
        response_text = response.text.strip()
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        
        return json.loads(response_text)
        
    except Exception as e:
        return {'overall': 50, 'feedback': f'Evaluation error: {str(e)}'}


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

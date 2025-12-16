# -*- coding: utf-8 -*-
"""
Speaking Evaluation Module - Gemini-based speaking assessment
"""
import os
import json
import logging

from app.celery_app import celery
from app.tasks.ai.utils import capture_ai_error, default_scores, parse_gemini_response
from app.tasks.ai.transcription import transcribe_audio

logger = logging.getLogger(__name__)


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
        
        # Step 1: Get audio data (from file or legacy BLOB)
        audio_data = recording.get_audio_base64()
        if not audio_data:
            return {'status': 'error', 'reason': 'audio not found'}
        
        # Step 2: Transcribe with Whisper
        transcript = transcribe_audio(audio_data)
        recording.transcript = transcript
        
        # Step 3: Evaluate with Gemini
        scores = evaluate_with_gemini(transcript)
        recording.ai_score_json = json.dumps(scores)
        
        # Step 4: Update candidate speaking score
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
        scores = parse_gemini_response(response.text)
        return scores
        
    except Exception as e:
        logger.error(f"Gemini speaking evaluation error: {e}")
        return default_scores(error=str(e))

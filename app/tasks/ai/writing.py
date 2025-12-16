# -*- coding: utf-8 -*-
"""
Writing Evaluation Module - Gemini-based writing assessment
"""
import os
import json
import logging

from app.celery_app import celery
from app.tasks.ai.utils import capture_ai_error, parse_gemini_response

logger = logging.getLogger(__name__)


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
        result = parse_gemini_response(response.text)
        
        # Ensure grammar_errors is a list
        if 'grammar_errors' not in result:
            result['grammar_errors'] = []
        
        return result
        
    except Exception as e:
        logger.error(f"Gemini writing evaluation error: {e}")
        return {
            'overall': 50, 
            'feedback': f'Evaluation error: {str(e)}',
            'grammar_errors': [],
            'highlighted_essay': essay_text
        }

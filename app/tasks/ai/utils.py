# -*- coding: utf-8 -*-
"""
AI Tasks Utilities - Common helpers for AI evaluation
"""
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
        logger.warning("Sentry SDK not installed - error tracking unavailable")
    except Exception as e:
        logger.warning(f"Sentry capture failed: {e}")


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


def parse_gemini_response(response_text):
    """
    Parse JSON response from Gemini, handling markdown code blocks.
    
    Args:
        response_text: Raw response text from Gemini
        
    Returns:
        Parsed JSON dictionary
    """
    import json
    
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    
    return json.loads(text)


def get_gemini_model():
    """Get configured Gemini model."""
    import os
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return None
    
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    return genai.GenerativeModel('gemini-pro')

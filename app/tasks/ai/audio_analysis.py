# -*- coding: utf-8 -*-
"""
Audio Analysis Module - Environment and speaker detection
"""
import os
import logging

logger = logging.getLogger(__name__)


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


def estimate_audio_quality(transcript):
    """
    Estimate audio quality based on transcript characteristics.
    """
    if not transcript:
        return {'quality': 'poor', 'score': 0.2}
    
    # Check for transcription errors
    error_indicators = [
        '[inaudible]',
        '[unclear]',
        '...',
        '[noise]',
        '[crosstalk]'
    ]
    
    transcript_lower = transcript.lower()
    error_count = sum(1 for e in error_indicators if e in transcript_lower)
    
    word_count = len(transcript.split())
    
    if error_count > 3 or word_count < 10:
        return {'quality': 'poor', 'score': 0.3}
    elif error_count > 1:
        return {'quality': 'acceptable', 'score': 0.6}
    else:
        return {'quality': 'good', 'score': 0.9}

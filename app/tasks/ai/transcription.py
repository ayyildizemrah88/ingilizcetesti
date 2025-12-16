# -*- coding: utf-8 -*-
"""
Transcription Module - Whisper audio transcription
"""
import os
import base64
import tempfile
import logging

logger = logging.getLogger(__name__)


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
        logger.error(f"Transcription error: {e}")
        return f"[Transcription error: {str(e)}]"


def transcribe_audio_file(file_path):
    """
    Transcribe audio from file path.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Transcribed text
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return "[Transcription unavailable - API key not configured]"
    
    try:
        import openai
        
        client = openai.OpenAI(api_key=api_key)
        
        with open(file_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        
        return transcript.text
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return f"[Transcription error: {str(e)}]"

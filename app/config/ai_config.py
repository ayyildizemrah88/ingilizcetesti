# -*- coding: utf-8 -*-
"""
AI Services Configuration
Unified configuration for OpenAI and Google Gemini AI services.

Usage:
    from app.config.ai_config import get_openai_client, get_gemini_model
    
    # OpenAI
    client = get_openai_client()
    response = client.chat.completions.create(...)
    
    # Gemini
    model = get_gemini_model()
    response = model.generate_content(...)
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# OPENAI CONFIGURATION
# ══════════════════════════════════════════════════════════════════

def get_openai_client():
    """
    Get configured OpenAI client.
    
    Environment Variables:
        OPENAI_API_KEY: Your OpenAI API key
        OPENAI_MODEL: Model to use (default: gpt-4o-mini)
    
    Returns:
        OpenAI client instance
    """
    try:
        from openai import OpenAI
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not set")
            return None
        
        client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized")
        return client
        
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI: {e}")
        return None


def chat_with_openai(prompt: str, system_prompt: str = None, model: str = None) -> Optional[str]:
    """
    Send a chat completion request to OpenAI.
    
    Args:
        prompt: User message
        system_prompt: System instructions
        model: Model to use (default from env or gpt-4o-mini)
    
    Returns:
        Response text or None on error
    """
    client = get_openai_client()
    if not client:
        return None
    
    model = model or os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"OpenAI chat error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# GOOGLE GEMINI CONFIGURATION
# ══════════════════════════════════════════════════════════════════

def get_gemini_model(model_name: str = None):
    """
    Get configured Gemini model.
    
    Environment Variables:
        GEMINI_API_KEY: Your Google AI API key
        GEMINI_MODEL: Model to use (default: gemini-1.5-flash)
    
    Returns:
        Gemini model instance
    """
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.warning("GEMINI_API_KEY not set")
            return None
        
        genai.configure(api_key=api_key)
        
        model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        model = genai.GenerativeModel(model_name)
        
        logger.info(f"Gemini model initialized: {model_name}")
        return model
        
    except ImportError:
        logger.error("google-generativeai package not installed. Run: pip install google-generativeai")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        return None


def chat_with_gemini(prompt: str, model_name: str = None) -> Optional[str]:
    """
    Send a generation request to Gemini.
    
    Args:
        prompt: User prompt
        model_name: Model to use
    
    Returns:
        Response text or None on error
    """
    model = get_gemini_model(model_name)
    if not model:
        return None
    
    try:
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        logger.error(f"Gemini generation error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# UNIFIED AI INTERFACE
# ══════════════════════════════════════════════════════════════════

def get_ai_response(prompt: str, system_prompt: str = None, provider: str = None) -> Optional[str]:
    """
    Get AI response using configured provider.
    
    Args:
        prompt: User prompt
        system_prompt: System instructions (OpenAI only)
        provider: 'openai', 'gemini', or None (auto-detect)
    
    Returns:
        Response text or None on error
    """
    # Auto-detect provider based on available API keys
    if provider is None:
        if os.getenv('GEMINI_API_KEY'):
            provider = 'gemini'
        elif os.getenv('OPENAI_API_KEY'):
            provider = 'openai'
        else:
            logger.error("No AI API key configured")
            return None
    
    if provider == 'openai':
        return chat_with_openai(prompt, system_prompt)
    elif provider == 'gemini':
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"
        return chat_with_gemini(prompt)
    else:
        logger.error(f"Unknown AI provider: {provider}")
        return None


# ══════════════════════════════════════════════════════════════════
# AI MODEL CONFIGURATIONS
# ══════════════════════════════════════════════════════════════════

AI_MODELS = {
    'openai': {
        'default': 'gpt-4o-mini',
        'fast': 'gpt-4o-mini',
        'powerful': 'gpt-4o',
        'legacy': 'gpt-3.5-turbo'
    },
    'gemini': {
        'default': 'gemini-1.5-flash',
        'fast': 'gemini-1.5-flash',
        'powerful': 'gemini-1.5-pro',
        'legacy': 'gemini-1.0-pro'
    }
}

# Speaking/Writing evaluation prompts
EVALUATION_PROMPTS = {
    'writing': """You are an expert English writing evaluator. Evaluate the essay on:
1. Grammar & Spelling (0-25)
2. Vocabulary (0-25) 
3. Coherence & Structure (0-25)
4. Task Achievement (0-25)

Return JSON only with scores and feedback.""",
    
    'speaking': """You are an expert English speaking evaluator. Evaluate based on:
1. Pronunciation (0-25)
2. Fluency (0-25)
3. Grammar (0-25)
4. Vocabulary (0-25)

Return JSON only with scores and feedback."""
}

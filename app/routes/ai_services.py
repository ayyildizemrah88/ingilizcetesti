# -*- coding: utf-8 -*-
"""
AI Service API - OpenAI Integration
Skills Test Center - AI Powered Question Generation and Chat
"""
import os
import random
from flask import Blueprint, request, jsonify

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')


def get_openai_keys():
    """Get all configured OpenAI API keys for rotation"""
    keys = []
    main_key = os.getenv('OPENAI_API_KEY')
    if main_key:
        keys.append(main_key)
    for i in range(1, 51):
        backup_key = os.getenv(f'OPENAI_API_KEY_{i}')
        if backup_key:
            keys.append(backup_key)
    return keys


def get_random_key():
    """Get a random API key from the pool"""
    keys = get_openai_keys()
    if not keys:
        return None
    return random.choice(keys)


@ai_bp.route('/chat', methods=['POST'])
def openai_chat():
    """OpenAI Chat API endpoint"""
    try:
        import openai
        data = request.get_json()
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required', 'success': False}), 400
        
        api_key = get_random_key()
        if not api_key:
            return jsonify({'error': 'No OpenAI API key configured', 'success': False}), 500
        
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful English language learning assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        
        return jsonify({
            'response': response.choices[0].message.content,
            'model': 'gpt-3.5-turbo',
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@ai_bp.route('/generate-question', methods=['POST'])
def generate_question():
    """Generate English test questions using AI"""
    try:
        import openai
        import json
        
        data = request.get_json()
        difficulty = data.get('difficulty', 'A2')
        category = data.get('category', 'grammar')
        
        api_key = get_random_key()
        if not api_key:
            return jsonify({'error': 'No API key configured', 'success': False}), 500
        
        client = openai.OpenAI(api_key=api_key)
        prompt = f"""Generate an English {category} question for CEFR level {difficulty}.
Return ONLY valid JSON:
{{"question": "...", "option_a": "...", "option_b": "...", "option_c": "...", "option_d": "...", "correct_answer": "A/B/C/D", "explanation": "..."}}"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        return jsonify({'response': response.choices[0].message.content, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@ai_bp.route('/health', methods=['GET'])
def ai_health():
    """Check AI service health"""
    keys = get_openai_keys()
    return jsonify({'status': 'healthy' if keys else 'no_keys', 'keys_configured': len(keys)})

# -*- coding: utf-8 -*-
"""
AI Service API - OpenAI Integration
"""
import os
import random
from flask import Blueprint, request, jsonify

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')


def get_openai_keys():
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
    keys = get_openai_keys()
    return random.choice(keys) if keys else None


@ai_bp.route('/chat', methods=['POST'])
def openai_chat():
    try:
        import openai
        data = request.get_json()
        prompt = data.get('prompt', '')
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        api_key = get_random_key()
        if not api_key:
            return jsonify({'error': 'No API key configured'}), 500
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        return jsonify({'response': response.choices[0].message.content, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@ai_bp.route('/generate-question', methods=['POST'])
def generate_question():
    try:
        import openai
        data = request.get_json()
        difficulty = data.get('difficulty', 'A2')
        category = data.get('category', 'grammar')
        api_key = get_random_key()
        if not api_key:
            return jsonify({'error': 'No API key'}), 500
        client = openai.OpenAI(api_key=api_key)
        prompt = f"Generate an English {category} question for CEFR {difficulty}. Return JSON with question, option_a, option_b, option_c, option_d, correct_answer, explanation."
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        return jsonify({'response': response.choices[0].message.content, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/health', methods=['GET'])
def ai_health():
    keys = get_openai_keys()
    return jsonify({'status': 'healthy' if keys else 'no_keys', 'keys_configured': len(keys)})

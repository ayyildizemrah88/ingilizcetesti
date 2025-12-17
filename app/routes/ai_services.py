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
    
    # Main API key
    main_key = os.getenv('OPENAI_API_KEY')
    if main_key:
        keys.append(main_key)
    
    # Backup keys (OPENAI_API_KEY_1 through OPENAI_API_KEY_50)
    for i in range(1, 51):
        backup_key = os.getenv(f'OPENAI_API_KEY_{i}')
        if backup_key:
            keys.append(backup_key)
    
    return keys


def get_random_key():
    """Get a random API key from the pool for load balancing"""
    keys = get_openai_keys()
    if not keys:
        return None
    return random.choice(keys)


@ai_bp.route('/chat', methods=['POST'])
def openai_chat():
    """
    OpenAI Chat API endpoint
    
    Request JSON:
        {"prompt": "Your question here"}
    
    Response JSON:
        {"response": "AI response", "model": "gpt-3.5-turbo", "success": true}
    """
    try:
        import openai
        
        data = request.get_json()
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required', 'success': False}), 400
        
        api_key = get_random_key()
        if not api_key:
            return jsonify({
                'error': 'No OpenAI API key configured. Please set OPENAI_API_KEY in environment.',
                'success': False
            }), 500
        
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful English language learning assistant for the Skills Test Center. Help users learn English through explanations, examples, and corrections."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return jsonify({
            'response': response.choices[0].message.content,
            'model': 'gpt-3.5-turbo',
            'success': True
        })
        
    except ImportError:
        return jsonify({
            'error': 'OpenAI package not installed. Run: pip install openai',
            'success': False
        }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@ai_bp.route('/generate-question', methods=['POST'])
def generate_question():
    """
    Generate English test questions using AI
    
    Request JSON:
        {"difficulty": "A2", "category": "grammar"}
    
    Response JSON:
        {"response": {...question data...}, "success": true}
    """
    try:
        import openai
        import json
        
        data = request.get_json()
        difficulty = data.get('difficulty', 'A2')
        category = data.get('category', 'grammar')
        
        api_key = get_random_key()
        if not api_key:
            return jsonify({
                'error': 'No OpenAI API key configured',
                'success': False
            }), 500
        
        client = openai.OpenAI(api_key=api_key)
        
        prompt = f"""Generate an English {category} question for CEFR level {difficulty}.

The question should be appropriate for a standardized English proficiency test.

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
    "question": "Question text with blank ___ if needed",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_answer": "A",
    "explanation": "Brief explanation of why this is correct",
    "category": "{category}",
    "difficulty": "{difficulty}"
}}"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert English language test question creator. Always respond with valid JSON only."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.8
        )
        
        # Parse the response
        response_text = response.choices[0].message.content.strip()
        
        # Try to parse as JSON
        try:
            question_data = json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, return raw response
            return jsonify({
                'response': response_text,
                'success': True,
                'parsed': False
            })
        
        return jsonify({
            'response': question_data,
            'success': True,
            'parsed': True
        })
        
    except ImportError:
        return jsonify({
            'error': 'OpenAI package not installed',
            'success': False
        }), 500
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@ai_bp.route('/explain-answer', methods=['POST'])
def explain_answer():
    """
    Get AI explanation for a test question answer
    
    Request JSON:
        {"question": "...", "correct_answer": "B", "user_answer": "A"}
    """
    try:
        import openai
        
        data = request.get_json()
        question = data.get('question', '')
        correct_answer = data.get('correct_answer', '')
        user_answer = data.get('user_answer', '')
        
        if not question:
            return jsonify({'error': 'Question is required', 'success': False}), 400
        
        api_key = get_random_key()
        if not api_key:
            return jsonify({'error': 'No API key configured', 'success': False}), 500
        
        client = openai.OpenAI(api_key=api_key)
        
        prompt = f"""Explain this English test question:

Question: {question}
Correct Answer: {correct_answer}
User's Answer: {user_answer}

Please explain:
1. Why the correct answer is right
2. Why the user's answer (if wrong) is incorrect
3. A helpful tip to remember this grammar/vocabulary rule

Keep the explanation concise and educational."""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly English teacher helping students understand their mistakes."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        
        return jsonify({
            'explanation': response.choices[0].message.content,
            'success': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@ai_bp.route('/health', methods=['GET'])
def ai_health():
    """Check AI service health and configuration"""
    keys = get_openai_keys()
    return jsonify({
        'status': 'healthy' if keys else 'no_keys',
        'keys_configured': len(keys),
        'service': 'openai'
    })

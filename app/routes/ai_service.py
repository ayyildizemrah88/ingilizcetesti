# -*- coding: utf-8 -*-
"""
AI Service API - OpenAI Integration
GÜNCELLENME: Writing ve Speaking değerlendirme endpoint'leri eklendi
GitHub: app/routes/ai_service.py
"""
import os
import random
import json
from flask import Blueprint, request, jsonify
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')
def get_openai_keys():
    """Get all configured OpenAI API keys"""
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
    """Get a random API key from available keys"""
    keys = get_openai_keys()
    return random.choice(keys) if keys else None
def get_openai_client():
    """Get OpenAI client with API key"""
    import openai
    api_key = get_random_key()
    if not api_key:
        return None
    return openai.OpenAI(api_key=api_key)
# ══════════════════════════════════════════════════════════════
# TEMEL ENDPOINT'LER
# ══════════════════════════════════════════════════════════════
@ai_bp.route('/health', methods=['GET'])
def ai_health():
    """AI service health check"""
    keys = get_openai_keys()
    return jsonify({
        'status': 'healthy' if keys else 'no_keys',
        'keys_configured': len(keys)
    })
@ai_bp.route('/chat', methods=['POST'])
def openai_chat():
    """General chat endpoint"""
    try:
        client = get_openai_client()
        if not client:
            return jsonify({'error': 'No API key configured'}), 500
            
        data = request.get_json()
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        
        return jsonify({
            'response': response.choices[0].message.content,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500
@ai_bp.route('/generate-question', methods=['POST'])
def generate_question():
    """Generate exam question using AI"""
    try:
        client = get_openai_client()
        if not client:
            return jsonify({'error': 'No API key'}), 500
            
        data = request.get_json()
        difficulty = data.get('difficulty', 'A2')
        category = data.get('category', 'grammar')
        
        prompt = f"""Generate an English {category} question for CEFR {difficulty} level.
Return JSON with: question, option_a, option_b, option_c, option_d, correct_answer, explanation."""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        return jsonify({
            'response': response.choices[0].message.content,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# ══════════════════════════════════════════════════════════════
# WRITING DEĞERLENDİRME
# ══════════════════════════════════════════════════════════════
@ai_bp.route('/evaluate-writing', methods=['POST'])
def evaluate_writing():
    """
    Evaluate written answer using AI
    
    Request JSON:
        text: str - The written answer to evaluate
        question_prompt: str - The original question/prompt
        cefr_level: str - Expected CEFR level (A1-C2)
        
    Response JSON:
        score: int (0-100)
        cefr_achieved: str
        feedback: str
        grammar_errors: list
        vocabulary_score: int
        coherence_score: int
        task_completion_score: int
        suggestions: list
    """
    try:
        client = get_openai_client()
        if not client:
            return jsonify({'error': 'No API key configured'}), 500
            
        data = request.get_json()
        text = data.get('text', '')
        question_prompt = data.get('question_prompt', '')
        cefr_level = data.get('cefr_level', 'B1')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        evaluation_prompt = f"""You are an English language examiner evaluating a written response.
QUESTION/PROMPT: {question_prompt}
STUDENT'S ANSWER: {text}
EXPECTED CEFR LEVEL: {cefr_level}
Please evaluate this response and return a JSON object with exactly these fields:
{{
    "score": <0-100 overall score>,
    "cefr_achieved": "<A1/A2/B1/B2/C1/C2>",
    "feedback": "<brief overall feedback in Turkish>",
    "grammar_errors": [
        {{"error": "<error text>", "correction": "<corrected text>", "explanation": "<brief explanation>"}}
    ],
    "vocabulary_score": <0-100>,
    "coherence_score": <0-100>,
    "task_completion_score": <0-100>,
    "suggestions": ["<improvement suggestion 1>", "<improvement suggestion 2>"]
}}
Scoring criteria:
- Grammar accuracy: 25%
- Vocabulary range and accuracy: 25%
- Coherence and cohesion: 25%
- Task completion: 25%
Return ONLY the JSON object, no other text."""
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert English language examiner. Always respond with valid JSON only."},
                {"role": "user", "content": evaluation_prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Try to parse JSON
        try:
            # Remove markdown code blocks if present
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # Return raw response if parsing fails
            result = {
                "score": 50,
                "cefr_achieved": cefr_level,
                "feedback": result_text[:500],
                "grammar_errors": [],
                "vocabulary_score": 50,
                "coherence_score": 50,
                "task_completion_score": 50,
                "suggestions": []
            }
        
        return jsonify({
            'success': True,
            'evaluation': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500
# ══════════════════════════════════════════════════════════════
# SPEAKING DEĞERLENDİRME
# ══════════════════════════════════════════════════════════════
@ai_bp.route('/evaluate-speaking', methods=['POST'])
def evaluate_speaking():
    """
    Evaluate speaking response (from transcript) using AI
    
    Request JSON:
        transcript: str - The transcribed speech
        question_prompt: str - The original question/prompt
        cefr_level: str - Expected CEFR level (A1-C2)
        audio_duration_seconds: int - Optional, duration of the audio
        
    Response JSON:
        score: int (0-100)
        cefr_achieved: str
        feedback: str
        fluency_score: int
        pronunciation_notes: list
        grammar_score: int
        vocabulary_score: int
        coherence_score: int
        suggestions: list
    """
    try:
        client = get_openai_client()
        if not client:
            return jsonify({'error': 'No API key configured'}), 500
            
        data = request.get_json()
        transcript = data.get('transcript', '')
        question_prompt = data.get('question_prompt', '')
        cefr_level = data.get('cefr_level', 'B1')
        duration = data.get('audio_duration_seconds', 0)
        
        if not transcript:
            return jsonify({'error': 'Transcript is required'}), 400
        
        # Calculate words per minute if duration provided
        word_count = len(transcript.split())
        wpm = (word_count / duration) * 60 if duration > 0 else 0
        
        evaluation_prompt = f"""You are an English language speaking examiner evaluating a spoken response transcript.
QUESTION/PROMPT: {question_prompt}
STUDENT'S SPOKEN RESPONSE (transcribed): {transcript}
EXPECTED CEFR LEVEL: {cefr_level}
RESPONSE DURATION: {duration} seconds ({word_count} words, {round(wpm, 1)} words per minute)
Please evaluate this speaking response and return a JSON object with exactly these fields:
{{
    "score": <0-100 overall score>,
    "cefr_achieved": "<A1/A2/B1/B2/C1/C2>",
    "feedback": "<brief overall feedback in Turkish>",
    "fluency_score": <0-100>,
    "pronunciation_notes": [
        {{"word": "<word>", "issue": "<pronunciation issue>", "suggestion": "<how to improve>"}}
    ],
    "grammar_score": <0-100>,
    "vocabulary_score": <0-100>,
    "coherence_score": <0-100>,
    "suggestions": ["<improvement suggestion 1>", "<improvement suggestion 2>"]
}}
Scoring criteria for speaking:
- Fluency and coherence: 25%
- Lexical resource (vocabulary): 25%
- Grammatical range and accuracy: 25%
- Pronunciation (based on transcript patterns): 25%
Note: Since this is a transcript, evaluate pronunciation based on word choice patterns 
that might indicate pronunciation difficulties (e.g., phonetically spelled words).
Return ONLY the JSON object, no other text."""
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert English speaking examiner. Always respond with valid JSON only."},
                {"role": "user", "content": evaluation_prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Try to parse JSON
        try:
            # Remove markdown code blocks if present
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            result = json.loads(result_text)
        except json.JSONDecodeError:
            result = {
                "score": 50,
                "cefr_achieved": cefr_level,
                "feedback": result_text[:500],
                "fluency_score": 50,
                "pronunciation_notes": [],
                "grammar_score": 50,
                "vocabulary_score": 50,
                "coherence_score": 50,
                "suggestions": []
            }
        
        # Add WPM data
        result['words_per_minute'] = round(wpm, 1)
        result['word_count'] = word_count
        
        return jsonify({
            'success': True,
            'evaluation': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500
# ══════════════════════════════════════════════════════════════
# BATCH DEĞERLENDİRME (Opsiyonel)
# ══════════════════════════════════════════════════════════════
@ai_bp.route('/evaluate-candidate', methods=['POST'])
def evaluate_candidate():
    """
    Evaluate all writing and speaking responses for a candidate
    Updates the candidate's p_writing and p_speaking scores
    
    Request JSON:
        candidate_id: int
        
    Response JSON:
        success: bool
        writing_score: float
        speaking_score: float
        total_score: float
    """
    try:
        from app.extensions import db
        from app.models import Candidate
        
        data = request.get_json()
        candidate_id = data.get('candidate_id')
        
        if not candidate_id:
            return jsonify({'error': 'candidate_id is required'}), 400
        
        candidate = Candidate.query.get(candidate_id)
        if not candidate:
            return jsonify({'error': 'Candidate not found'}), 404
        
        # Get writing and speaking answers from ExamAnswer
        from app.models import ExamAnswer, Question
        
        writing_answers = db.session.query(ExamAnswer, Question).join(
            Question, ExamAnswer.soru_id == Question.id
        ).filter(
            ExamAnswer.aday_id == candidate_id,
            Question.kategori == 'writing'
        ).all()
        
        speaking_answers = db.session.query(ExamAnswer, Question).join(
            Question, ExamAnswer.soru_id == Question.id
        ).filter(
            ExamAnswer.aday_id == candidate_id,
            Question.kategori == 'speaking'
        ).all()
        
        # Evaluate writing
        writing_scores = []
        for answer, question in writing_answers:
            if answer.cevap_metin:
                # Call evaluate_writing internally
                client = get_openai_client()
                if client:
                    # Simplified evaluation for batch processing
                    prompt = f"Rate this English writing 0-100: '{answer.cevap_metin[:500]}'"
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=50
                    )
                    try:
                        score = int(''.join(filter(str.isdigit, response.choices[0].message.content[:10])))
                        score = min(100, max(0, score))
                        writing_scores.append(score)
                    except:
                        writing_scores.append(50)
        
        # Evaluate speaking
        speaking_scores = []
        for answer, question in speaking_answers:
            if answer.cevap_metin:  # Transcript stored here
                client = get_openai_client()
                if client:
                    prompt = f"Rate this English speaking transcript 0-100: '{answer.cevap_metin[:500]}'"
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=50
                    )
                    try:
                        score = int(''.join(filter(str.isdigit, response.choices[0].message.content[:10])))
                        score = min(100, max(0, score))
                        speaking_scores.append(score)
                    except:
                        speaking_scores.append(50)
        
        # Calculate averages
        writing_avg = sum(writing_scores) / len(writing_scores) if writing_scores else 0
        speaking_avg = sum(speaking_scores) / len(speaking_scores) if speaking_scores else 0
        
        # Update candidate
        candidate.p_writing = round(writing_avg, 2)
        candidate.p_speaking = round(speaking_avg, 2)
        candidate.calculate_total_score()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'writing_score': candidate.p_writing,
            'speaking_score': candidate.p_speaking,
            'total_score': candidate.puan,
            'cefr_level': candidate.get_cefr_level()
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

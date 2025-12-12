# -*- coding: utf-8 -*-
"""
══════════════════════════════════════════════════════════════
INTERNATIONAL FEATURES MODULE
══════════════════════════════════════════════════════════════
Adds international English testing standard features:
1. Listening Module with Audio Player
2. Reading Passages with Comprehension
3. CAT Algorithm (Item Response Theory)
4. CEFR Skill Mapping with Radar Charts
5. Speaking Recording with AI Analysis
6. QR Code Certificates
7. WCAG 2.1 Accessibility
"""

import os
import io
import json
import base64
import hashlib
import datetime
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for, 
                   session, jsonify, flash, send_file, current_app)

# Create Blueprint
international_bp = Blueprint('international', __name__)

# ══════════════════════════════════════════════════════════════
# HELPER IMPORTS (these will be available when blueprint is registered)
# ══════════════════════════════════════════════════════════════

def get_db_connection():
    """Import from main app - this will be overridden when registered"""
    from app import get_db_connection as app_get_db
    return app_get_db()

def check_role(roles):
    """Import from main app - role check decorator"""
    from app import check_role as app_check_role
    return app_check_role(roles)

# ══════════════════════════════════════════════════════════════
# LISTENING MODULE ROUTES
# ══════════════════════════════════════════════════════════════

@international_bp.route('/exam/listening/<int:audio_id>')
def sinav_listening(audio_id):
    """Listening comprehension exam page"""
    aday_id = session.get('aday_id')
    if not aday_id:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for('sinav_giris'))
    
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None
    
    conn, is_pg = get_db_connection()
    if is_pg and RealDictCursor:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    # Get audio
    q = "SELECT * FROM listening_audio WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (audio_id,))
    audio = c.fetchone()
    
    if not audio:
        flash("Dinleme kaydı bulunamadı.", "danger")
        return redirect(url_for('sinav'))
    
    # Get questions for this audio
    q = "SELECT * FROM listening_questions WHERE audio_id=? ORDER BY soru_sirasi"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (audio_id,))
    questions = c.fetchall()
    
    # Get play count from session
    plays_key = f'listening_plays_{audio_id}'
    plays_used = session.get(plays_key, 0)
    max_plays = 2  # Standard: 2 plays allowed
    
    # Get remaining time
    remaining_time = session.get('listening_time', 30 * 60)  # 30 minutes default
    
    conn.close()
    
    if is_pg:
        audio_dict = dict(audio)
        questions_list = [dict(q) for q in questions]
    else:
        audio_dict = {
            'id': audio[0],
            'title': audio[1],
            'audio_url': audio[2],
            'transcript': audio[3],
            'duration_seconds': audio[4],
            'difficulty': audio[5]
        }
        questions_list = []
        for q in questions:
            questions_list.append({
                'id': q[0],
                'soru_metni': q[2],
                'secenek_a': q[3],
                'secenek_b': q[4],
                'secenek_c': q[5],
                'secenek_d': q[6],
                'dogru_cevap': q[7]
            })
    
    return render_template('listening_exam.html',
                          audio=audio_dict,
                          questions=questions_list,
                          plays_used=plays_used,
                          max_plays=max_plays,
                          remaining_time=remaining_time,
                          current_question=1,
                          total_questions=len(questions_list))

@international_bp.route('/api/listening/log-play', methods=['POST'])
def api_listening_log_play():
    """Log audio play event"""
    data = request.get_json()
    audio_id = data.get('audio_id')
    
    plays_key = f'listening_plays_{audio_id}'
    current_plays = session.get(plays_key, 0)
    session[plays_key] = current_plays + 1
    
    return jsonify({'plays': session[plays_key]})

@international_bp.route('/exam/listening/submit', methods=['POST'])
def sinav_listening_cevap():
    """Submit listening answers"""
    aday_id = session.get('aday_id')
    if not aday_id:
        return redirect(url_for('sinav_giris'))
    
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None
    
    audio_id = request.form.get('audio_id')
    
    conn, is_pg = get_db_connection()
    c = conn.cursor()
    
    # Get questions for this audio
    q = "SELECT id, dogru_cevap FROM listening_questions WHERE audio_id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (audio_id,))
    questions = c.fetchall()
    
    correct_count = 0
    total_count = len(questions)
    
    for question in questions:
        q_id = question[0]
        correct_answer = question[1] if not is_pg else question['dogru_cevap']
        q_id_val = q_id if not is_pg else question['id']
        
        user_answer = request.form.get(f'q_{q_id_val}', '').upper()
        is_correct = user_answer == correct_answer
        
        if is_correct:
            correct_count += 1
        
        # Save answer
        q_insert = """INSERT INTO cevaplar (aday_id, soru_id, verilen_cevap, dogru_mu) 
                     VALUES (?, ?, ?, ?)"""
        if is_pg:
            q_insert = q_insert.replace('?', '%s')
        c.execute(q_insert, (aday_id, q_id_val, user_answer, 1 if is_correct else 0))
    
    # Calculate listening score
    listening_score = (correct_count / total_count * 100) if total_count > 0 else 0
    
    # Update candidate listening score
    q = "UPDATE adaylar SET p_listening=? WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (listening_score, aday_id))
    
    conn.commit()
    conn.close()
    
    flash(f"Dinleme bölümü tamamlandı. Skor: {listening_score:.1f}%", "success")
    return redirect(url_for('sinav'))

# ══════════════════════════════════════════════════════════════
# READING PASSAGES ROUTES
# ══════════════════════════════════════════════════════════════

@international_bp.route('/exam/reading/<int:passage_id>')
def sinav_reading(passage_id):
    """Reading comprehension exam page"""
    aday_id = session.get('aday_id')
    if not aday_id:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for('sinav_giris'))
    
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None
    
    conn, is_pg = get_db_connection()
    if is_pg and RealDictCursor:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    # Get passage
    q = "SELECT * FROM reading_passages_bank WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (passage_id,))
    passage = c.fetchone()
    
    if not passage:
        flash("Okuma pasajı bulunamadı.", "danger")
        return redirect(url_for('sinav'))
    
    # Get questions for this passage
    q = "SELECT * FROM reading_questions WHERE passage_id=? ORDER BY id"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (passage_id,))
    questions = c.fetchall()
    
    conn.close()
    
    # Format for template
    if is_pg:
        passage_dict = dict(passage)
        questions_list = [dict(q) for q in questions]
    else:
        passage_dict = {
            'id': passage[0],
            'title': passage[1],
            'passage_text': passage[2],
            'word_count': passage[3],
            'topic': passage[4],
            'difficulty': passage[5]
        }
        questions_list = []
        for q in questions:
            questions_list.append({
                'id': q[0],
                'passage_id': q[1],
                'soru_metni': q[2],
                'soru_tipi': q[3],
                'secenek_a': q[4] if len(q) > 4 else '',
                'secenek_b': q[5] if len(q) > 5 else '',
                'secenek_c': q[6] if len(q) > 6 else '',
                'secenek_d': q[7] if len(q) > 7 else '',
                'dogru_cevap': q[8] if len(q) > 8 else ''
            })
    
    # Calculate reading time (60 mins standard)
    remaining_time = session.get('reading_time', 60 * 60)
    
    return render_template('reading_exam.html',
                          passage=passage_dict,
                          questions=questions_list,
                          remaining_time=remaining_time)

@international_bp.route('/exam/reading/submit', methods=['POST'])
def sinav_reading_cevap():
    """Submit reading answers"""
    aday_id = session.get('aday_id')
    if not aday_id:
        return redirect(url_for('sinav_giris'))
    
    passage_id = request.form.get('passage_id')
    
    conn, is_pg = get_db_connection()
    c = conn.cursor()
    
    # Get questions for this passage
    q = "SELECT id, dogru_cevap, soru_tipi FROM reading_questions WHERE passage_id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (passage_id,))
    questions = c.fetchall()
    
    correct_count = 0
    total_count = len(questions)
    
    for question in questions:
        q_id = question[0]
        correct_answer = question[1].upper().strip()
        q_type = question[2] if len(question) > 2 else 'MCQ'
        
        user_answer = request.form.get(f'q_{q_id}', '').upper().strip()
        
        # For fill-in-blank, check for partial match
        if q_type == 'FILL_BLANK':
            is_correct = correct_answer.lower() in user_answer.lower() or user_answer.lower() in correct_answer.lower()
        else:
            is_correct = user_answer == correct_answer
        
        if is_correct:
            correct_count += 1
        
        # Save answer
        q_insert = """INSERT INTO cevaplar (aday_id, soru_id, verilen_cevap, dogru_mu) 
                     VALUES (?, ?, ?, ?)"""
        if is_pg:
            q_insert = q_insert.replace('?', '%s')
        c.execute(q_insert, (aday_id, q_id, user_answer, 1 if is_correct else 0))
    
    # Calculate reading score
    reading_score = (correct_count / total_count * 100) if total_count > 0 else 0
    
    # Update candidate reading score
    q = "UPDATE adaylar SET p_reading=? WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (reading_score, aday_id))
    
    conn.commit()
    conn.close()
    
    flash(f"Okuma bölümü tamamlandı. Skor: {reading_score:.1f}%", "success")
    return redirect(url_for('sinav'))

# ══════════════════════════════════════════════════════════════
# SPEAKING RECORDING ROUTES
# ══════════════════════════════════════════════════════════════

@international_bp.route('/exam/speaking/<int:question_num>')
def sinav_speaking(question_num):
    """Speaking test page"""
    aday_id = session.get('aday_id')
    if not aday_id:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for('sinav_giris'))
    
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None
    
    conn, is_pg = get_db_connection()
    if is_pg and RealDictCursor:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    # Get speaking questions
    q = "SELECT * FROM sorular WHERE soru_tipi='KONUSMA' ORDER BY id LIMIT 5"
    c.execute(q)
    questions = c.fetchall()
    conn.close()
    
    if question_num > len(questions):
        return redirect(url_for('sinav_bitti'))
    
    question = questions[question_num - 1]
    
    if is_pg:
        question_dict = dict(question)
    else:
        question_dict = {
            'id': question[0],
            'soru_metni': question[1],
            'soru_tipi': question[6] if len(question) > 6 else 'KONUSMA',
            'referans_cevap': question[8] if len(question) > 8 else ''
        }
    
    return render_template('speaking_exam.html',
                          question=question_dict,
                          current_question=question_num,
                          total_questions=len(questions),
                          preparation_time=30,  # 30 seconds prep
                          max_duration=120)    # 2 minutes max

@international_bp.route('/api/speaking/upload', methods=['POST'])
def api_speaking_upload():
    """Upload and process speaking recording"""
    from flask_wtf.csrf import validate_csrf
    
    aday_id = session.get('aday_id')
    if not aday_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400
    
    audio_file = request.files['audio']
    question_id = request.form.get('question_id')
    
    # Save audio blob
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'speaking_{aday_id}_{question_id}_{timestamp}.webm'
    audio_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/uploads'), filename)
    
    try:
        audio_file.save(audio_path)
    except Exception as e:
        return jsonify({'error': f'Save failed: {str(e)}'}), 500
    
    # Try AI transcription and scoring
    transcript = ""
    scores = None
    
    try:
        # Try Whisper API for transcription
        import openai
        if os.getenv('OPENAI_API_KEY'):
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            with open(audio_path, 'rb') as audio:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )
            transcript = transcription.text
    except Exception as e:
        transcript = f"[Transcription unavailable: {str(e)}]"
    
    try:
        # Try Gemini for scoring
        import google.generativeai as genai
        if os.getenv('GEMINI_API_KEY'):
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""Evaluate this English speaking response on IELTS criteria (0-9 scale):
            
Transcript: {transcript}

Provide JSON only: {{"fluency": X, "pronunciation": X, "grammar": X, "vocabulary": X, "feedback": "..."}}"""
            
            response = model.generate_content(prompt)
            try:
                scores = json.loads(response.text)
            except:
                scores = {'fluency': 5, 'pronunciation': 5, 'grammar': 5, 'vocabulary': 5}
    except:
        scores = {'fluency': 5, 'pronunciation': 5, 'grammar': 5, 'vocabulary': 5}
    
    # Save to database
    conn, is_pg = get_db_connection()
    c = conn.cursor()
    
    q = """INSERT INTO speaking_recordings (aday_id, soru_id, audio_blob, transcript, ai_score_json)
           VALUES (?, ?, ?, ?, ?)"""
    if is_pg:
        q = q.replace('?', '%s')
    
    c.execute(q, (aday_id, question_id, filename, transcript, json.dumps(scores)))
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'transcript': transcript,
        'scores': scores
    })

# ══════════════════════════════════════════════════════════════
# CAT ALGORITHM ROUTES
# ══════════════════════════════════════════════════════════════

@international_bp.route('/exam/cat/next-question')
def cat_next_question():
    """Get next question using CAT algorithm"""
    aday_id = session.get('aday_id')
    if not aday_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    from cat_engine import CATEngine, DIFFICULTY_MAP
    
    # Get or create CAT session
    cat_data = session.get('cat_session', {
        'ability': 0.0,
        'responses': [],
        'asked_ids': []
    })
    
    cat = CATEngine(initial_ability=cat_data['ability'])
    
    # Replay responses to restore state
    for diff, correct in cat_data['responses']:
        cat.record_response(diff, correct)
    
    # Check if should stop
    should_stop, reason = cat.should_stop()
    if should_stop:
        return jsonify({
            'done': True,
            'reason': reason,
            'summary': cat.get_summary()
        })
    
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None
    
    conn, is_pg = get_db_connection()
    if is_pg and RealDictCursor:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    # Get available questions (not yet asked)
    asked_ids = cat_data['asked_ids']
    placeholders = ','.join(['?' for _ in asked_ids]) if asked_ids else '0'
    
    q = f"""SELECT id, soru_metni, secenek_a, secenek_b, secenek_c, secenek_d, 
                   dogru_cevap, zorluk, kategori 
            FROM sorular 
            WHERE soru_tipi='SECMELI' AND id NOT IN ({placeholders})
            ORDER BY RANDOM() LIMIT 50"""
    
    if is_pg:
        q = q.replace('?', '%s')
    
    c.execute(q, tuple(asked_ids) if asked_ids else ())
    available = c.fetchall()
    conn.close()
    
    if not available:
        return jsonify({
            'done': True,
            'reason': 'no_more_questions',
            'summary': cat.get_summary()
        })
    
    # Format questions for CAT selection
    items = []
    for q in available:
        if is_pg:
            items.append({
                'id': q['id'],
                'difficulty': q['zorluk'],
                'data': dict(q)
            })
        else:
            items.append({
                'id': q[0],
                'difficulty': q[7],
                'data': {
                    'id': q[0],
                    'soru_metni': q[1],
                    'secenek_a': q[2],
                    'secenek_b': q[3],
                    'secenek_c': q[4],
                    'secenek_d': q[5],
                    'dogru_cevap': q[6],
                    'zorluk': q[7],
                    'kategori': q[8]
                }
            })
    
    # Select best question
    selected = cat.select_next_item(items)
    
    if not selected:
        return jsonify({'done': True, 'reason': 'selection_failed'})
    
    return jsonify({
        'done': False,
        'question': selected['data'],
        'question_number': len(cat_data['responses']) + 1,
        'current_ability': cat.ability,
        'current_cefr': cat.get_cefr_level()
    })

@international_bp.route('/exam/cat/answer', methods=['POST'])
def cat_record_answer():
    """Record answer and update CAT state"""
    aday_id = session.get('aday_id')
    if not aday_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    question_id = data.get('question_id')
    answer = data.get('answer')
    correct_answer = data.get('correct_answer')
    difficulty = data.get('difficulty', 'B1')
    
    is_correct = answer.upper() == correct_answer.upper()
    
    # Update CAT session
    cat_data = session.get('cat_session', {
        'ability': 0.0,
        'responses': [],
        'asked_ids': []
    })
    
    cat_data['responses'].append((difficulty, is_correct))
    cat_data['asked_ids'].append(question_id)
    
    from cat_engine import CATEngine
    cat = CATEngine(initial_ability=0.0)
    for diff, correct in cat_data['responses']:
        cat.record_response(diff, correct)
    
    cat_data['ability'] = cat.ability
    session['cat_session'] = cat_data
    
    # Save to database
    conn, is_pg = get_db_connection()
    c = conn.cursor()
    
    q = """INSERT INTO cevaplar (aday_id, soru_id, verilen_cevap, dogru_mu) 
           VALUES (?, ?, ?, ?)"""
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (aday_id, question_id, answer, 1 if is_correct else 0))
    conn.commit()
    conn.close()
    
    return jsonify({
        'is_correct': is_correct,
        'new_ability': cat.ability,
        'new_cefr': cat.get_cefr_level(),
        'standard_error': cat.calculate_se()
    })

# ══════════════════════════════════════════════════════════════
# CEFR SKILL REPORT ROUTES
# ══════════════════════════════════════════════════════════════

@international_bp.route('/results/cefr-report/<int:aday_id>')
def cefr_skill_report(aday_id):
    """Generate CEFR skill report with radar chart"""
    from cefr_mapper import calculate_skill_levels, get_radar_chart_data
    
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None
    
    conn, is_pg = get_db_connection()
    if is_pg and RealDictCursor:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    q = "SELECT * FROM adaylar WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (aday_id,))
    aday = c.fetchone()
    conn.close()
    
    if not aday:
        flash("Aday bulunamadı.", "danger")
        return redirect(url_for('index'))
    
    # Extract scores
    if is_pg:
        scores = {
            'reading': aday.get('p_reading', 0),
            'listening': aday.get('p_listening', 0),
            'writing': aday.get('p_writing', 0),
            'speaking': aday.get('p_speaking', 0),
            'grammar': aday.get('p_grammar', 0),
            'vocabulary': aday.get('p_vocab', 0)
        }
        aday_dict = dict(aday)
    else:
        # Assuming column order from init_db
        scores = {
            'reading': aday[22] if len(aday) > 22 else 0,
            'listening': aday[25] if len(aday) > 25 else 0,
            'writing': aday[23] if len(aday) > 23 else 0,
            'speaking': aday[24] if len(aday) > 24 else 0,
            'grammar': aday[20] if len(aday) > 20 else 0,
            'vocabulary': aday[21] if len(aday) > 21 else 0
        }
        aday_dict = {
            'id': aday[0],
            'ad_soyad': aday[1],
            'puan': aday[7],
            'seviye_sonuc': aday[27] if len(aday) > 27 else '',
            'bitis_tarihi': aday[17] if len(aday) > 17 else '',
            'certificate_hash': aday[19] if len(aday) > 19 else ''
        }
    
    # Calculate CEFR levels
    skill_results = calculate_skill_levels(scores)
    radar_data = get_radar_chart_data(skill_results)
    
    return render_template('cefr_rapor.html',
                          aday=aday_dict,
                          skill_results=skill_results,
                          radar_data=radar_data)

# ══════════════════════════════════════════════════════════════
# QR CODE CERTIFICATE ROUTES
# ══════════════════════════════════════════════════════════════

def generate_qr_code(data):
    """Generate QR code as base64 string"""
    try:
        import qrcode
        from PIL import Image
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except ImportError:
        return None

@international_bp.route('/cert/verify/<cert_hash>')
def cert_verify(cert_hash):
    """Public certificate verification page"""
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None
    
    conn, is_pg = get_db_connection()
    if is_pg and RealDictCursor:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    q = """SELECT ad_soyad, puan, seviye_sonuc, bitis_tarihi, band_score,
                  ielts_reading, ielts_writing, ielts_speaking, ielts_listening
           FROM adaylar WHERE certificate_hash=?"""
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (cert_hash,))
    cert = c.fetchone()
    conn.close()
    
    certificate = None
    qr_image = None
    
    if cert:
        if is_pg:
            certificate = dict(cert)
        else:
            certificate = {
                'ad_soyad': cert[0],
                'puan': cert[1],
                'seviye_sonuc': cert[2],
                'bitis_tarihi': cert[3],
                'band_score': cert[4],
                'ielts_reading': cert[5],
                'ielts_writing': cert[6],
                'ielts_speaking': cert[7],
                'ielts_listening': cert[8]
            }
        
        certificate['certificate_hash'] = cert_hash
        
        # Check expiry (2 years validity)
        if certificate['bitis_tarihi']:
            try:
                issue_date = datetime.datetime.strptime(str(certificate['bitis_tarihi'])[:10], '%Y-%m-%d')
                expiry_date = issue_date + datetime.timedelta(days=730)  # 2 years
                certificate['expiry_date'] = expiry_date.strftime('%Y-%m-%d')
                certificate['is_expired'] = datetime.datetime.now() > expiry_date
                certificate['validity_years'] = 2
            except:
                certificate['is_expired'] = False
        
        # Generate QR code
        verify_url = url_for('international.cert_verify', cert_hash=cert_hash, _external=True)
        qr_image = generate_qr_code(verify_url)
    
    return render_template('cert_verify.html',
                          certificate=certificate,
                          qr_image=qr_image,
                          verified_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@international_bp.route('/cert/download-with-qr/<cert_hash>')
def cert_download_qr(cert_hash):
    """Download PDF certificate with QR code"""
    try:
        from psycopg2.extras import RealDictCursor
    except ImportError:
        RealDictCursor = None
    
    conn, is_pg = get_db_connection()
    if is_pg and RealDictCursor:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    q = """SELECT ad_soyad, puan, seviye_sonuc, bitis_tarihi, band_score
           FROM adaylar WHERE certificate_hash=?"""
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (cert_hash,))
    aday = c.fetchone()
    conn.close()
    
    if not aday:
        flash("Sertifika bulunamadı.", "danger")
        return redirect(url_for('index'))
    
    try:
        from fpdf import FPDF
        import qrcode
        
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Helvetica', 'B', 28)
        pdf.cell(0, 25, 'SKILLS TEST CENTER', 0, 1, 'C')
        
        pdf.set_font('Helvetica', 'B', 20)
        pdf.cell(0, 15, 'CERTIFICATE OF ENGLISH PROFICIENCY', 0, 1, 'C')
        
        pdf.ln(10)
        
        # Candidate info
        pdf.set_font('Helvetica', '', 14)
        pdf.cell(0, 10, 'This is to certify that', 0, 1, 'C')
        
        ad_soyad = aday['ad_soyad'] if is_pg else aday[0]
        puan = aday['puan'] if is_pg else aday[1]
        seviye = aday['seviye_sonuc'] if is_pg else aday[2]
        tarih = aday['bitis_tarihi'] if is_pg else aday[3]
        band = aday['band_score'] if is_pg else (aday[4] if len(aday) > 4 else '')
        
        pdf.set_font('Helvetica', 'B', 24)
        pdf.cell(0, 15, ad_soyad, 0, 1, 'C')
        
        pdf.set_font('Helvetica', '', 14)
        pdf.cell(0, 10, 'has demonstrated English language proficiency at', 0, 1, 'C')
        
        pdf.set_font('Helvetica', 'B', 32)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 20, f'CEFR Level {seviye}', 0, 1, 'C')
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 14)
        pdf.ln(5)
        pdf.cell(0, 10, f'Overall Score: {puan}%', 0, 1, 'C')
        if band:
            pdf.cell(0, 10, f'IELTS Band Equivalent: {band}', 0, 1, 'C')
        pdf.cell(0, 10, f'Date of Assessment: {tarih}', 0, 1, 'C')
        
        pdf.ln(15)
        
        # Generate QR code and save temporarily
        verify_url = url_for('international.cert_verify', cert_hash=cert_hash, _external=True)
        qr = qrcode.make(verify_url)
        qr_path = f'/tmp/qr_{cert_hash}.png'
        qr.save(qr_path)
        
        # Add QR to PDF
        pdf.image(qr_path, x=85, y=pdf.get_y(), w=40)
        pdf.ln(45)
        
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 8, 'Scan QR code to verify this certificate online', 0, 1, 'C')
        pdf.cell(0, 8, f'Verification Code: {cert_hash}', 0, 1, 'C')
        
        # Clean up temp file
        try:
            os.remove(qr_path)
        except:
            pass
        
        # Output
        out = io.BytesIO()
        pdf.output(out)
        out.seek(0)
        
        return send_file(
            out,
            download_name=f'certificate_{cert_hash}.pdf',
            as_attachment=True,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        flash(f"PDF oluşturma hatası: {str(e)}", "danger")
        return redirect(url_for('index'))

# ══════════════════════════════════════════════════════════════
# ACCESSIBILITY ROUTES
# ══════════════════════════════════════════════════════════════

@international_bp.route('/accessibility/toggle', methods=['POST'])
def toggle_accessibility():
    """Toggle accessibility features"""
    data = request.get_json() or {}
    feature = data.get('feature', '')
    
    accessibility = session.get('accessibility', {
        'high_contrast': False,
        'large_text': False,
        'reduced_motion': False,
        'colorblind_mode': None,
        'dyslexia_friendly': False
    })
    
    if feature == 'high_contrast':
        accessibility['high_contrast'] = not accessibility['high_contrast']
    elif feature == 'large_text':
        accessibility['large_text'] = not accessibility['large_text']
    elif feature == 'reduced_motion':
        accessibility['reduced_motion'] = not accessibility['reduced_motion']
    elif feature == 'dyslexia_friendly':
        accessibility['dyslexia_friendly'] = not accessibility['dyslexia_friendly']
    elif feature.startswith('colorblind_'):
        mode = feature.replace('colorblind_', '')
        if accessibility['colorblind_mode'] == mode:
            accessibility['colorblind_mode'] = None
        else:
            accessibility['colorblind_mode'] = mode
    
    session['accessibility'] = accessibility
    
    return jsonify(accessibility)

@international_bp.route('/accessibility/settings')
def accessibility_settings():
    """Get current accessibility settings"""
    return jsonify(session.get('accessibility', {}))


# ══════════════════════════════════════════════════════════════
# REGISTER BLUEPRINT FUNCTION
# ══════════════════════════════════════════════════════════════

def register_international_features(app):
    """Register this blueprint with the Flask app"""
    app.register_blueprint(international_bp)
    
    # Add accessibility context processor
    @app.context_processor
    def inject_accessibility():
        return {
            'accessibility': session.get('accessibility', {
                'high_contrast': False,
                'large_text': False,
                'reduced_motion': False,
                'colorblind_mode': None,
                'dyslexia_friendly': False
            })
        }
    
    return app

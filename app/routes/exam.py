# -*- coding: utf-8 -*-
"""
Exam Routes - Exam interface and flow
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.extensions import db
import random

exam_bp = Blueprint('exam', __name__)


def exam_required(f):
    """Require active exam session"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'aday_id' not in session:
            flash("Lütfen sınav giriş kodunuzu girin.", "warning")
            return redirect(url_for('auth.sinav_giris'))
        return f(*args, **kwargs)
    return decorated


@exam_bp.route('/')
@exam_bp.route('/sinav')
@exam_required
def sinav():
    """
    Main exam page - displays current question
    ---
    tags:
      - Exam
    responses:
      200:
        description: Exam question page
    """
    from app.models import Candidate, Question, ExamAnswer
    
    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)
    
    if not candidate:
        session.clear()
        return redirect(url_for('auth.sinav_giris'))
    
    # Check time limit
    from datetime import datetime
    elapsed = datetime.utcnow() - candidate.baslama_tarihi
    remaining = (candidate.sinav_suresi * 60) - elapsed.total_seconds()
    
    if remaining <= 0:
        return redirect(url_for('exam.sinav_bitti'))
    
    # Get answered question IDs
    answered_ids = [a.soru_id for a in ExamAnswer.query.filter_by(aday_id=aday_id).all()]
    
    # Get next question (CAT or random)
    if candidate.soru_limiti and len(answered_ids) >= candidate.soru_limiti:
        return redirect(url_for('exam.sinav_bitti'))
    
    # Select question using CAT or random
    question = select_next_question(candidate, answered_ids)
    
    if not question:
        return redirect(url_for('exam.sinav_bitti'))
    
    soru_no = len(answered_ids) + 1
    toplam = candidate.soru_limiti or 25
    
    return render_template('sinav.html',
                          soru=question,
                          soru_no=soru_no,
                          toplam=toplam,
                          kalan_sure=int(remaining),
                          soru_suresi=candidate.soru_suresi or 0)


def select_next_question(candidate, answered_ids):
    """Select next question using CAT algorithm or random"""
    from app.models import Question
    
    # Query available questions
    query = Question.query.filter(
        Question.sirket_id == candidate.sirket_id,
        Question.is_active == True,
        Question.soru_tipi == 'SECMELI'
    )
    
    if answered_ids:
        query = query.filter(~Question.id.in_(answered_ids))
    
    # Filter by current difficulty (CAT)
    difficulty = candidate.current_difficulty or 'B1'
    questions_at_level = query.filter_by(zorluk=difficulty).all()
    
    if questions_at_level:
        return random.choice(questions_at_level)
    
    # Fallback to any available question
    all_questions = query.all()
    if all_questions:
        return random.choice(all_questions)
    
    return None


@exam_bp.route('/sinav', methods=['POST'])
@exam_required
def sinav_cevap():
    """
    Submit answer and get next question
    ---
    tags:
      - Exam
    """
    from app.models import Candidate, Question, ExamAnswer
    
    aday_id = session.get('aday_id')
    soru_id = request.form.get('soru_id', type=int)
    cevap = request.form.get('cevap', '').upper()
    
    # Get question
    question = Question.query.get(soru_id)
    if not question:
        return redirect(url_for('exam.sinav'))
    
    # Check answer
    is_correct = cevap == question.dogru_cevap.upper()
    
    # Save answer
    answer = ExamAnswer(
        aday_id=aday_id,
        soru_id=soru_id,
        verilen_cevap=cevap,
        dogru_mu=is_correct
    )
    db.session.add(answer)
    
    # Update CAT difficulty
    candidate = Candidate.query.get(aday_id)
    update_cat_difficulty(candidate, question.zorluk, is_correct)
    
    db.session.commit()
    
    return redirect(url_for('exam.sinav'))


def update_cat_difficulty(candidate, question_difficulty, is_correct):
    """Update candidate difficulty level based on answer"""
    difficulty_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    current_idx = difficulty_levels.index(candidate.current_difficulty or 'B1')
    
    if is_correct and current_idx < len(difficulty_levels) - 1:
        candidate.current_difficulty = difficulty_levels[current_idx + 1]
    elif not is_correct and current_idx > 0:
        candidate.current_difficulty = difficulty_levels[current_idx - 1]


@exam_bp.route('/sinav-bitti')
@exam_required
def sinav_bitti():
    """
    Exam completion page with results
    ---
    tags:
      - Exam
    """
    from app.models import Candidate, ExamAnswer, Question
    from datetime import datetime
    import hashlib
    
    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)
    
    if not candidate:
        return redirect(url_for('auth.sinav_giris'))
    
    # Calculate scores
    answers = ExamAnswer.query.filter_by(aday_id=aday_id).all()
    
    # Group by category
    category_scores = {}
    for answer in answers:
        question = Question.query.get(answer.soru_id)
        if question:
            cat = question.kategori or 'general'
            if cat not in category_scores:
                category_scores[cat] = {'correct': 0, 'total': 0}
            category_scores[cat]['total'] += 1
            if answer.dogru_mu:
                category_scores[cat]['correct'] += 1
    
    # Update candidate scores
    for cat, scores in category_scores.items():
        pct = (scores['correct'] / scores['total'] * 100) if scores['total'] > 0 else 0
        if cat == 'grammar':
            candidate.p_grammar = pct
        elif cat == 'vocabulary':
            candidate.p_vocabulary = pct
        elif cat == 'reading':
            candidate.p_reading = pct
    
    # Calculate total
    candidate.calculate_total_score()
    candidate.seviye_sonuc = candidate.get_cefr_level()
    
    # Generate certificate hash
    if not candidate.certificate_hash:
        cert_data = f"{candidate.id}-{candidate.ad_soyad}-{datetime.utcnow().isoformat()}"
        candidate.certificate_hash = hashlib.sha256(cert_data.encode()).hexdigest()[:16]
    
    # Mark completed
    candidate.sinav_durumu = 'tamamlandi'
    candidate.bitis_tarihi = datetime.utcnow()
    
    db.session.commit()
    
    # Trigger webhook
    from app.tasks.webhook_tasks import trigger_exam_completed
    trigger_exam_completed.delay(candidate.id)
    
    return render_template('sinav_bitti.html', 
                          aday=candidate,
                          category_scores=category_scores)


@exam_bp.route('/sonuc/<giris_kodu>')
def sonuc(giris_kodu):
    """
    Public result page
    ---
    tags:
      - Exam
    """
    from app.models import Candidate
    
    candidate = Candidate.query.filter_by(giris_kodu=giris_kodu).first_or_404()
    
    if candidate.sinav_durumu != 'tamamlandi':
        flash("Sınav henüz tamamlanmamış.", "warning")
        return redirect(url_for('index'))
    
    return render_template('sinav_bitti.html', aday=candidate)

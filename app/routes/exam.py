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
    from datetime import datetime
    
    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)
    
    if not candidate:
        session.clear()
        return redirect(url_for('auth.sinav_giris'))
    
    # Check time limit
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
    
    # ══════════════════════════════════════════════════════════════════
    # SECURITY: Store active question ID to prevent manipulation
    # ══════════════════════════════════════════════════════════════════
    session['active_question_id'] = question.id
    session['question_started_at'] = datetime.utcnow().isoformat()  # For reading time verification
    
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
    
    # ══════════════════════════════════════════════════════════════════
    # SECURITY: Validate question ID matches session
    # Prevents manipulation via DevTools/API
    # ══════════════════════════════════════════════════════════════════
    active_question_id = session.get('active_question_id')
    if not active_question_id or soru_id != active_question_id:
        flash("Geçersiz soru ID. Lütfen tekrar deneyin.", "warning")
        return redirect(url_for('exam.sinav'))
    
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
    
    # Clear active question from session
    session.pop('active_question_id', None)
    session.pop('question_started_at', None)
    
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


# ══════════════════════════════════════════════════════════════════
# PAUSE/RESUME FUNCTIONALITY
# ══════════════════════════════════════════════════════════════════

@exam_bp.route('/sinav/pause', methods=['POST'])
@exam_required
def pause_exam():
    """
    Pause the current exam session
    ---
    tags:
      - Exam
    """
    from app.models import Candidate
    from datetime import datetime
    
    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)
    
    if not candidate:
        return jsonify({'status': 'error', 'message': 'Aday bulunamadı'}), 404
    
    if candidate.is_paused:
        return jsonify({'status': 'already_paused'})
    
    # Save current question ID for resume
    current_question_id = request.json.get('current_question_id')
    
    candidate.is_paused = True
    candidate.paused_at = datetime.utcnow()
    candidate.last_question_id = current_question_id
    candidate.sinav_durumu = 'duraklatildi'
    
    db.session.commit()
    
    return jsonify({
        'status': 'paused',
        'message': 'Sınav duraklatıldı. Kaldığınız yerden devam edebilirsiniz.'
    })


@exam_bp.route('/sinav/resume', methods=['POST'])
@exam_required
def resume_exam():
    """
    Resume a paused exam session
    ---
    tags:
      - Exam
    """
    from app.models import Candidate
    from datetime import datetime
    
    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)
    
    if not candidate:
        return jsonify({'status': 'error', 'message': 'Aday bulunamadı'}), 404
    
    if not candidate.is_paused:
        return jsonify({'status': 'not_paused'})
    
    # Calculate paused duration
    paused_duration = (datetime.utcnow() - candidate.paused_at).total_seconds()
    candidate.total_paused_seconds = (candidate.total_paused_seconds or 0) + int(paused_duration)
    
    candidate.is_paused = False
    candidate.paused_at = None
    candidate.sinav_durumu = 'devam_ediyor'
    
    db.session.commit()
    
    return jsonify({
        'status': 'resumed',
        'last_question_id': candidate.last_question_id,
        'message': 'Sınava devam ediliyor.'
    })


# ══════════════════════════════════════════════════════════════════
# PRACTICE MODE
# ══════════════════════════════════════════════════════════════════

@exam_bp.route('/practice')
def practice_mode():
    """
    Start a practice exam (results not saved to profile)
    ---
    tags:
      - Exam
    """
    from app.models import Candidate
    from datetime import datetime
    import secrets
    
    # Create a temporary practice candidate
    practice_code = f"PRACTICE-{secrets.token_hex(4).upper()}"
    
    candidate = Candidate(
        ad_soyad="Deneme Kullanıcısı",
        giris_kodu=practice_code,
        is_practice=True,
        sinav_suresi=15,  # Shorter duration for practice
        soru_limiti=10,   # Fewer questions
        soru_suresi=0,    # No time limit per question
        sinav_durumu='devam_ediyor',
        baslama_tarihi=datetime.utcnow()
    )
    
    db.session.add(candidate)
    db.session.commit()
    
    session['aday_id'] = candidate.id
    session['is_practice'] = True
    
    flash("🎯 Deneme modu başladı. Sonuçlar kaydedilmeyecek.", "info")
    return redirect(url_for('exam.sinav'))


@exam_bp.route('/practice/finish')
@exam_required
def finish_practice():
    """
    Finish practice mode and show results without saving
    ---
    tags:
      - Exam
    """
    from app.models import Candidate, ExamAnswer, Question
    
    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)
    
    if not candidate or not candidate.is_practice:
        return redirect(url_for('exam.sinav_bitti'))
    
    # Calculate scores for display only
    answers = ExamAnswer.query.filter_by(aday_id=aday_id).all()
    
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
    
    # Calculate total for display
    candidate.calculate_total_score()
    candidate.seviye_sonuc = candidate.get_cefr_level()
    
    # Clear session
    session.clear()
    
    return render_template('practice_result.html',
                          aday=candidate,
                          category_scores=category_scores,
                          is_practice=True)


# ══════════════════════════════════════════════════════════════════
# LISTENING REPLAY
# ══════════════════════════════════════════════════════════════════

@exam_bp.route('/listening/replay', methods=['POST'])
@exam_required
def listening_replay():
    """
    Use a listening replay (max 2 per exam)
    ---
    tags:
      - Exam
    """
    from app.models import Candidate
    
    MAX_REPLAYS = 2
    
    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)
    
    if not candidate:
        return jsonify({'status': 'error'}), 404
    
    replays_used = candidate.listening_replays_used or 0
    
    if replays_used >= MAX_REPLAYS:
        return jsonify({
            'status': 'limit_reached',
            'message': f'Maksimum {MAX_REPLAYS} tekrar hakkınız var.',
            'replays_remaining': 0
        })
    
    candidate.listening_replays_used = replays_used + 1
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'replays_remaining': MAX_REPLAYS - candidate.listening_replays_used,
        'message': f'Tekrar hakkı kullanıldı. Kalan: {MAX_REPLAYS - candidate.listening_replays_used}'
    })


# ══════════════════════════════════════════════════════════════════
# READING WPM TRACKING
# ══════════════════════════════════════════════════════════════════

@exam_bp.route('/reading/wpm', methods=['POST'])
@exam_required
def track_reading_wpm():
    """
    Track reading words per minute
    ---
    tags:
      - Exam
    """
    from app.models import Candidate
    
    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)
    
    if not candidate:
        return jsonify({'status': 'error'}), 404
    
    word_count = request.json.get('word_count', 0)
    reading_time_seconds = request.json.get('reading_time_seconds', 1)
    
    # Calculate WPM
    wpm = (word_count / reading_time_seconds) * 60 if reading_time_seconds > 0 else 0
    
    # Store average WPM
    if candidate.reading_wpm:
        candidate.reading_wpm = (candidate.reading_wpm + wpm) / 2
    else:
        candidate.reading_wpm = wpm
    
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'wpm': round(wpm, 1),
        'average_wpm': round(candidate.reading_wpm, 1)
    })


# ══════════════════════════════════════════════════════════════════
# BENCHMARK CALCULATION
# ══════════════════════════════════════════════════════════════════

def calculate_benchmark_percentile(candidate):
    """
    Calculate percentile ranking compared to other candidates
    """
    from app.models import Candidate
    
    # Get all completed candidates with scores
    all_candidates = Candidate.query.filter(
        Candidate.sinav_durumu == 'tamamlandi',
        Candidate.puan > 0,
        Candidate.is_practice == False,
        Candidate.id != candidate.id
    ).all()
    
    if not all_candidates:
        return 50.0  # No comparison data, assume median
    
    scores = [c.puan for c in all_candidates]
    below_count = sum(1 for s in scores if s < candidate.puan)
    
    percentile = (below_count / len(scores)) * 100
    return round(percentile, 1)


@exam_bp.route('/benchmark/<int:candidate_id>')
def get_benchmark(candidate_id):
    """
    Get benchmark comparison for a candidate
    ---
    tags:
      - Exam
    """
    from app.models import Candidate
    
    candidate = Candidate.query.get_or_404(candidate_id)
    
    if candidate.sinav_durumu != 'tamamlandi':
        return jsonify({'status': 'exam_not_completed'}), 400
    
    # Calculate and store percentile
    percentile = calculate_benchmark_percentile(candidate)
    candidate.benchmark_percentile = percentile
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'percentile': percentile,
        'message': f"Aynı seviyedeki adayların %{percentile}'inden daha iyi performans gösterdiniz."
    })


# ══════════════════════════════════════════════════════════════════
# ANSWER ANALYSIS DASHBOARD
# ══════════════════════════════════════════════════════════════════

@exam_bp.route('/analysis/<giris_kodu>')
def answer_analysis(giris_kodu):
    """
    Detailed answer analysis dashboard
    ---
    tags:
      - Exam
    """
    from app.models import Candidate, ExamAnswer, Question
    
    candidate = Candidate.query.filter_by(giris_kodu=giris_kodu).first_or_404()
    
    if candidate.sinav_durumu != 'tamamlandi':
        flash("Sınav henüz tamamlanmamış.", "warning")
        return redirect(url_for('index'))
    
    # Get all answers with questions
    answers = ExamAnswer.query.filter_by(aday_id=candidate.id).all()
    
    analysis = {
        'total': len(answers),
        'correct': sum(1 for a in answers if a.dogru_mu),
        'wrong': sum(1 for a in answers if not a.dogru_mu),
        'categories': {},
        'difficulty_breakdown': {},
        'strengths': [],
        'weaknesses': []
    }
    
    # Analyze by category and difficulty
    for answer in answers:
        question = Question.query.get(answer.soru_id)
        if question:
            # Category analysis
            cat = question.kategori or 'general'
            if cat not in analysis['categories']:
                analysis['categories'][cat] = {'correct': 0, 'total': 0, 'percentage': 0}
            analysis['categories'][cat]['total'] += 1
            if answer.dogru_mu:
                analysis['categories'][cat]['correct'] += 1
            
            # Difficulty analysis
            diff = question.zorluk or 'B1'
            if diff not in analysis['difficulty_breakdown']:
                analysis['difficulty_breakdown'][diff] = {'correct': 0, 'total': 0}
            analysis['difficulty_breakdown'][diff]['total'] += 1
            if answer.dogru_mu:
                analysis['difficulty_breakdown'][diff]['correct'] += 1
    
    # Calculate percentages and find strengths/weaknesses
    for cat, data in analysis['categories'].items():
        if data['total'] > 0:
            data['percentage'] = round((data['correct'] / data['total']) * 100, 1)
            if data['percentage'] >= 70:
                analysis['strengths'].append(cat)
            elif data['percentage'] < 50:
                analysis['weaknesses'].append(cat)
    
    # Calculate benchmark
    analysis['benchmark_percentile'] = calculate_benchmark_percentile(candidate)
    
    return render_template('answer_analysis.html',
                          aday=candidate,
                          analysis=analysis)


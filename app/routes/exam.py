# -*- coding: utf-8 -*-
"""
Exam Routes - Exam interface and flow
DÜZELTME: auth.sinav_giris -> candidate_auth.sinav_giris
GitHub: app/routes/exam.py
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.extensions import db
import random
from datetime import datetime

exam_bp = Blueprint('exam', __name__)


def exam_required(f):
    """Require active exam session - FIXED: candidate_auth.sinav_giris"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'aday_id' not in session:
            flash("Lütfen sınav giriş kodunuzu girin.", "warning")
            return redirect(url_for('candidate_auth.sinav_giris'))
        return f(*args, **kwargs)
    return decorated


def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    """Only superadmin can access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu işlem sadece süper admin tarafından yapılabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════
# EXAM ROUTES
# ══════════════════════════════════════════════════════════════
@exam_bp.route('/')
@exam_bp.route('/sinav')
@exam_required
def sinav():
    """Main exam page - displays current question"""
    from app.models import Candidate, Question, ExamAnswer

    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)

    if not candidate:
        session.clear()
        return redirect(url_for('candidate_auth.sinav_giris'))

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

    # SECURITY: Store active question ID to prevent manipulation
    session['active_question_id'] = question.id
    session['question_started_at'] = datetime.utcnow().isoformat()

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
    """Submit answer and get next question"""
    from app.models import Candidate, Question, ExamAnswer

    aday_id = session.get('aday_id')
    soru_id = request.form.get('soru_id', type=int)
    cevap = request.form.get('cevap', '').upper()

    # SECURITY: Validate question ID matches session
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


# ══════════════════════════════════════════════════════════════
# EXAM COMPLETION
# ══════════════════════════════════════════════════════════════
@exam_bp.route('/sinav-bitti')
@exam_required
def sinav_bitti():
    """Exam completion page with results"""
    from app.models import Candidate, ExamAnswer, Question
    import hashlib

    aday_id = session.get('aday_id')
    candidate = Candidate.query.get(aday_id)

    if not candidate:
        return redirect(url_for('candidate_auth.sinav_giris'))

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
    try:
        from app.tasks.webhook_tasks import trigger_exam_completed
        trigger_exam_completed.delay(candidate.id)
    except:
        pass

    return render_template('sinav_bitti.html', 
                          aday=candidate,
                          category_scores=category_scores)


@exam_bp.route('/sonuc/<giris_kodu>')
def sonuc(giris_kodu):
    """Public result page"""
    from app.models import Candidate

    candidate = Candidate.query.filter_by(giris_kodu=giris_kodu).first_or_404()

    if candidate.sinav_durumu != 'tamamlandi':
        flash("Sınav henüz tamamlanmamış.", "warning")
        return redirect(url_for('main.index'))

    return render_template('sinav_bitti.html', aday=candidate)


# ══════════════════════════════════════════════════════════════
# EXAM RESET & TIME EXTENSION
# ══════════════════════════════════════════════════════════════
@exam_bp.route('/reset', methods=['GET'])
@login_required
@superadmin_required
def reset_page():
    """Exam reset page - shows candidates that can be reset"""
    from app.models import Candidate

    sirket_id = session.get('sirket_id')

    # Get candidates with active or completed exams
    query = Candidate.query.filter(
        Candidate.sinav_durumu.in_(['devam_ediyor', 'tamamlandi']),
        Candidate.is_deleted == False
    )

    if sirket_id and session.get('rol') != 'superadmin':
        query = query.filter_by(sirket_id=sirket_id)

    candidates = query.order_by(Candidate.updated_at.desc()).limit(50).all()

    return render_template('exam_reset.html', candidates=candidates)


@exam_bp.route('/reset/<int:candidate_id>', methods=['POST'])
@login_required
def reset_exam(candidate_id):
    """Reset a candidate's exam - clears answers and allows re-entry"""
    from app.models import Candidate, ExamAnswer

    candidate = Candidate.query.get_or_404(candidate_id)
    sirket_id = session.get('sirket_id')
    rol = session.get('rol')

    # Security check
    if rol not in ['super_admin', 'superadmin']:
        if sirket_id and candidate.sirket_id != sirket_id:
            return jsonify({'success': False, 'message': 'Yetkiniz yok'}), 403

    try:
        # Delete all answers for this candidate
        ExamAnswer.query.filter_by(aday_id=candidate_id).delete()

        # Reset candidate exam status
        candidate.sinav_durumu = 'beklemede'
        candidate.puan = None
        candidate.seviye_sonuc = None
        candidate.baslama_tarihi = None
        candidate.bitis_tarihi = None
        candidate.current_difficulty = 'B1'
        candidate.p_grammar = None
        candidate.p_vocabulary = None
        candidate.p_reading = None
        candidate.p_listening = None
        candidate.p_speaking = None
        candidate.p_writing = None

        db.session.commit()

        flash(f"'{candidate.ad_soyad}' sınavı sıfırlandı.", "success")
        return jsonify({'success': True, 'message': 'Sınav sıfırlandı'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@exam_bp.route('/extend-time/<int:candidate_id>', methods=['POST'])
@login_required
def extend_time(candidate_id):
    """Extend exam time for a candidate"""
    from app.models import Candidate

    candidate = Candidate.query.get_or_404(candidate_id)
    sirket_id = session.get('sirket_id')
    rol = session.get('rol')

    # Security check
    if rol not in ['super_admin', 'superadmin']:
        if sirket_id and candidate.sirket_id != sirket_id:
            return jsonify({'success': False, 'message': 'Yetkiniz yok'}), 403

    # Only extend for active exams
    if candidate.sinav_durumu != 'devam_ediyor':
        return jsonify({'success': False, 'message': 'Sadece devam eden sınavlar uzatılabilir'}), 400

    extra_minutes = request.form.get('extra_minutes', 15, type=int)

    try:
        candidate.sinav_suresi += extra_minutes
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': f'{extra_minutes} dakika eklendi',
            'new_duration': candidate.sinav_suresi
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════
@exam_bp.route('/api/status/<int:candidate_id>')
@login_required
def get_exam_status(candidate_id):
    """Get current exam status for a candidate"""
    from app.models import Candidate, ExamAnswer

    candidate = Candidate.query.get_or_404(candidate_id)

    # Calculate progress
    answered = ExamAnswer.query.filter_by(aday_id=candidate_id).count()
    total = candidate.soru_limiti or 25

    # Calculate remaining time
    remaining_seconds = 0
    if candidate.sinav_durumu == 'devam_ediyor' and candidate.baslama_tarihi:
        elapsed = (datetime.utcnow() - candidate.baslama_tarihi).total_seconds()
        remaining_seconds = max(0, (candidate.sinav_suresi * 60) - elapsed)

    return jsonify({
        'status': candidate.sinav_durumu,
        'answered': answered,
        'total': total,
        'progress_pct': round(answered / total * 100) if total > 0 else 0,
        'remaining_seconds': int(remaining_seconds),
        'score': candidate.puan,
        'level': candidate.seviye_sonuc
    })

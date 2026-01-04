# -*- coding: utf-8 -*-
"""
Candidate Routes - Candidate-facing features
FIXED: Field names aligned with Candidate model
FIXED: Dashboard error handling improved
"""
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash, current_app
from app.extensions import db
from datetime import datetime

candidate_bp = Blueprint('candidate', __name__, url_prefix='/candidate')


@candidate_bp.route('/history')
def score_history():
    """Show candidate's exam history"""
    from app.models import Candidate

    # Get candidate from session or email
    email = request.args.get('email') or session.get('candidate_email')
    if not email:
        return render_template('score_history.html', exams=[], avg_score=0, best_level='N/A', improvement=0)

    try:
        # Get all exams for this email - FIXED: using puan and seviye_sonuc
        exams = Candidate.query.filter_by(
            email=email,
            sinav_durumu='tamamlandi',
            is_practice=False
        ).order_by(Candidate.bitis_tarihi.desc()).all()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Score history query failed: {e}")
        exams = []

    # Calculate stats - FIXED: using puan instead of score
    avg_score = sum(e.puan or 0 for e in exams) / len(exams) if exams else 0

    # Best level - FIXED: using seviye_sonuc
    level_order = {'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2': 6}
    best_level = 'N/A'
    if exams:
        exams_with_level = [e for e in exams if e.seviye_sonuc]
        if exams_with_level:
            best_level = max(exams_with_level, key=lambda e: level_order.get(e.seviye_sonuc, 0)).seviye_sonuc

    # Improvement (last vs previous)
    improvement = 0
    if len(exams) >= 2:
        improvement = (exams[0].puan or 0) - (exams[1].puan or 0)

    return render_template('score_history.html',
                          exams=exams,
                          avg_score=avg_score,
                          best_level=best_level,
                          improvement=improvement)


@candidate_bp.route('/progress')
def progress():
    """Show candidate's progress over time with charts"""
    from app.models import Candidate

    email = request.args.get('email') or session.get('candidate_email')
    if not email:
        return render_template('progress.html', 
                              exam_dates=[], 
                              overall_scores=[], 
                              skill_data={'grammar': [], 'vocabulary': [], 'reading': [], 'listening': [], 'speaking': [], 'writing': []},
                              current_level='B1')

    try:
        exams = Candidate.query.filter_by(
            email=email,
            sinav_durumu='tamamlandi',
            is_practice=False
        ).order_by(Candidate.bitis_tarihi.asc()).all()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Progress query failed: {e}")
        exams = []

    exam_dates = [e.bitis_tarihi.strftime('%d/%m') if e.bitis_tarihi else '' for e in exams]
    overall_scores = [e.puan or 0 for e in exams]

    skill_data = {
        'grammar': [e.p_grammar or 0 for e in exams],
        'vocabulary': [e.p_vocabulary or 0 for e in exams],
        'reading': [e.p_reading or 0 for e in exams],
        'listening': [e.p_listening or 0 for e in exams],
        'speaking': [e.p_speaking or 0 for e in exams],
        'writing': [e.p_writing or 0 for e in exams]
    }

    current_level = exams[-1].seviye_sonuc if exams else 'B1'

    return render_template('progress.html',
                          exam_dates=exam_dates,
                          overall_scores=overall_scores,
                          skill_data=skill_data,
                          current_level=current_level)


@candidate_bp.route('/study-plan/<giris_kodu>')
def study_plan(giris_kodu):
    """Show personalized study plan"""
    from app.models import Candidate
    import json

    try:
        candidate = Candidate.query.filter_by(giris_kodu=giris_kodu).first_or_404()
    except Exception as e:
        db.session.rollback()
        flash("Çalışma planı bulunamadı.", "danger")
        return redirect(url_for('main.index'))

    # Check if study plan already exists
    plan = None
    if candidate.admin_notes:
        try:
            notes = json.loads(candidate.admin_notes)
            plan = notes.get('study_plan')
        except:
            pass

    # Generate simple plan if not exists
    if not plan:
        plan = {
            'weeks': [
                {'week': 1, 'focus': 'Grammar Foundations', 'tasks': ['Review tenses', 'Practice exercises']},
                {'week': 2, 'focus': 'Vocabulary Building', 'tasks': ['Learn 50 new words', 'Flashcard practice']},
                {'week': 3, 'focus': 'Reading Skills', 'tasks': ['Read articles', 'Comprehension exercises']},
                {'week': 4, 'focus': 'Review & Practice', 'tasks': ['Take practice test', 'Review weak areas']}
            ]
        }

    # Target level (one level up)
    level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    current_level = candidate.seviye_sonuc or 'B1'
    current_idx = level_order.index(current_level) if current_level in level_order else 2
    target_level = level_order[min(current_idx + 1, 5)]

    return render_template('study_plan.html',
                          aday=candidate,
                          plan=plan,
                          target_level=target_level,
                          estimated_weeks=8)


@candidate_bp.route('/tutorial')
def tutorial():
    """Pre-test tutorial page"""
    return render_template('tutorial.html')


# ══════════════════════════════════════════════════════════════════
# FIXED: Dashboard with proper error handling
# ══════════════════════════════════════════════════════════════════
@candidate_bp.route('/dashboard')
def dashboard():
    """Candidate dashboard after login - FIXED: Added proper error handling"""
    from app.models import Candidate
    
    # Get candidate ID from session
    candidate_id = session.get('candidate_id') or session.get('aday_id')

    # If no session, redirect to exam entry
    if not candidate_id:
        flash("Lütfen giriş yapın.", "warning")
        try:
            return redirect(url_for('candidate_auth.sinav_giris'))
        except:
            # Fallback if candidate_auth blueprint doesn't exist
            return redirect(url_for('auth.sinav_giris'))

    # Try to get candidate from database
    try:
        candidate = Candidate.query.get(candidate_id)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Candidate dashboard query failed: {e}")
        session.clear()
        flash("Bir hata oluştu. Lütfen tekrar giriş yapın.", "danger")
        try:
            return redirect(url_for('candidate_auth.sinav_giris'))
        except:
            return redirect(url_for('auth.sinav_giris'))

    # If candidate not found, clear session
    if not candidate:
        session.clear()
        flash("Aday bulunamadı. Lütfen tekrar giriş yapın.", "warning")
        try:
            return redirect(url_for('candidate_auth.sinav_giris'))
        except:
            return redirect(url_for('auth.sinav_giris'))

    return render_template('candidate_dashboard.html', aday=candidate)


@candidate_bp.route('/offline-sync', methods=['POST'])
def offline_sync():
    """Sync offline exam data"""
    from app.models import Candidate, ExamAnswer

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    candidate_id = data.get('candidate_id')
    answers = data.get('answers', [])

    try:
        candidate = Candidate.query.get(candidate_id)
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

    if not candidate:
        return jsonify({'success': False, 'error': 'Candidate not found'}), 404

    # Save answers
    try:
        for ans in answers:
            existing = ExamAnswer.query.filter_by(
                aday_id=candidate_id,
                soru_id=ans.get('question_id')
            ).first()

            if not existing:
                answer = ExamAnswer(
                    aday_id=candidate_id,
                    soru_id=ans.get('question_id'),
                    verilen_cevap=ans.get('answer'),
                    dogru_mu=ans.get('is_correct', False)
                )
                db.session.add(answer)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'synced': len(answers)})

# -*- coding: utf-8 -*-
"""
Candidate Routes - Candidate-facing features
"""
from flask import Blueprint, render_template, jsonify, request, session
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
    
    # Get all exams for this email
    exams = Candidate.query.filter_by(
        email=email,
        sinav_durumu='tamamlandi',
        is_practice=False
    ).order_by(Candidate.bitis_tarihi.desc()).all()
    
    # Calculate stats
    avg_score = sum(e.puan or 0 for e in exams) / len(exams) if exams else 0
    
    # Best level
    level_order = {'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2': 6}
    best_level = max(exams, key=lambda e: level_order.get(e.seviye_sonuc, 0)).seviye_sonuc if exams else 'N/A'
    
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
    
    exams = Candidate.query.filter_by(
        email=email,
        sinav_durumu='tamamlandi',
        is_practice=False
    ).order_by(Candidate.bitis_tarihi.asc()).all()
    
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
    from app.tasks.ai_tasks import generate_study_plan
    import json
    
    candidate = Candidate.query.filter_by(giris_kodu=giris_kodu).first_or_404()
    
    # Check if study plan already exists
    plan = None
    if candidate.admin_notes:
        try:
            notes = json.loads(candidate.admin_notes)
            plan = notes.get('study_plan')
        except:
            pass
    
    # Generate if not exists
    if not plan:
        plan = generate_study_plan(candidate.id)
    
    # Target level (one level up)
    level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    current_idx = level_order.index(candidate.seviye_sonuc or 'B1') if (candidate.seviye_sonuc in level_order) else 2
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


# Offline Sync API
@candidate_bp.route('/api/batch-sync', methods=['POST'])
def batch_sync():
    """
    Receive batch of answers from offline queue.
    Used when connection is restored after being offline.
    """
    from app.models import Candidate, ExamAnswer, Question
    from app.tasks.calibration_tasks import update_question_stats
    
    data = request.json
    aday_id = data.get('aday_id')
    answers = data.get('answers', [])
    
    candidate = Candidate.query.get(aday_id)
    if not candidate:
        return jsonify({'status': 'error', 'message': 'Aday bulunamadı'}), 404
    
    synced_count = 0
    conflict_count = 0
    
    for answer_data in answers:
        soru_id = answer_data.get('soru_id')
        cevap = answer_data.get('cevap')
        timestamp = answer_data.get('timestamp')
        
        # Check if answer already exists
        existing = ExamAnswer.query.filter_by(
            aday_id=aday_id,
            soru_id=soru_id
        ).first()
        
        if existing:
            # Conflict resolution: keep the later answer
            if timestamp and existing.created_at:
                answer_time = datetime.fromisoformat(timestamp)
                if answer_time > existing.created_at:
                    existing.cevap = cevap
                    existing.created_at = answer_time
                    synced_count += 1
                else:
                    conflict_count += 1
            else:
                conflict_count += 1
        else:
            # Create new answer
            question = Question.query.get(soru_id)
            is_correct = question and cevap == question.dogru_cevap
            
            answer = ExamAnswer(
                aday_id=aday_id,
                soru_id=soru_id,
                cevap=cevap,
                dogru_mu=is_correct,
                created_at=datetime.fromisoformat(timestamp) if timestamp else datetime.utcnow()
            )
            db.session.add(answer)
            synced_count += 1
            
            # Update question stats
            if question:
                update_question_stats.delay(soru_id, is_correct)
    
    db.session.commit()
    
    return jsonify({
        'status': 'ok',
        'synced': synced_count,
        'conflicts': conflict_count,
        'message': f'{synced_count} cevap senkronize edildi.'
    })


@candidate_bp.route('/api/sync-status')
def sync_status():
    """Get sync status for offline indicator"""
    return jsonify({
        'status': 'online',
        'server_time': datetime.utcnow().isoformat()
    })

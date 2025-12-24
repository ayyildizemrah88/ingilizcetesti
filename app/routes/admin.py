# -*- coding: utf-8 -*-
"""
Analytics Routes - Dashboard and reporting endpoints
"""
from flask import Blueprint, render_template, jsonify, request
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/dashboard')
def analytics_dashboard():
    """Main analytics dashboard with real-time stats"""
    from app.models import Candidate, Company, Question
    
    # Get stats
    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    stats = {
        'active_exams': Candidate.query.filter_by(sinav_durumu='devam_ediyor').count(),
        'today_completed': Candidate.query.filter(
            Candidate.sinav_durumu == 'tamamlandi',
            func.date(Candidate.bitis_tarihi) == today
        ).count(),
        'total_candidates': Candidate.query.filter_by(is_deleted=False).count(),
        'avg_score': db.session.query(func.avg(Candidate.puan)).filter(
            Candidate.sinav_durumu == 'tamamlandi'
        ).scalar() or 0,
        'db_response_time': 5,  # Placeholder
        'celery_queue': 0
    }
    
    # CEFR distribution
    cefr_distribution = []
    for level in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
        count = Candidate.query.filter_by(seviye_sonuc=level, sinav_durumu='tamamlandi').count()
        cefr_distribution.append(count)
    
    # Trend data (last 7 days)
    trend_labels = []
    trend_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        trend_labels.append(day.strftime('%d/%m'))
        count = Candidate.query.filter(
            Candidate.sinav_durumu == 'tamamlandi',
            func.date(Candidate.bitis_tarihi) == day
        ).count()
        trend_data.append(count)
    
    # Company stats
    companies = Company.query.limit(5).all()
    company_names = [c.isim for c in companies]
    company_scores = []
    for company in companies:
        avg = db.session.query(func.avg(Candidate.puan)).filter(
            Candidate.sirket_id == company.id,
            Candidate.sinav_durumu == 'tamamlandi'
        ).scalar() or 0
        company_scores.append(round(avg, 1))
    
    # Skill averages
    skill_averages = [
        round(db.session.query(func.avg(Candidate.p_grammar)).scalar() or 0, 1),
        round(db.session.query(func.avg(Candidate.p_vocabulary)).scalar() or 0, 1),
        round(db.session.query(func.avg(Candidate.p_reading)).scalar() or 0, 1),
        round(db.session.query(func.avg(Candidate.p_listening)).scalar() or 0, 1),
        round(db.session.query(func.avg(Candidate.p_speaking)).scalar() or 0, 1),
        round(db.session.query(func.avg(Candidate.p_writing)).scalar() or 0, 1)
    ]
    
    # Top performers
    top_performers = Candidate.query.filter(
        Candidate.sinav_durumu == 'tamamlandi',
        Candidate.bitis_tarihi >= week_ago
    ).order_by(Candidate.puan.desc()).limit(5).all()
    
    # Alerts
    alerts = []
    
    return render_template('analytics_dashboard.html',
                          stats=stats,
                          cefr_distribution=cefr_distribution,
                          trend_labels=trend_labels,
                          trend_data=trend_data,
                          company_names=company_names,
                          company_scores=company_scores,
                          skill_averages=skill_averages,
                          top_performers=top_performers,
                          alerts=alerts)


@analytics_bp.route('/questions')
def question_analytics():
    """Question difficulty and performance analytics"""
    from app.models import Question
    from app.tasks.calibration_tasks import get_calibration_report
    
    # Get calibration report
    report = get_calibration_report()
    
    # Get all questions with stats
    questions = Question.query.filter_by(is_active=True).order_by(Question.id.desc()).limit(100).all()
    
    # Categories
    categories = db.session.query(Question.kategori).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    # Labeled vs calculated distribution
    labeled_dist = []
    calculated_dist = []
    for level in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
        labeled_dist.append(Question.query.filter_by(zorluk=level).count())
        # Calculated based on actual difficulty
        level_map = {'A1': 1, 'A2': 2, 'B1': 3, 'B2': 4, 'C1': 5, 'C2': 6}
        target = level_map.get(level, 3)
        calc_count = Question.query.filter(
            Question.calculated_difficulty.isnot(None),
            Question.calculated_difficulty >= target - 0.5,
            Question.calculated_difficulty < target + 0.5
        ).count()
        calculated_dist.append(calc_count)
    
    # Category accuracy
    cat_names = []
    cat_accuracy = []
    for cat in categories:
        cat_names.append(cat)
        qs = Question.query.filter_by(kategori=cat).all()
        total_correct = sum(q.times_correct or 0 for q in qs)
        total_answered = sum(q.times_answered or 0 for q in qs)
        acc = (total_correct / total_answered * 100) if total_answered else 0
        cat_accuracy.append(round(acc, 1))
    
    # Stats
    stats = {
        'total_questions': Question.query.filter_by(is_active=True).count(),
        'calibrated': Question.query.filter(Question.last_calibrated.isnot(None)).count(),
        'warnings': len(report.get('warnings', [])),
        'avg_accuracy': sum(cat_accuracy) / len(cat_accuracy) if cat_accuracy else 0
    }
    
    return render_template('question_analytics.html',
                          stats=stats,
                          questions=questions,
                          categories=categories,
                          warnings=report.get('warnings', []),
                          labeled_dist=labeled_dist,
                          calculated_dist=calculated_dist,
                          cat_names=cat_names,
                          cat_accuracy=cat_accuracy)


@analytics_bp.route('/fraud')
def fraud_dashboard():
    """Fraud detection dashboard"""
    from app.models import Candidate
    
    # FraudCase model doesn't exist yet, show placeholder stats
    stats = {
        'flagged': 0,
        'plagiarism': 0,
        'ai_detected': 0,
        'proctoring': 0
    }
    
    # Empty lists for placeholders
    flagged_cases = []
    similarity_pairs = []
    proctoring_violations = []
    
    return render_template('fraud_dashboard.html',
                          stats=stats,
                          flagged_cases=flagged_cases,
                          similarity_pairs=similarity_pairs,
                          proctoring_violations=proctoring_violations)


@analytics_bp.route('/team/<int:team_id>')
@analytics_bp.route('/team')
def team_report(team_id=None):
    """Team/department report"""
    from app.models import Candidate, Company
    
    # Get all departments (companies as departments for now)
    departments = Company.query.all()
    
    # Get candidates
    query = Candidate.query.filter_by(is_deleted=False, is_practice=False)
    if team_id:
        query = query.filter_by(sirket_id=team_id)
        team_name = Company.query.get(team_id).isim if team_id else None
    else:
        team_name = None
    
    candidates = query.order_by(Candidate.bitis_tarihi.desc()).all()
    
    # Calculate stats
    completed = [c for c in candidates if c.sinav_durumu == 'tamamlandi']
    stats = {
        'total_candidates': len(candidates),
        'completed': round(len(completed) / len(candidates) * 100) if candidates else 0,
        'avg_score': sum(c.puan or 0 for c in completed) / len(completed) if completed else 0,
        'most_common_level': 'B1',  # Calculate actual
        'skill_averages': {
            'grammar': sum(c.p_grammar or 0 for c in completed) / len(completed) if completed else 0,
            'vocabulary': sum(c.p_vocabulary or 0 for c in completed) / len(completed) if completed else 0,
            'reading': sum(c.p_reading or 0 for c in completed) / len(completed) if completed else 0,
            'listening': sum(c.p_listening or 0 for c in completed) / len(completed) if completed else 0,
            'speaking': sum(c.p_speaking or 0 for c in completed) / len(completed) if completed else 0,
            'writing': sum(c.p_writing or 0 for c in completed) / len(completed) if completed else 0
        }
    }
    
    # Level distribution
    level_distribution = []
    for level in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
        count = len([c for c in completed if c.seviye_sonuc == level])
        level_distribution.append(count)
    
    # Department comparison
    dept_names = [d.isim for d in departments[:5]]
    dept_scores = []
    for dept in departments[:5]:
        dept_candidates = [c for c in completed if c.sirket_id == dept.id]
        avg = sum(c.puan or 0 for c in dept_candidates) / len(dept_candidates) if dept_candidates else 0
        dept_scores.append(round(avg, 1))
    
    return render_template('team_report.html',
                          stats=stats,
                          candidates=candidates[:50],
                          departments=departments,
                          team_id=team_id,
                          team_name=team_name,
                          level_distribution=level_distribution,
                          dept_names=dept_names,
                          dept_scores=dept_scores)


# API Endpoints
@analytics_bp.route('/api/calibrate', methods=['POST'])
def api_calibrate():
    """Trigger question calibration"""
    from app.tasks.calibration_tasks import calibrate_all_questions
    
    result = calibrate_all_questions.delay()
    return jsonify({'status': 'started', 'task_id': result.id})


@analytics_bp.route('/api/questions/<int:question_id>/difficulty', methods=['PATCH'])
def update_question_difficulty(question_id):
    """Update question difficulty manually"""
    from app.models import Question
    from app.models.admin import log_action
    from flask_login import current_user
    
    question = Question.query.get_or_404(question_id)
    new_level = request.json.get('zorluk')
    
    old_level = question.zorluk
    question.zorluk = new_level
    question.calibration_warning = False
    db.session.commit()
    
    # Log action
    log_action(current_user, 'UPDATE', 'question', question_id,
               f'Difficulty changed from {old_level} to {new_level}',
               {'zorluk': old_level}, {'zorluk': new_level}, request)
    
    return jsonify({'status': 'ok'})


@analytics_bp.route('/api/fraud-cases/<int:case_id>/clear', methods=['POST'])
def clear_fraud_case(case_id):
    """Mark fraud case as cleared - FraudCase model not implemented yet"""
    return jsonify({'status': 'error', 'message': 'FraudCase feature not implemented yet'}), 501


@analytics_bp.route('/api/fraud-cases/<int:case_id>/confirm', methods=['POST'])
def confirm_fraud_case(case_id):
    """Confirm fraud case - FraudCase model not implemented yet"""
    return jsonify({'status': 'error', 'message': 'FraudCase feature not implemented yet'}), 501


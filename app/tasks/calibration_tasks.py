# -*- coding: utf-8 -*-
"""
Calibration Tasks - IRT-based question difficulty calibration
"""
from app.celery_app import celery
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# CEFR to numeric difficulty mapping
CEFR_TO_DIFFICULTY = {
    'A1': 1.0, 'A2': 2.0, 'B1': 3.0, 'B2': 4.0, 'C1': 5.0, 'C2': 6.0
}
DIFFICULTY_TO_CEFR = {
    1: 'A1', 2: 'A2', 3: 'B1', 4: 'B2', 5: 'C1', 6: 'C2'
}


@celery.task
def calibrate_all_questions():
    """
    Celery task to calibrate all questions based on response data.
    Runs periodically (e.g., daily via Celery Beat).
    """
    from app.models import Question
    from app.extensions import db
    
    logger.info("Starting question calibration...")
    
    # Get questions with enough data (min 10 responses)
    questions = Question.query.filter(Question.times_answered >= 10).all()
    
    calibrated_count = 0
    warning_count = 0
    
    for question in questions:
        result = calibrate_question(question)
        if result['calibrated']:
            calibrated_count += 1
        if result['warning']:
            warning_count += 1
    
    db.session.commit()
    
    logger.info(f"Calibration complete: {calibrated_count} calibrated, {warning_count} warnings")
    
    return {
        'total': len(questions),
        'calibrated': calibrated_count,
        'warnings': warning_count
    }


def calibrate_question(question):
    """
    Calibrate a single question using Item Response Theory.
    
    The basic IRT difficulty is calculated from:
    - p = proportion correct
    - difficulty = -ln(p / (1 - p))  (logit transform)
    
    Then mapped to CEFR levels.
    """
    import math
    from app.extensions import db
    from datetime import datetime
    
    if question.times_answered < 10:
        return {'calibrated': False, 'warning': False}
    
    # Calculate proportion correct
    p = question.times_correct / question.times_answered
    
    # Avoid division by zero
    if p <= 0.05:
        p = 0.05
    elif p >= 0.95:
        p = 0.95
    
    # Logit transform to get difficulty (higher = harder)
    logit_difficulty = -math.log(p / (1 - p))
    
    # Normalize to 1-6 scale (CEFR)
    # Typical logit range: -3 to +3, map to 1-6
    normalized_difficulty = (logit_difficulty + 3) / 6 * 5 + 1
    normalized_difficulty = max(1, min(6, normalized_difficulty))
    
    question.calculated_difficulty = round(normalized_difficulty, 2)
    question.last_calibrated = datetime.utcnow()
    
    # Check for mismatch with labeled CEFR
    labeled_difficulty = CEFR_TO_DIFFICULTY.get(question.zorluk, 3)
    difference = abs(normalized_difficulty - labeled_difficulty)
    
    # Warning if difference > 1 level
    question.calibration_warning = difference > 1.0
    
    return {
        'calibrated': True,
        'warning': question.calibration_warning,
        'calculated': normalized_difficulty,
        'labeled': labeled_difficulty
    }


def get_suggested_cefr(calculated_difficulty):
    """Convert calculated difficulty to suggested CEFR level."""
    rounded = round(calculated_difficulty)
    return DIFFICULTY_TO_CEFR.get(rounded, 'B1')


@celery.task
def update_question_stats(question_id, is_correct):
    """
    Update question statistics after each answer.
    Called from exam route when answer is submitted.
    """
    from app.models import Question
    from app.extensions import db
    
    question = Question.query.get(question_id)
    if not question:
        return
    
    question.times_answered = (question.times_answered or 0) + 1
    if is_correct:
        question.times_correct = (question.times_correct or 0) + 1
    
    db.session.commit()


def get_calibration_report():
    """
    Generate calibration report for admin dashboard.
    """
    from app.models import Question
    
    questions = Question.query.filter(Question.times_answered >= 10).all()
    
    report = {
        'total_calibrated': len(questions),
        'warnings': [],
        'difficulty_distribution': {
            'A1': 0, 'A2': 0, 'B1': 0, 'B2': 0, 'C1': 0, 'C2': 0
        },
        'mismatches': []
    }
    
    for q in questions:
        if q.zorluk:
            report['difficulty_distribution'][q.zorluk] = \
                report['difficulty_distribution'].get(q.zorluk, 0) + 1
        
        if q.calibration_warning:
            report['warnings'].append({
                'question_id': q.id,
                'labeled': q.zorluk,
                'suggested': get_suggested_cefr(q.calculated_difficulty),
                'accuracy': round(q.times_correct / q.times_answered * 100, 1) if q.times_answered else 0
            })
    
    return report

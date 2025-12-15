# -*- coding: utf-8 -*-
"""
Cleanup Tasks - Automatic Data Retention
KVKK compliant data deletion after retention period
"""
from datetime import datetime, timedelta
import logging

from app.celery_app import celery
from app.extensions import db

logger = logging.getLogger(__name__)


# Data retention periods (in days)
RETENTION_PERIODS = {
    'speaking_recordings': 365,  # 1 year
    'writing_answers': 365,       # 1 year
    'exam_answers': 365,          # 1 year
    'audit_logs': 2 * 365,        # 2 years (legal requirement)
    'consent_logs': 5 * 365,      # 5 years (KVKK requirement)
    'completed_exams': 365,       # 1 year after completion
}


@celery.task
def cleanup_old_speaking_recordings():
    """
    Delete speaking recordings older than retention period.
    Runs weekly via Celery beat.
    
    KVKK compliant: Removes audio data after 1 year.
    """
    from app.models.exam import SpeakingRecording
    from app.models.audit_log import AuditLog
    
    retention_days = RETENTION_PERIODS['speaking_recordings']
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    try:
        # Find old recordings
        old_recordings = SpeakingRecording.query.filter(
            SpeakingRecording.created_at < cutoff_date
        ).all()
        
        count = len(old_recordings)
        
        if count > 0:
            # Log before deletion
            AuditLog.log(
                user_id=0,  # System
                user_email='system@cleanup',
                action='bulk_delete',
                table_name='speaking_recordings',
                description=f'KVKK cleanup: Deleting {count} speaking recordings older than {retention_days} days'
            )
            
            # Delete in batches
            for recording in old_recordings:
                db.session.delete(recording)
            
            db.session.commit()
            logger.info(f"Cleanup: Deleted {count} old speaking recordings")
        
        return {'deleted': count, 'cutoff_date': cutoff_date.isoformat()}
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        db.session.rollback()
        return {'error': str(e)}


@celery.task
def cleanup_old_writing_answers():
    """
    Delete writing answers older than retention period.
    """
    from app.models.exam import WritingAnswer
    from app.models.audit_log import AuditLog
    
    retention_days = RETENTION_PERIODS['writing_answers']
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    try:
        old_answers = WritingAnswer.query.filter(
            WritingAnswer.created_at < cutoff_date
        ).all()
        
        count = len(old_answers)
        
        if count > 0:
            AuditLog.log(
                user_id=0,
                user_email='system@cleanup',
                action='bulk_delete',
                table_name='yazili_cevaplar',
                description=f'KVKK cleanup: Deleting {count} writing answers older than {retention_days} days'
            )
            
            for answer in old_answers:
                db.session.delete(answer)
            
            db.session.commit()
            logger.info(f"Cleanup: Deleted {count} old writing answers")
        
        return {'deleted': count}
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        db.session.rollback()
        return {'error': str(e)}


@celery.task
def cleanup_old_exam_data():
    """
    Anonymize completed exams older than retention period.
    Keeps aggregate data for statistics but removes PII.
    """
    from app.models import Candidate
    from app.models.audit_log import AuditLog
    
    retention_days = RETENTION_PERIODS['completed_exams']
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    try:
        # Find old completed exams
        old_candidates = Candidate.query.filter(
            Candidate.bitis_tarihi < cutoff_date,
            Candidate.sinav_durumu == 'tamamlandi',
            Candidate.is_anonymized != True  # Not already anonymized
        ).all()
        
        count = len(old_candidates)
        
        if count > 0:
            AuditLog.log(
                user_id=0,
                user_email='system@cleanup',
                action='anonymize',
                table_name='adaylar',
                description=f'KVKK cleanup: Anonymizing {count} candidates older than {retention_days} days'
            )
            
            for candidate in old_candidates:
                # Anonymize PII but keep scores for statistics
                candidate.ad_soyad = f"Anonymized_{candidate.id}"
                candidate.email = None
                candidate.tc_kimlik = None
                candidate.cep_no = None
                candidate.giris_kodu = f"EXPIRED_{candidate.id}"
                candidate.is_anonymized = True
            
            db.session.commit()
            logger.info(f"Cleanup: Anonymized {count} old candidates")
        
        return {'anonymized': count}
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        db.session.rollback()
        return {'error': str(e)}


@celery.task
def cleanup_orphan_records():
    """
    Delete orphan records (records without parent).
    Should not happen with proper cascade delete, but safety measure.
    """
    from app.models.exam import SpeakingRecording, ExamAnswer, WritingAnswer
    from app.models import Candidate
    
    orphan_counts = {}
    
    try:
        # Find speaking recordings without candidate
        valid_candidate_ids = db.session.query(Candidate.id).subquery()
        
        orphan_recordings = SpeakingRecording.query.filter(
            ~SpeakingRecording.aday_id.in_(valid_candidate_ids)
        ).delete(synchronize_session='fetch')
        orphan_counts['speaking_recordings'] = orphan_recordings
        
        orphan_answers = ExamAnswer.query.filter(
            ~ExamAnswer.aday_id.in_(valid_candidate_ids)
        ).delete(synchronize_session='fetch')
        orphan_counts['exam_answers'] = orphan_answers
        
        orphan_writing = WritingAnswer.query.filter(
            ~WritingAnswer.aday_id.in_(valid_candidate_ids)
        ).delete(synchronize_session='fetch')
        orphan_counts['writing_answers'] = orphan_writing
        
        db.session.commit()
        
        total = sum(orphan_counts.values())
        if total > 0:
            logger.warning(f"Cleanup: Removed {total} orphan records: {orphan_counts}")
        
        return {'orphans_deleted': orphan_counts}
        
    except Exception as e:
        logger.error(f"Orphan cleanup error: {e}")
        db.session.rollback()
        return {'error': str(e)}


@celery.task
def run_all_cleanup_tasks():
    """
    Master task to run all cleanup tasks.
    Schedule this in Celery beat to run weekly.
    """
    results = {
        'speaking': cleanup_old_speaking_recordings.delay().id,
        'writing': cleanup_old_writing_answers.delay().id,
        'exams': cleanup_old_exam_data.delay().id,
        'orphans': cleanup_orphan_records.delay().id,
    }
    
    logger.info(f"Scheduled all cleanup tasks: {results}")
    return results


@celery.task
def get_data_statistics():
    """
    Get current data statistics for admin dashboard.
    """
    from app.models.exam import SpeakingRecording, WritingAnswer, ExamAnswer
    from app.models import Candidate
    
    try:
        stats = {
            'candidates_total': Candidate.query.count(),
            'candidates_completed': Candidate.query.filter_by(sinav_durumu='tamamlandi').count(),
            'speaking_recordings': SpeakingRecording.query.count(),
            'writing_answers': WritingAnswer.query.count(),
            'exam_answers': ExamAnswer.query.count(),
        }
        
        # Calculate storage estimates (rough)
        # Assume average audio blob is 500KB base64
        stats['estimated_audio_storage_mb'] = (stats['speaking_recordings'] * 0.5)
        
        return stats
        
    except Exception as e:
        return {'error': str(e)}


# Celery Beat Schedule Configuration
CLEANUP_SCHEDULE = {
    'cleanup-speaking-weekly': {
        'task': 'app.tasks.cleanup_tasks.cleanup_old_speaking_recordings',
        'schedule': 7 * 24 * 60 * 60,  # Weekly (in seconds)
    },
    'cleanup-writing-weekly': {
        'task': 'app.tasks.cleanup_tasks.cleanup_old_writing_answers',
        'schedule': 7 * 24 * 60 * 60,
    },
    'cleanup-exams-weekly': {
        'task': 'app.tasks.cleanup_tasks.cleanup_old_exam_data',
        'schedule': 7 * 24 * 60 * 60,
    },
    'cleanup-orphans-daily': {
        'task': 'app.tasks.cleanup_tasks.cleanup_orphan_records',
        'schedule': 24 * 60 * 60,  # Daily
    },
}

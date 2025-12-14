# -*- coding: utf-8 -*-
"""
Celery Application Configuration
"""
from celery import Celery
import os


def make_celery(app=None):
    """
    Create Celery application with Flask integration
    
    Args:
        app: Flask application instance (optional)
    
    Returns:
        Celery application instance
    """
    celery = Celery(
        'skillstestcenter',
        broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        include=[
            'app.tasks.email_tasks',
            'app.tasks.webhook_tasks',
            'app.tasks.ai_tasks',
            'app.tasks.report_tasks'
        ]
    )
    
    celery.conf.update(
        # Task settings
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Europe/Istanbul',
        enable_utc=True,
        
        # Task execution
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        
        # Retry settings
        task_default_retry_delay=60,  # 1 minute
        task_max_retries=3,
        
        # Rate limiting
        task_annotations={
            'app.tasks.email_tasks.send_email_task': {'rate_limit': '10/m'},
            'app.tasks.ai_tasks.evaluate_speaking': {'rate_limit': '5/m'},
        },
        
        # Beat schedule for periodic tasks
        beat_schedule={
            'cleanup-expired-sessions': {
                'task': 'app.tasks.cleanup_tasks.cleanup_sessions',
                'schedule': 3600.0,  # Every hour
            },
            'send-exam-reminders': {
                'task': 'app.tasks.email_tasks.send_exam_reminders',
                'schedule': 86400.0,  # Daily
            },
        }
    )
    
    if app:
        celery.conf.update(app.config)
        
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery


# Create Celery instance
celery = make_celery()

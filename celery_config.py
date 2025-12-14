# -*- coding: utf-8 -*-
"""
Celery Beat Configuration
Scheduled tasks for Skills Test Center
"""
from celery.schedules import crontab, timedelta

# Celery Beat Schedule
beat_schedule = {
    
    # ====================
    # DATABASE BACKUP
    # ====================
    'daily-database-backup': {
        'task': 'app.tasks.backup_tasks.backup_database',
        'schedule': crontab(hour=3, minute=0),  # Every day at 03:00
        'options': {'queue': 'backup'}
    },
    
    'weekly-cleanup-old-backups': {
        'task': 'app.tasks.backup_tasks.cleanup_old_backups',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),  # Sunday 04:00
        'options': {'queue': 'backup'}
    },
    
    # ====================
    # QUESTION CALIBRATION
    # ====================
    'nightly-question-calibration': {
        'task': 'app.tasks.calibration_tasks.calibrate_all_questions',
        'schedule': crontab(hour=2, minute=0),  # Every day at 02:00
        'options': {'queue': 'calibration'}
    },
    
    # ====================
    # SCHEDULED EMAILS
    # ====================
    'hourly-exam-reminders': {
        'task': 'app.tasks.email_tasks.send_scheduled_reminders',
        'schedule': crontab(minute=0),  # Every hour at :00
        'options': {'queue': 'email'}
    },
    
    # ====================
    # CLEANUP TASKS
    # ====================
    'daily-cleanup-expired-sessions': {
        'task': 'app.tasks.cleanup_tasks.cleanup_expired_sessions',
        'schedule': crontab(hour=5, minute=0),  # Every day at 05:00
    },
    
    'weekly-cleanup-orphan-files': {
        'task': 'app.tasks.cleanup_tasks.cleanup_orphan_files',
        'schedule': crontab(hour=6, minute=0, day_of_week='saturday'),  # Saturday 06:00
    },
    
    # ====================
    # HEALTH CHECKS
    # ====================
    'every-5min-health-check': {
        'task': 'app.tasks.monitoring_tasks.health_check',
        'schedule': timedelta(minutes=5),
    },
}

# Celery Configuration
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'

# Task settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'Europe/Istanbul'
enable_utc = True

# Task routing
task_routes = {
    'app.tasks.backup_tasks.*': {'queue': 'backup'},
    'app.tasks.calibration_tasks.*': {'queue': 'calibration'},
    'app.tasks.email_tasks.*': {'queue': 'email'},
    'app.tasks.ai_tasks.*': {'queue': 'ai'},
}

# Rate limits
task_annotations = {
    'app.tasks.ai_tasks.*': {'rate_limit': '10/m'},  # Max 10 AI calls per minute
    'app.tasks.email_tasks.*': {'rate_limit': '100/m'},  # Max 100 emails per minute
}

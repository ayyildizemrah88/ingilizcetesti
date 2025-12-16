# -*- coding: utf-8 -*-
"""
BLOB Migration Task
Migrates audio data from database BLOB to file system storage.
Run this once to clean up existing BLOB data.
"""
import logging
from datetime import datetime

from app.celery_app import celery
from app.extensions import db

logger = logging.getLogger(__name__)


@celery.task
def migrate_blob_to_file_storage():
    """
    Migrate all existing BLOB audio data to file-based storage.
    
    This is a one-time migration task to:
    1. Find all SpeakingRecording with audio_blob data
    2. Save audio to file system
    3. Clear audio_blob field
    4. Update audio_file_path
    
    Run with: celery -A app.celery_app call app.tasks.cleanup_tasks.migrate_blob_to_file_storage
    """
    from app.models.exam import SpeakingRecording
    from app.utils.audio_storage import audio_storage
    
    results = {
        'total': 0,
        'migrated': 0,
        'failed': 0,
        'already_migrated': 0,
        'errors': []
    }
    
    try:
        # Find all recordings with BLOB data but no file path
        recordings = SpeakingRecording.query.filter(
            SpeakingRecording.audio_blob.isnot(None),
            SpeakingRecording.audio_blob != ''
        ).all()
        
        results['total'] = len(recordings)
        logger.info(f"Starting BLOB migration for {results['total']} recordings")
        
        for recording in recordings:
            try:
                # Skip if already has file path
                if recording.audio_file_path:
                    results['already_migrated'] += 1
                    continue
                
                # Save audio to file system
                recording.save_audio_base64(recording.audio_blob)
                
                # Clear BLOB field to free database space
                recording.audio_blob = None
                
                results['migrated'] += 1
                
                # Commit in batches of 100
                if results['migrated'] % 100 == 0:
                    db.session.commit()
                    logger.info(f"Migrated {results['migrated']} recordings...")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'recording_id': recording.id,
                    'error': str(e)
                })
                logger.error(f"Failed to migrate recording {recording.id}: {e}")
        
        # Final commit
        db.session.commit()
        
        logger.info(f"BLOB migration complete: {results}")
        return results
        
    except Exception as e:
        logger.error(f"BLOB migration failed: {e}")
        db.session.rollback()
        return {'error': str(e)}


@celery.task
def cleanup_migrated_blobs():
    """
    Remove BLOB data from recordings that have been migrated.
    This is a safety task to run after verifying migration was successful.
    
    Only clears audio_blob where audio_file_path exists and is valid.
    """
    from app.models.exam import SpeakingRecording
    from app.utils.audio_storage import audio_storage
    
    results = {
        'cleaned': 0,
        'invalid_files': 0,
        'errors': []
    }
    
    try:
        # Find recordings with both BLOB and file path
        recordings = SpeakingRecording.query.filter(
            SpeakingRecording.audio_blob.isnot(None),
            SpeakingRecording.audio_file_path.isnot(None)
        ).all()
        
        for recording in recordings:
            try:
                # Verify file exists
                if audio_storage.get_audio_path(recording.audio_file_path).exists():
                    recording.audio_blob = None
                    results['cleaned'] += 1
                else:
                    results['invalid_files'] += 1
                    
            except Exception as e:
                results['errors'].append({
                    'recording_id': recording.id,
                    'error': str(e)
                })
        
        db.session.commit()
        logger.info(f"BLOB cleanup complete: {results}")
        return results
        
    except Exception as e:
        logger.error(f"BLOB cleanup failed: {e}")
        db.session.rollback()
        return {'error': str(e)}


@celery.task
def get_blob_storage_stats():
    """
    Get statistics about BLOB storage usage.
    Useful for monitoring migration progress.
    """
    from app.models.exam import SpeakingRecording
    from sqlalchemy import func
    
    try:
        total_recordings = SpeakingRecording.query.count()
        
        with_blob = SpeakingRecording.query.filter(
            SpeakingRecording.audio_blob.isnot(None),
            SpeakingRecording.audio_blob != ''
        ).count()
        
        with_file = SpeakingRecording.query.filter(
            SpeakingRecording.audio_file_path.isnot(None)
        ).count()
        
        both = SpeakingRecording.query.filter(
            SpeakingRecording.audio_blob.isnot(None),
            SpeakingRecording.audio_file_path.isnot(None)
        ).count()
        
        # Estimate BLOB storage size (rough estimate)
        # Assume average base64 audio is 500KB
        estimated_blob_mb = (with_blob * 0.5)
        
        return {
            'total_recordings': total_recordings,
            'with_blob_only': with_blob - both,
            'with_file_only': with_file - both,
            'with_both': both,
            'fully_migrated': with_file - both,
            'pending_migration': with_blob - both,
            'estimated_blob_storage_mb': round(estimated_blob_mb, 2),
            'migration_progress_percent': round((with_file / total_recordings * 100) if total_recordings > 0 else 0, 1)
        }
        
    except Exception as e:
        return {'error': str(e)}

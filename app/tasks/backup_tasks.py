# -*- coding: utf-8 -*-
"""
Database Backup Tasks with Google Drive Integration
Automated backup system for Skills Test Center
"""
import os
import gzip
import shutil
import logging
from datetime import datetime, timedelta
from celery import shared_task

logger = logging.getLogger(__name__)


# ====================
# BACKUP CONFIGURATION
# ====================

BACKUP_CONFIG = {
    'local_backup_dir': os.getenv('BACKUP_DIR', '/tmp/backups'),
    'keep_local_days': int(os.getenv('BACKUP_KEEP_DAYS', 7)),
    'google_drive_folder_id': os.getenv('GOOGLE_DRIVE_BACKUP_FOLDER_ID', ''),
    'enable_google_drive': os.getenv('ENABLE_GOOGLE_DRIVE_BACKUP', 'false').lower() == 'true',
}


# ====================
# LOCAL BACKUP TASKS
# ====================

@shared_task(bind=True, max_retries=3)
def backup_database(self):
    """
    Create a compressed backup of the PostgreSQL database.
    Runs daily via Celery Beat.
    """
    try:
        backup_dir = BACKUP_CONFIG['local_backup_dir']
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"skillstest_backup_{timestamp}.sql"
        backup_path = os.path.join(backup_dir, backup_filename)
        compressed_path = f"{backup_path}.gz"
        
        # Get database URL
        database_url = os.getenv('DATABASE_URL', '')
        if not database_url:
            logger.error("DATABASE_URL not set, cannot backup")
            return {'success': False, 'error': 'DATABASE_URL not set'}
        
        # Parse database URL
        db_info = parse_database_url(database_url)
        if not db_info:
            return {'success': False, 'error': 'Invalid DATABASE_URL format'}
        
        # Create backup using pg_dump
        import subprocess
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_info['password']
        
        cmd = [
            'pg_dump',
            '-h', db_info['host'],
            '-p', str(db_info['port']),
            '-U', db_info['user'],
            '-d', db_info['database'],
            '-f', backup_path,
            '--no-owner',
            '--no-privileges',
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return {'success': False, 'error': result.stderr}
        
        # Compress backup
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed file
        os.remove(backup_path)
        
        # Get file size
        file_size = os.path.getsize(compressed_path)
        
        logger.info(f"✅ Database backup created: {compressed_path} ({file_size / 1024 / 1024:.2f} MB)")
        
        # Upload to Google Drive if enabled
        if BACKUP_CONFIG['enable_google_drive']:
            upload_to_google_drive.delay(compressed_path)
        
        # Cleanup old backups
        cleanup_old_backups.delay()
        
        return {
            'success': True,
            'path': compressed_path,
            'size_mb': round(file_size / 1024 / 1024, 2),
            'timestamp': timestamp
        }
        
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        self.retry(countdown=300, exc=e)  # Retry in 5 minutes


@shared_task
def cleanup_old_backups():
    """Remove local backups older than configured days."""
    try:
        backup_dir = BACKUP_CONFIG['local_backup_dir']
        keep_days = BACKUP_CONFIG['keep_local_days']
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        removed_count = 0
        
        for filename in os.listdir(backup_dir):
            if filename.startswith('skillstest_backup_') and filename.endswith('.sql.gz'):
                filepath = os.path.join(backup_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_time < cutoff_date:
                    os.remove(filepath)
                    removed_count += 1
                    logger.info(f"Removed old backup: {filename}")
        
        return {'removed': removed_count}
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return {'error': str(e)}


# ====================
# GOOGLE DRIVE BACKUP
# ====================

@shared_task(bind=True, max_retries=3)
def upload_to_google_drive(self, file_path):
    """
    Upload backup file to Google Drive.
    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
        folder_id = BACKUP_CONFIG['google_drive_folder_id']
        
        if not credentials_path or not folder_id:
            logger.warning("Google Drive credentials or folder ID not configured")
            return {'success': False, 'error': 'Not configured'}
        
        # Authenticate
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        
        # Prepare file metadata
        filename = os.path.basename(file_path)
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        # Upload file
        media = MediaFileUpload(
            file_path,
            mimetype='application/gzip',
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, size'
        ).execute()
        
        logger.info(f"✅ Uploaded to Google Drive: {file['name']} (ID: {file['id']})")
        
        # Cleanup old Drive backups (keep last 30)
        cleanup_old_drive_backups.delay()
        
        return {
            'success': True,
            'file_id': file['id'],
            'name': file['name']
        }
        
    except ImportError:
        logger.error("Google Drive libraries not installed. Run: pip install google-auth google-api-python-client")
        return {'success': False, 'error': 'Libraries not installed'}
    except Exception as e:
        logger.error(f"Google Drive upload failed: {str(e)}")
        self.retry(countdown=600, exc=e)  # Retry in 10 minutes


@shared_task
def cleanup_old_drive_backups(keep_count=30):
    """Remove old backups from Google Drive, keeping the most recent ones."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
        folder_id = BACKUP_CONFIG['google_drive_folder_id']
        
        if not credentials_path or not folder_id:
            return {'success': False, 'error': 'Not configured'}
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        
        # List all backup files
        results = service.files().list(
            q=f"'{folder_id}' in parents and name contains 'skillstest_backup_'",
            orderBy='createdTime desc',
            fields='files(id, name, createdTime)'
        ).execute()
        
        files = results.get('files', [])
        
        # Delete old files beyond keep_count
        deleted_count = 0
        if len(files) > keep_count:
            for file in files[keep_count:]:
                service.files().delete(fileId=file['id']).execute()
                deleted_count += 1
                logger.info(f"Deleted old Drive backup: {file['name']}")
        
        return {'deleted': deleted_count}
        
    except Exception as e:
        logger.error(f"Drive cleanup failed: {str(e)}")
        return {'error': str(e)}


# ====================
# HELPER FUNCTIONS
# ====================

def parse_database_url(url):
    """Parse PostgreSQL connection URL."""
    try:
        # Format: postgresql://user:password@host:port/database
        import re
        pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
        match = re.match(pattern, url)
        
        if match:
            return {
                'user': match.group(1),
                'password': match.group(2),
                'host': match.group(3),
                'port': int(match.group(4)),
                'database': match.group(5)
            }
        return None
    except Exception:
        return None


@shared_task
def get_backup_status():
    """Get current backup status and statistics."""
    try:
        backup_dir = BACKUP_CONFIG['local_backup_dir']
        
        if not os.path.exists(backup_dir):
            return {'backups': [], 'total_size_mb': 0}
        
        backups = []
        total_size = 0
        
        for filename in sorted(os.listdir(backup_dir), reverse=True):
            if filename.startswith('skillstest_backup_') and filename.endswith('.sql.gz'):
                filepath = os.path.join(backup_dir, filename)
                size = os.path.getsize(filepath)
                total_size += size
                
                backups.append({
                    'filename': filename,
                    'size_mb': round(size / 1024 / 1024, 2),
                    'created': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                })
        
        return {
            'backups': backups[:10],  # Last 10
            'total_count': len(backups),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'google_drive_enabled': BACKUP_CONFIG['enable_google_drive']
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return {'error': str(e)}


# ====================
# RESTORE FUNCTION
# ====================

@shared_task(bind=True)
def restore_database(self, backup_filename):
    """
    Restore database from a backup file.
    USE WITH CAUTION - This will overwrite the current database!
    """
    try:
        backup_dir = BACKUP_CONFIG['local_backup_dir']
        compressed_path = os.path.join(backup_dir, backup_filename)
        
        if not os.path.exists(compressed_path):
            return {'success': False, 'error': 'Backup file not found'}
        
        database_url = os.getenv('DATABASE_URL', '')
        db_info = parse_database_url(database_url)
        
        if not db_info:
            return {'success': False, 'error': 'Invalid DATABASE_URL'}
        
        # Decompress backup
        sql_path = compressed_path.replace('.gz', '')
        with gzip.open(compressed_path, 'rb') as f_in:
            with open(sql_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Restore using psql
        import subprocess
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_info['password']
        
        cmd = [
            'psql',
            '-h', db_info['host'],
            '-p', str(db_info['port']),
            '-U', db_info['user'],
            '-d', db_info['database'],
            '-f', sql_path,
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        # Cleanup
        os.remove(sql_path)
        
        if result.returncode != 0:
            logger.error(f"Restore failed: {result.stderr}")
            return {'success': False, 'error': result.stderr}
        
        logger.info(f"✅ Database restored from: {backup_filename}")
        
        return {'success': True, 'restored_from': backup_filename}
        
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}")
        return {'success': False, 'error': str(e)}

# -*- coding: utf-8 -*-
"""
Audio Storage Utility
File-based audio storage instead of database BLOB
Supports local filesystem and S3-compatible storage
"""
import os
import uuid
import base64
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Default storage configuration
AUDIO_STORAGE_PATH = os.getenv('AUDIO_STORAGE_PATH', 'static/audio')
AUDIO_STORAGE_TYPE = os.getenv('AUDIO_STORAGE_TYPE', 'local')  # 'local' or 's3'

# S3 Configuration (optional)
S3_BUCKET = os.getenv('S3_AUDIO_BUCKET', '')
S3_REGION = os.getenv('S3_REGION', 'eu-central-1')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', '')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', '')


class AudioStorage:
    """
    Audio file storage handler.
    
    Stores audio files on disk instead of database BLOB.
    Database only stores the file path reference.
    
    Benefits:
    - Database stays small and fast
    - Easy to backup audio files separately
    - Can migrate to S3/cloud storage later
    - Better for caching and CDN
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or AUDIO_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, candidate_id: int, question_id: int, extension: str = 'webm') -> str:
        """Generate unique filename for audio file."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        return f"speaking_{candidate_id}_{question_id}_{timestamp}_{unique_id}.{extension}"
    
    def _get_subdir(self, candidate_id: int) -> Path:
        """
        Get subdirectory for candidate's audio files.
        Uses candidate_id modulo to distribute files across folders.
        Prevents having too many files in one directory.
        """
        # Create subdirectory structure: /audio/00-99/
        subdir = f"{candidate_id % 100:02d}"
        path = self.base_path / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def save_audio(self, audio_data: bytes, candidate_id: int, question_id: int,
                   extension: str = 'webm') -> Tuple[str, int]:
        """
        Save audio file to disk.
        
        Args:
            audio_data: Raw audio bytes (not base64)
            candidate_id: Candidate ID
            question_id: Question ID
            extension: File extension
            
        Returns:
            Tuple of (relative_file_path, file_size_bytes)
        """
        filename = self._generate_filename(candidate_id, question_id, extension)
        subdir = self._get_subdir(candidate_id)
        file_path = subdir / filename
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        file_size = len(audio_data)
        relative_path = str(file_path.relative_to(self.base_path))
        
        logger.info(f"Saved audio: {relative_path} ({file_size} bytes)")
        return relative_path, file_size
    
    def save_audio_base64(self, audio_base64: str, candidate_id: int, question_id: int,
                          extension: str = 'webm') -> Tuple[str, int]:
        """
        Save base64-encoded audio to disk.
        
        Args:
            audio_base64: Base64 encoded audio string
            candidate_id: Candidate ID
            question_id: Question ID
            extension: File extension
            
        Returns:
            Tuple of (relative_file_path, file_size_bytes)
        """
        # Decode base64
        audio_data = base64.b64decode(audio_base64)
        return self.save_audio(audio_data, candidate_id, question_id, extension)
    
    def get_audio_path(self, relative_path: str) -> Path:
        """Get absolute path to audio file."""
        return self.base_path / relative_path
    
    def get_audio_data(self, relative_path: str) -> Optional[bytes]:
        """Read audio file from disk."""
        file_path = self.get_audio_path(relative_path)
        
        if not file_path.exists():
            logger.warning(f"Audio file not found: {relative_path}")
            return None
        
        with open(file_path, 'rb') as f:
            return f.read()
    
    def get_audio_base64(self, relative_path: str) -> Optional[str]:
        """Read audio file and return as base64."""
        audio_data = self.get_audio_data(relative_path)
        if audio_data:
            return base64.b64encode(audio_data).decode('utf-8')
        return None
    
    def delete_audio(self, relative_path: str) -> bool:
        """Delete audio file from disk."""
        file_path = self.get_audio_path(relative_path)
        
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Deleted audio: {relative_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete audio: {e}")
                return False
        return False
    
    def get_file_size(self, relative_path: str) -> int:
        """Get file size in bytes."""
        file_path = self.get_audio_path(relative_path)
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        total_files = 0
        total_size = 0
        
        for file_path in self.base_path.rglob('*.webm'):
            total_files += 1
            total_size += file_path.stat().st_size
        
        for file_path in self.base_path.rglob('*.mp3'):
            total_files += 1
            total_size += file_path.stat().st_size
        
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'storage_path': str(self.base_path)
        }


class S3AudioStorage(AudioStorage):
    """
    S3-compatible audio storage.
    Use this for production with AWS S3, MinIO, or DigitalOcean Spaces.
    """
    
    def __init__(self):
        super().__init__()
        self.bucket = S3_BUCKET
        self._client = None
    
    @property
    def client(self):
        """Lazy S3 client initialization."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    's3',
                    region_name=S3_REGION,
                    aws_access_key_id=S3_ACCESS_KEY,
                    aws_secret_access_key=S3_SECRET_KEY
                )
            except ImportError:
                logger.error("boto3 not installed for S3 storage")
                raise
        return self._client
    
    def save_audio(self, audio_data: bytes, candidate_id: int, question_id: int,
                   extension: str = 'webm') -> Tuple[str, int]:
        """Save audio to S3."""
        filename = self._generate_filename(candidate_id, question_id, extension)
        key = f"audio/{candidate_id % 100:02d}/{filename}"
        
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=audio_data,
                ContentType=f'audio/{extension}'
            )
            
            logger.info(f"Uploaded to S3: {key} ({len(audio_data)} bytes)")
            return key, len(audio_data)
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            # Fallback to local storage
            return super().save_audio(audio_data, candidate_id, question_id, extension)
    
    def get_audio_data(self, key: str) -> Optional[bytes]:
        """Read audio from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read()
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            # Fallback to local
            return super().get_audio_data(key)
    
    def delete_audio(self, key: str) -> bool:
        """Delete audio from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted from S3: {key}")
            return True
        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
            return False


def get_audio_storage() -> AudioStorage:
    """Get configured audio storage instance."""
    if AUDIO_STORAGE_TYPE == 's3' and S3_BUCKET:
        return S3AudioStorage()
    return AudioStorage()


# Global instance
audio_storage = get_audio_storage()

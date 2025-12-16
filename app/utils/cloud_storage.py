# -*- coding: utf-8 -*-
"""
Cloud Storage Backend - S3/MinIO/GCS/Local abstraction
Supports multiple storage providers for scalable file storage.
"""
import os
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, BinaryIO

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def save(self, file_data: bytes, path: str) -> str:
        """Save file and return URL/path."""
        pass
    
    @abstractmethod
    def get(self, path: str) -> Optional[bytes]:
        """Get file content by path."""
        pass
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete file by path."""
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """Get signed URL for file access."""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.getenv('AUDIO_STORAGE_PATH', './storage')
        os.makedirs(self.base_path, exist_ok=True)
    
    def _full_path(self, path: str) -> str:
        return os.path.join(self.base_path, path)
    
    def save(self, file_data: bytes, path: str) -> str:
        full_path = self._full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"Saved file to local: {path}")
        return path
    
    def get(self, path: str) -> Optional[bytes]:
        full_path = self._full_path(path)
        if not os.path.exists(full_path):
            return None
        
        with open(full_path, 'rb') as f:
            return f.read()
    
    def delete(self, path: str) -> bool:
        full_path = self._full_path(path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
    
    def exists(self, path: str) -> bool:
        return os.path.exists(self._full_path(path))
    
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        # For local storage, return relative path (served by app)
        return f"/storage/{path}"


class S3StorageBackend(StorageBackend):
    """AWS S3 / MinIO storage backend."""
    
    def __init__(self):
        import boto3
        from botocore.config import Config
        
        self.bucket = os.getenv('S3_BUCKET', 'skillstestcenter')
        self.region = os.getenv('S3_REGION', 'eu-central-1')
        
        # Support custom endpoint for MinIO
        endpoint_url = os.getenv('S3_ENDPOINT_URL')
        
        config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )
        
        self.client = boto3.client(
            's3',
            region_name=self.region,
            endpoint_url=endpoint_url,
            aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('S3_SECRET_KEY'),
            config=config
        )
        
        logger.info(f"Initialized S3 backend: {self.bucket}")
    
    def save(self, file_data: bytes, path: str) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=path,
            Body=file_data,
            ContentType=self._get_content_type(path)
        )
        logger.info(f"Saved file to S3: {path}")
        return path
    
    def get(self, path: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=path)
            return response['Body'].read()
        except self.client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.error(f"S3 get error: {e}")
            return None
    
    def delete(self, path: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=path)
            return True
        except Exception as e:
            logger.error(f"S3 delete error: {e}")
            return False
    
    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except:
            return False
    
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for temporary access."""
        url = self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': path},
            ExpiresIn=expires_in
        )
        return url
    
    def _get_content_type(self, path: str) -> str:
        ext = path.split('.')[-1].lower()
        content_types = {
            'webm': 'audio/webm',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg',
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg'
        }
        return content_types.get(ext, 'application/octet-stream')


class GCSStorageBackend(StorageBackend):
    """Google Cloud Storage backend."""
    
    def __init__(self):
        from google.cloud import storage
        
        self.bucket_name = os.getenv('GCS_BUCKET', 'skillstestcenter')
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)
        
        logger.info(f"Initialized GCS backend: {self.bucket_name}")
    
    def save(self, file_data: bytes, path: str) -> str:
        blob = self.bucket.blob(path)
        blob.upload_from_string(file_data)
        logger.info(f"Saved file to GCS: {path}")
        return path
    
    def get(self, path: str) -> Optional[bytes]:
        try:
            blob = self.bucket.blob(path)
            return blob.download_as_bytes()
        except Exception as e:
            logger.error(f"GCS get error: {e}")
            return None
    
    def delete(self, path: str) -> bool:
        try:
            blob = self.bucket.blob(path)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"GCS delete error: {e}")
            return False
    
    def exists(self, path: str) -> bool:
        blob = self.bucket.blob(path)
        return blob.exists()
    
    def get_url(self, path: str, expires_in: int = 3600) -> str:
        from datetime import timedelta
        blob = self.bucket.blob(path)
        return blob.generate_signed_url(expiration=timedelta(seconds=expires_in))


# ══════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ══════════════════════════════════════════════════════════════════

_storage_instance = None

def get_storage() -> StorageBackend:
    """
    Get the configured storage backend singleton.
    
    Environment Variables:
        STORAGE_TYPE: 'local', 's3', 'gcs', or 'minio'
        S3_BUCKET, S3_REGION, S3_ACCESS_KEY, S3_SECRET_KEY
        S3_ENDPOINT_URL (for MinIO)
        GCS_BUCKET
    """
    global _storage_instance
    
    if _storage_instance is not None:
        return _storage_instance
    
    storage_type = os.getenv('STORAGE_TYPE', 'local').lower()
    
    if storage_type == 's3' or storage_type == 'minio':
        _storage_instance = S3StorageBackend()
    elif storage_type == 'gcs':
        _storage_instance = GCSStorageBackend()
    else:
        _storage_instance = LocalStorageBackend()
    
    logger.info(f"Storage backend initialized: {storage_type}")
    return _storage_instance


def generate_file_path(prefix: str, filename: str, unique: bool = True) -> str:
    """
    Generate a structured file path.
    
    Example: audio/2024/01/15/abc123_recording.webm
    """
    now = datetime.utcnow()
    date_path = now.strftime('%Y/%m/%d')
    
    if unique:
        unique_id = hashlib.md5(f"{datetime.utcnow().isoformat()}{filename}".encode()).hexdigest()[:8]
        filename = f"{unique_id}_{filename}"
    
    return f"{prefix}/{date_path}/{filename}"

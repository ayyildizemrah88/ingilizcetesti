# -*- coding: utf-8 -*-
"""
Configuration classes for Skills Test Center
"""
import os
from datetime import timedelta


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', '')
    
    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    
    # Upload
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/tmp/uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    
    # Email
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASS = os.getenv('SMTP_PASS', '')
    
    # AI Services
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Celery
    CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Swagger
    SWAGGER = {
        'title': 'Skills Test Center API',
        'version': '2.0',
        'description': 'International English Proficiency Testing API',
        'uiversion': 3,
        'specs_route': '/apidocs/'
    }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///skillstest_dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # Log SQL queries


class ProductionConfig(Config):
    """
    Production configuration
    
    ══════════════════════════════════════════════════════════════════
    DATABASE CONNECTION POOL SIZING
    ══════════════════════════════════════════════════════════════════
    
    PostgreSQL has a default max_connections of 100.
    Each component uses connections:
    
    - Web Workers (Gunicorn): workers × pool_size = 4 × 5 = 20
    - Celery Workers: concurrency × pool_size = 8 × 5 = 40
    - Celery Beat: 1 × pool_size = 5
    - Other services: ~5
    
    FORMULA:
        Max connections needed = (gunicorn_workers + celery_workers) × pool_size + overflow
        
    EXAMPLE (Conservative):
        Gunicorn: 4 workers
        Celery: 4 workers (concurrency=4)
        Pool size: 5
        Overflow: 10
        Total: (4 + 4) × 5 + 10 = 50 connections
        
    IMPORTANT:
        If you increase Celery concurrency, adjust DB pool accordingly:
        - celery -A celery_config worker --concurrency=8  ← 8 workers
        - Set SQLALCHEMY_POOL_SIZE based on: total_workers / process_count
    ══════════════════════════════════════════════════════════════════
    """
    DEBUG = False
    TESTING = False
    
    # SQLAlchemy - PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', '')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ═══════════════════════════════════════════════════════════════
    # CONNECTION POOL CONFIGURATION
    # ═══════════════════════════════════════════════════════════════
    
    # Pool size per process (adjust based on Celery concurrency)
    # Default: 5 connections per process
    # Formula: pool_size = max_db_connections / (gunicorn_workers + celery_workers)
    SQLALCHEMY_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 5))
    
    # Overflow connections for burst traffic
    # These are created when pool is exhausted, then recycled
    SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', 10))
    
    # Connection recycling (prevent stale connections)
    # Recycle connections after 30 minutes
    SQLALCHEMY_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', 1800))
    
    # Pre-ping: check connection before using
    # Prevents "server closed connection" errors
    SQLALCHEMY_POOL_PRE_PING = True
    
    # Connection timeout (seconds)
    SQLALCHEMY_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', 30))
    
    # Engine options for additional tuning
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'skillstestcenter'
        }
    }


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


# Weak/default secret keys that should never be used in production
WEAK_SECRET_KEYS = [
    'your-secret-key-change-in-production',
    'your-super-secret-key',
    'change-this-in-production',
    'secret-key',
    'dev-secret-key',
    'test-secret-key',
]


def validate_production_config():
    """
    Validate configuration for production environment.
    Raises ValueError if critical settings are missing or insecure.
    """
    import sys
    import logging
    
    logger = logging.getLogger(__name__)
    env = os.getenv('FLASK_ENV', 'development')
    
    if env != 'production':
        return True  # Skip validation in non-production
    
    errors = []
    warnings = []
    
    # Check SECRET_KEY
    secret_key = os.getenv('SECRET_KEY', '')
    if not secret_key:
        errors.append("SECRET_KEY is not set")
    elif secret_key in WEAK_SECRET_KEYS:
        errors.append(f"SECRET_KEY is using a weak default value")
    elif len(secret_key) < 32:
        warnings.append("SECRET_KEY should be at least 32 characters")
    
    # Check JWT_SECRET
    jwt_secret = os.getenv('JWT_SECRET', '')
    if jwt_secret and jwt_secret in WEAK_SECRET_KEYS:
        warnings.append("JWT_SECRET is using a weak default value")
    
    # Check DATABASE_URL
    db_url = os.getenv('DATABASE_URL', '')
    if not db_url:
        errors.append("DATABASE_URL is not set")
    elif 'sqlite' in db_url.lower():
        warnings.append("SQLite is not recommended for production")
    
    # Check SENTRY_DSN (recommended for production)
    sentry_dsn = os.getenv('SENTRY_DSN', '')
    if not sentry_dsn:
        warnings.append("SENTRY_DSN is not set - error tracking disabled")
    
    # Log warnings
    for warning in warnings:
        logger.warning(f"⚠️ Production Warning: {warning}")
    
    # Handle errors
    if errors:
        for error in errors:
            logger.error(f"❌ Production Error: {error}")
        
        print("\n" + "="*60)
        print("❌ CRITICAL PRODUCTION CONFIGURATION ERRORS:")
        print("="*60)
        for error in errors:
            print(f"  • {error}")
        print("="*60)
        print("Please fix these issues before deploying to production.")
        print("="*60 + "\n")
        
        # Exit if critical errors
        sys.exit(1)
    
    return True


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    
    # Validate production config
    if env == 'production':
        validate_production_config()
    
    return config.get(env, config['default'])


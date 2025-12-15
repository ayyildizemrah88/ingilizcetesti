# -*- coding: utf-8 -*-
"""
Flask Application Factory
"""
import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config import get_config


def create_app(config_class=None):
    """
    Application factory pattern for Flask
    
    Args:
        config_class: Configuration class to use (optional)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    
    # Proxy fix for deployment behind reverse proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    
    # Initialize Sentry for error tracking (production)
    init_sentry(app)
    
    # Configure logging
    configure_logging(app)
    
    # Initialize extensions
    from app.extensions import init_extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register context processors
    register_context_processors(app)
    
    # Initialize database
    with app.app_context():
        from app.extensions import db
        db.create_all()
    
    return app


def configure_logging(app):
    """Configure application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    app.logger.setLevel(logging.INFO)


def init_sentry(app):
    """
    Initialize Sentry SDK for error tracking.
    Only active if SENTRY_DSN is configured.
    """
    import os
    
    sentry_dsn = os.getenv('SENTRY_DSN')
    if not sentry_dsn:
        app.logger.info("Sentry DSN not configured - error tracking disabled")
        return
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FlaskIntegration(),
                CeleryIntegration(),
                SqlalchemyIntegration(),
            ],
            # Performance monitoring
            traces_sample_rate=0.1,  # 10% of transactions
            # Send user info
            send_default_pii=False,
            # Environment
            environment=os.getenv('FLASK_ENV', 'development'),
            # Release version
            release=os.getenv('APP_VERSION', '2.0.0'),
        )
        
        app.logger.info("✅ Sentry initialized for error tracking")
        
    except ImportError:
        app.logger.warning("sentry-sdk not installed - pip install sentry-sdk[flask]")
    except Exception as e:
        app.logger.error(f"Sentry initialization failed: {e}")


def register_blueprints(app):
    """Register all Flask blueprints"""
    # Import blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.exam import exam_bp
    from app.routes.api import api_bp
    
    # Register with URL prefixes
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(exam_bp, url_prefix='/exam')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register credits blueprint
    try:
        from app.routes.credits import credits_bp
        app.register_blueprint(credits_bp)
        app.logger.info("✅ Credits blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Credits blueprint not available: {e}")
    
    # Register 2FA blueprint
    try:
        from app.routes.two_factor import twofa_bp
        app.register_blueprint(twofa_bp)
        app.logger.info("✅ 2FA blueprint registered")
    except ImportError as e:
        app.logger.warning(f"2FA blueprint not available: {e}")
    
    # Register candidate blueprint
    try:
        from app.routes.candidate import candidate_bp
        app.register_blueprint(candidate_bp)
        app.logger.info("✅ Candidate blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Candidate blueprint not available: {e}")
    
    # Register analytics blueprint
    try:
        from app.routes.analytics import analytics_bp
        app.register_blueprint(analytics_bp)
        app.logger.info("✅ Analytics blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Analytics blueprint not available: {e}")
    
    # Register health check blueprint
    try:
        from app.routes.health import health_bp
        app.register_blueprint(health_bp)
        app.logger.info("✅ Health check blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Health check blueprint not available: {e}")
    
    # Initialize i18n (internationalization)
    try:
        from app.i18n import init_i18n
        init_i18n(app)
    except ImportError as e:
        app.logger.warning(f"i18n module not available: {e}")
    
    # Register international features if available
    try:
        from international_features import register_international_features
        register_international_features(app)
    except ImportError:
        app.logger.debug("International features module not available")


def register_error_handlers(app):
    """Register error handlers"""
    from flask import render_template, jsonify
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from app.extensions import db
        db.session.rollback()
        return render_template('500.html'), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Rate limit exceeded", "message": str(e.description)}), 429


def register_context_processors(app):
    """Register context processors for templates"""
    from flask import session
    
    @app.context_processor
    def inject_accessibility():
        return {
            'accessibility': session.get('accessibility', {
                'high_contrast': False,
                'large_text': False,
                'reduced_motion': False,
                'colorblind_mode': None,
                'dyslexia_friendly': False
            })
        }
    
    @app.context_processor
    def inject_user():
        rol = session.get('rol')
        is_superadmin = (rol == 'superadmin')
        is_customer = (rol == 'customer')
        
        return {
            'current_user': session.get('kullanici'),
            'current_role': rol,
            'current_company': session.get('sirket_id'),
            # Permission flags for menu visibility
            'is_superadmin': is_superadmin,
            'is_customer': is_customer,
            'can_manage_questions': is_superadmin,
            'can_manage_users': is_superadmin,
            'can_manage_settings': is_superadmin,
            'can_manage_templates': is_superadmin,
            'can_invite_candidates': is_superadmin or is_customer,
            'can_view_reports': is_superadmin or is_customer,
            'can_download_reports': is_superadmin or is_customer
        }

# -*- coding: utf-8 -*-
    try:
        from app.routes.candidate_auth import candidate_auth_bp
        app.register_blueprint(candidate_auth_bp)
        app.logger.info("✅ Candidate Auth blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Candidate Auth blueprint not available: {e}")
        
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
        
    # FIXED: Register question import blueprint
    try:
        from app.routes.question_import import question_import_bp
        app.register_blueprint(question_import_bp)
        app.logger.info("✅ Question Import blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Question Import blueprint not available: {e}")

        # Register certificate blueprint for /sertifika/* routes
    try:
        from app.routes.certificate import certificate_bp
        app.register_blueprint(certificate_bp)
        app.logger.info("✅ Certificate blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Certificate blueprint not available: {e}")
        
    # NEW: Register data management blueprint for /data/* routes
    try:
        from app.routes.data_management import data_bp
        app.register_blueprint(data_bp)
        app.logger.info("✅ Data Management blueprint registered")
    except ImportError as e:
        app.logger.warning(f"Data Management blueprint not available: {e}")

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

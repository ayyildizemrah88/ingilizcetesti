# -*- coding: utf-8 -*-
"""
Flask Extensions - Centralized extension initialization
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger

# Database
db = SQLAlchemy()
migrate = Migrate()

# Security
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

# Documentation
swagger = Swagger()

# ══════════════════════════════════════════════════════════════════
# REAL-TIME WEBSOCKET (imported from websocket module)
# ══════════════════════════════════════════════════════════════════
# Note: SocketIO instance is created in app/utils/websocket.py
# and initialized here for centralized management


def init_extensions(app):
    """Initialize all Flask extensions with the app"""
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    swagger.init_app(app)
    
    # ══════════════════════════════════════════════════════════════
    # WEBSOCKET INITIALIZATION
    # ══════════════════════════════════════════════════════════════
    try:
        from app.utils.websocket import init_socketio
        init_socketio(app)
        app.logger.info("✅ Flask-SocketIO initialized")
    except ImportError as e:
        app.logger.warning(f"WebSocket not available: {e}")
    except Exception as e:
        app.logger.error(f"WebSocket initialization failed: {e}")
    
    return app


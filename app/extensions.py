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


def init_extensions(app):
    """Initialize all Flask extensions with the app"""
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    swagger.init_app(app)
    
    return app

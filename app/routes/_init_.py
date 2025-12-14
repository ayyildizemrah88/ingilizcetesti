# -*- coding: utf-8 -*-
"""
Routes Package - Flask Blueprints
"""
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.exam import exam_bp
from app.routes.api import api_bp

__all__ = ['auth_bp', 'admin_bp', 'exam_bp', 'api_bp']

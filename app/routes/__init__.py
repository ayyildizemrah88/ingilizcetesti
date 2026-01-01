# -*- coding: utf-8 -*-
"""
Routes Package - Flask Blueprints
TÜM BLUEPRINT'LER DAHİL - TAM VERSİYON
GitHub: app/routes/__init__.py
"""
# ══════════════════════════════════════════════════════════════
# TEMEL BLUEPRINT'LER (Mevcut)
# ══════════════════════════════════════════════════════════════
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.exam import exam_bp
from app.routes.api import api_bp
from app.routes.ai_service import ai_bp
# ══════════════════════════════════════════════════════════════
# EK BLUEPRINT'LER (YENİ EKLENDİ)
# ══════════════════════════════════════════════════════════════
from app.routes.health import health_bp
from app.routes.analytics import analytics_bp
from app.routes.certificate import certificate_bp
from app.routes.credits import credits_bp
from app.routes.question_import import question_import_bp
from app.routes.data_management import data_bp
# ══════════════════════════════════════════════════════════════
# TÜM BLUEPRINT LİSTESİ
# ══════════════════════════════════════════════════════════════
__all__ = [
    # Temel
    'auth_bp',
    'admin_bp', 
    'exam_bp',
    'api_bp',
    'ai_bp',
    # Ek özellikler
    'health_bp',
    'analytics_bp',
    'certificate_bp',
    'credits_bp',
    'question_import_bp',
    'data_bp',
]

# -*- coding: utf-8 -*-
"""
Routes Package - Flask Blueprints
TÜM BLUEPRINT'LER DAHİL - TAM VERSİYON (GÜNCELLENME: customer_bp EKLENDİ)
GitHub: app/routes/__init__.py
"""
# ══════════════════════════════════════════════════════════════
# TEMEL BLUEPRINT'LER
# ══════════════════════════════════════════════════════════════
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.exam import exam_bp
from app.routes.api import api_bp
from app.routes.ai_service import ai_bp

# ══════════════════════════════════════════════════════════════
# ÖZELLİK BLUEPRINT'LERİ
# ══════════════════════════════════════════════════════════════
from app.routes.health import health_bp
from app.routes.analytics import analytics_bp
from app.routes.certificate import certificate_bp
from app.routes.credits import credits_bp
from app.routes.question_import import question_import_bp
from app.routes.data_management import data_bp

# ══════════════════════════════════════════════════════════════
# YENİ EKLENEN BLUEPRINT'LER
# ══════════════════════════════════════════════════════════════
from app.routes.two_factor import twofa_bp
from app.routes.candidate import candidate_bp
from app.routes.candidate_auth import candidate_auth_bp
from app.routes.email_verification import email_verification_bp
from app.routes.proctoring import proctoring_bp
from app.routes.customer import customer_bp  # YENİ: Müşteri dashboard

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
    
    # Özellik blueprint'leri
    'health_bp',
    'analytics_bp',
    'certificate_bp',
    'credits_bp',
    'question_import_bp',
    'data_bp',
    
    # Yeni eklenenler
    'twofa_bp',
    'candidate_bp',
    'candidate_auth_bp',
    'email_verification_bp',
    'proctoring_bp',
    'customer_bp',  # YENİ: Müşteri dashboard
]

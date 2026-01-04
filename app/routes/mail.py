# -*- coding: utf-8 -*-
"""
Main Routes - Homepage and public pages
YENİ DOSYA - Ana sayfa (/) route'u için
GitHub: app/routes/main.py
"""
from flask import Blueprint, render_template, session

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Ana sayfa - Skills Test Center"""
    return render_template('index.html')


@main_bp.route('/about')
def about():
    """Hakkımızda sayfası"""
    return render_template('about.html')


@main_bp.route('/contact')
def contact():
    """İletişim sayfası"""
    return render_template('contact.html')


@main_bp.route('/privacy')
def privacy():
    """Gizlilik politikası"""
    return render_template('privacy.html')


@main_bp.route('/terms')
def terms():
    """Kullanım şartları"""
    return render_template('terms.html')

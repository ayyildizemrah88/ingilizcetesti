# -*- coding: utf-8 -*-
"""
Main Routes - Homepage and public pages
GitHub: app/routes/main.py

FIX: Added /demo-olustur route that was missing
FIX: Added /iletisim route for Turkish URL compatibility
"""
from flask import Blueprint, render_template, session

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Ana sayfa - Skills Test Center"""
    return render_template('index.html')


@main_bp.route('/hakkimizda')
def hakkimizda():
    """Hakkımızda sayfası (Türkçe URL)"""
    return render_template('hakkimizda.html')


@main_bp.route('/about')
def about():
    """Hakkımızda sayfası (İngilizce URL)"""
    return render_template('hakkimizda.html')


@main_bp.route('/demo-sinav')
@main_bp.route('/demo')
def demo_sinav():
    """
    Demo sınav bilgi sayfası
    NOT: Gerçek demo sınav sadece admin panelinden başlatılabilir
    Bu sayfa sadece bilgilendirme amaçlıdır
    """
    return render_template('demo_sinav.html')


@main_bp.route('/demo-olustur')
def demo_olustur():
    """
    Demo sınav oluşturma sayfası
    Kullanıcıların demo sınav talebinde bulunabilecekleri sayfa
    """
    return render_template('demo_olustur.html')


@main_bp.route('/contact')
def contact():
    """İletişim sayfası (İngilizce URL)"""
    return render_template('iletisim.html')


@main_bp.route('/iletisim')
def iletisim():
    """İletişim sayfası (Türkçe URL)"""
    return render_template('iletisim.html')


@main_bp.route('/privacy')
def privacy():
    """Gizlilik politikası"""
    return render_template('privacy.html')


@main_bp.route('/terms')
def terms():
    """Kullanım şartları"""
    return render_template('terms.html')


@main_bp.route('/toggle-theme')
def toggle_theme():
    """Tema değiştir (Light/Dark mode)"""
    from flask import redirect, request
    
    # Mevcut temayı al ve tersini ayarla
    current_theme = session.get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    session['theme'] = new_theme
    
    # Geri dön (referrer varsa oraya, yoksa ana sayfaya)
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    return redirect('/')

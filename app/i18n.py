# -*- coding: utf-8 -*-
"""
Internationalization (i18n) Setup
Multi-language support using Flask-Babel
"""
import os
from flask import Flask, request, session, g
from flask_babel import Babel, gettext, ngettext, lazy_gettext

# Initialize Babel
babel = Babel()

# Supported languages
SUPPORTED_LANGUAGES = {
    'tr': {
        'name': 'Türkçe',
        'flag': '🇹🇷',
        'direction': 'ltr'
    },
    'en': {
        'name': 'English',
        'flag': '🇬🇧',
        'direction': 'ltr'
    },
    'de': {
        'name': 'Deutsch',
        'flag': '🇩🇪',
        'direction': 'ltr'
    },
    'es': {
        'name': 'Español',
        'flag': '🇪🇸',
        'direction': 'ltr'
    },
    'fr': {
        'name': 'Français',
        'flag': '🇫🇷',
        'direction': 'ltr'
    },
    'ar': {
        'name': 'العربية',
        'flag': '🇸🇦',
        'direction': 'rtl'
    }
}

DEFAULT_LANGUAGE = 'tr'


def get_locale():
    """
    Determine the best language for the user.
    
    Priority:
    1. User preference in session
    2. User preference in database (if logged in)
    3. Browser Accept-Language header
    4. Default language
    """
    # Check session
    if 'language' in session:
        return session['language']
    
    # Check user preference
    if hasattr(g, 'user') and g.user and hasattr(g.user, 'language'):
        return g.user.language
    
    # Check browser preference
    return request.accept_languages.best_match(SUPPORTED_LANGUAGES.keys(), default=DEFAULT_LANGUAGE)


def get_timezone():
    """Get user's timezone."""
    if hasattr(g, 'user') and g.user and hasattr(g.user, 'timezone'):
        return g.user.timezone
    return 'Europe/Istanbul'


def init_i18n(app: Flask):
    """
    Initialize internationalization for the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Configure Babel
    app.config.setdefault('BABEL_DEFAULT_LOCALE', DEFAULT_LANGUAGE)
    app.config.setdefault('BABEL_DEFAULT_TIMEZONE', 'Europe/Istanbul')
    app.config.setdefault('BABEL_TRANSLATION_DIRECTORIES', 'translations')
    
    # Initialize Babel with app
    babel.init_app(app, locale_selector=get_locale, timezone_selector=get_timezone)
    
    # Add context processor for templates
    @app.context_processor
    def inject_i18n():
        return {
            'supported_languages': SUPPORTED_LANGUAGES,
            'current_language': get_locale(),
            'current_language_info': SUPPORTED_LANGUAGES.get(get_locale(), SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE]),
            '_': gettext,
            '_n': ngettext
        }
    
    # Add route for language switching
    @app.route('/set-language/<lang>')
    def set_language(lang):
        if lang in SUPPORTED_LANGUAGES:
            session['language'] = lang
            
            # Update user preference if logged in
            if 'user_id' in session:
                try:
                    from app.models.user import User
                    from app.extensions import db
                    user = User.query.get(session['user_id'])
                    if user:
                        user.language = lang
                        db.session.commit()
                except:
                    pass
        
        # Redirect back to previous page
        from flask import redirect, request
        return redirect(request.referrer or '/')
    
    app.logger.info(f"✅ i18n initialized with {len(SUPPORTED_LANGUAGES)} languages")


# =====================================================
# TRANSLATION STRINGS (for babel extraction)
# Run: pybabel extract -F babel.cfg -o messages.pot .
# =====================================================

# Common UI strings
_ = lazy_gettext

# Navigation
NAV_DASHBOARD = _('Dashboard')
NAV_CANDIDATES = _('Adaylar')
NAV_EXAMS = _('Sınavlar')
NAV_REPORTS = _('Raporlar')
NAV_SETTINGS = _('Ayarlar')
NAV_LOGOUT = _('Çıkış')

# Auth
AUTH_LOGIN = _('Giriş Yap')
AUTH_LOGOUT = _('Çıkış')
AUTH_EMAIL = _('E-posta')
AUTH_PASSWORD = _('Şifre')
AUTH_FORGOT_PASSWORD = _('Şifremi Unuttum')
AUTH_REMEMBER_ME = _('Beni Hatırla')

# Buttons
BTN_SAVE = _('Kaydet')
BTN_CANCEL = _('İptal')
BTN_DELETE = _('Sil')
BTN_EDIT = _('Düzenle')
BTN_ADD = _('Ekle')
BTN_SEARCH = _('Ara')
BTN_FILTER = _('Filtrele')
BTN_EXPORT = _('Dışa Aktar')
BTN_IMPORT = _('İçe Aktar')
BTN_DOWNLOAD = _('İndir')
BTN_UPLOAD = _('Yükle')
BTN_SUBMIT = _('Gönder')
BTN_BACK = _('Geri')
BTN_NEXT = _('İleri')
BTN_FINISH = _('Bitir')

# Messages
MSG_SUCCESS = _('İşlem başarılı!')
MSG_ERROR = _('Bir hata oluştu.')
MSG_CONFIRM_DELETE = _('Bu öğeyi silmek istediğinizden emin misiniz?')
MSG_NO_DATA = _('Veri bulunamadı.')
MSG_LOADING = _('Yükleniyor...')

# CEFR Levels
CEFR_A1 = _('Başlangıç')
CEFR_A2 = _('Temel')
CEFR_B1 = _('Orta')
CEFR_B2 = _('Orta Üstü')
CEFR_C1 = _('İleri')
CEFR_C2 = _('Uzman')

# Exam Related
EXAM_STATUS_PENDING = _('Beklemede')
EXAM_STATUS_IN_PROGRESS = _('Sınavda')
EXAM_STATUS_COMPLETED = _('Tamamlandı')
EXAM_START = _('Sınava Başla')
EXAM_CONTINUE = _('Sınava Devam Et')
EXAM_FINISH = _('Sınavı Bitir')
EXAM_TIME_REMAINING = _('Kalan Süre')

# Skills
SKILL_GRAMMAR = _('Dilbilgisi')
SKILL_VOCABULARY = _('Kelime Bilgisi')
SKILL_READING = _('Okuma')
SKILL_LISTENING = _('Dinleme')
SKILL_WRITING = _('Yazma')
SKILL_SPEAKING = _('Konuşma')

# Time periods
TIME_TODAY = _('Bugün')
TIME_YESTERDAY = _('Dün')
TIME_THIS_WEEK = _('Bu Hafta')
TIME_THIS_MONTH = _('Bu Ay')
TIME_LAST_MONTH = _('Geçen Ay')
TIME_THIS_YEAR = _('Bu Yıl')

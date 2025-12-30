# -*- coding: utf-8 -*-
"""
Question Import Routes - Bulk import questions from Excel/CSV
"""
import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, current_app


from app.extensions import db


question_import_bp = Blueprint('question_import', __name__, url_prefix='/question-import')




def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated




def superadmin_required(f):
    """Only superadmin can access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu işlem sadece süper admin tarafından yapılabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated




@question_import_bp.route('/')
def index():
    """Redirect to upload page"""
    return redirect(url_for('question_import.upload'))


@question_import_bp.route('/import', methods=['GET', 'POST'])
def import_questions():
    """Redirect to upload page"""
    return redirect(url_for('question_import.upload'))


@question_import_bp.route('/download-template')
def download_template_redirect():
    """Redirect to template download"""
    return redirect(url_for('question_import.download_template'))


@question_import_bp.route('/upload', methods=['GET', 'POST'])

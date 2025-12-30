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


@question_import_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@superadmin_required
def upload():
    """Upload and import questions from file"""
    if request.method == 'GET':
        return render_template('question_import.html')
    
    # POST - handle file upload
    from app.models import Question
    
    file = request.files.get('file')
    category = request.form.get('category', 'grammar')
    default_level = request.form.get('level', 'B1')
    
    if not file or file.filename == '':
        flash("Dosya seçilmedi.", "danger")
        return redirect(url_for('question_import.upload'))
    
    filename = file.filename.lower()
    if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
        flash("Desteklenmeyen dosya formatı. .xlsx, .xls veya .csv kullanın.", "danger")
        return redirect(url_for('question_import.upload'))
    
    try:
        import pandas as pd
        
        # Read file
        if filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Validate columns
        required_cols = ['soru', 'a', 'b', 'c', 'd', 'dogru_cevap']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            flash(f"Eksik sütunlar: {', '.join(missing_cols)}", "danger")
            return redirect(url_for('question_import.upload'))
        
        # Import questions
        imported = 0
        for _, row in df.iterrows():
            try:
                question = Question(
                    soru_metni=str(row['soru']),
                    secenek_a=str(row['a']),
                    secenek_b=str(row['b']),
                    secenek_c=str(row['c']),
                    secenek_d=str(row['d']),
                    dogru_cevap=str(row['dogru_cevap']).lower().strip(),
                    kategori=category,
                    seviye=str(row.get('seviye', default_level)).upper(),
                    aktif=True
                )
                db.session.add(question)
                imported += 1
            except Exception as e:
                current_app.logger.error(f"Row import error: {e}")
                continue
        
        db.session.commit()
        flash(f"{imported} soru başarıyla içe aktarıldı.", "success")
        
    except ImportError:
        flash("pandas ve openpyxl kütüphaneleri gerekli: pip install pandas openpyxl", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"İçe aktarma hatası: {str(e)}", "danger")
    
    return redirect(url_for('question_import.upload'))


@question_import_bp.route('/template')
@login_required
def download_template():
    """Download Excel template for questions"""
    import io
    
    try:
        import pandas as pd
        
        # Create sample template
        data = {
            'soru': ['What is the capital of France?', 'She ___ to school every day.'],
            'a': ['London', 'go'],
            'b': ['Paris', 'goes'],
            'c': ['Berlin', 'going'],
            'd': ['Madrid', 'went'],
            'dogru_cevap': ['b', 'b'],
            'seviye': ['A2', 'A1']
        }
        
        df = pd.DataFrame(data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sorular')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='soru_sablonu.xlsx'
        )
        
    except ImportError:
        flash("pandas ve openpyxl gerekli: pip install pandas openpyxl", "danger")
        return redirect(url_for('question_import.upload'))

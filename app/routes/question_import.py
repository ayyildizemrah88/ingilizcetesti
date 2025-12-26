# -*- coding: utf-8 -*-
"""
Question Import Routes
Bulk import questions from Excel/CSV
FIXED: Route URLs updated for /question-import prefix
"""
import os
import io
import tempfile
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, session, send_file
from werkzeug.utils import secure_filename

from app.extensions import db

question_import_bp = Blueprint('question_import', __name__)


def superadmin_required(f):
    """Decorator to require superadmin role."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('rol') != 'superadmin':
            flash('Bu işlem için SuperAdmin yetkisi gereklidir.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@question_import_bp.route('/import', methods=['GET', 'POST'])
@superadmin_required
def import_questions():
    """
    Bulk import questions from Excel or CSV file.
    URL: /question-import/import
    """
    if request.method == 'POST':
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('Dosya seçilmedi', 'danger')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('Dosya seçilmedi', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Geçersiz dosya formatı. Sadece .xlsx, .xls ve .csv kabul edilir.', 'danger')
            return redirect(request.url)

        try:
            # Save file temporarily
            filename = secure_filename(file.filename)
            temp_dir = tempfile.mkdtemp()
            filepath = os.path.join(temp_dir, filename)
            file.save(filepath)

            # Import questions
            try:
                from app.utils.question_importer import QuestionImporter
                importer = QuestionImporter()
            except ImportError:
                # Fallback - simple import
                flash('Soru içe aktarma modülü bulunamadı.', 'danger')
                return redirect(request.url)

            ext = os.path.splitext(filename)[1].lower()

            if ext in ['.xlsx', '.xls']:
                questions, stats = importer.import_from_excel(filepath)
            else:
                questions, stats = importer.import_from_csv(filepath)

            # Save to database
            if questions:
                saved, save_errors = importer.save_questions_to_db(questions)
                stats['saved'] = saved
                if save_errors:
                    stats['errors'].extend(save_errors)
            else:
                stats['saved'] = 0

            # Clean up
            os.remove(filepath)
            os.rmdir(temp_dir)

            # Show results
            if stats['saved'] > 0:
                flash(f"✅ {stats['saved']} soru başarıyla eklendi!", 'success')

            if stats['skipped'] > 0:
                flash(f"⚠️ {stats['skipped']} soru atlandı (hatalı veri)", 'warning')

            if stats['errors']:
                for error in stats['errors'][:5]:  # Show first 5 errors
                    flash(f"❌ {error}", 'danger')
                if len(stats['errors']) > 5:
                    flash(f"... ve {len(stats['errors']) - 5} hata daha", 'danger')

            return redirect(url_for('question_import.import_questions'))

        except Exception as e:
            flash(f'İçe aktarma hatası: {str(e)}', 'danger')
            return redirect(request.url)

    # GET request - show form
    template_info = {
        'columns': ['kategori', 'soru_metni', 'secenek_a', 'secenek_b', 'secenek_c', 'secenek_d', 'dogru_cevap', 'zorluk', 'aciklama'],
        'required': ['kategori', 'soru_metni', 'secenek_a', 'secenek_b', 'secenek_c', 'secenek_d', 'dogru_cevap'],
        'optional': ['zorluk', 'aciklama']
    }

    return render_template('question_import.html', template_info=template_info)


@question_import_bp.route('/download-template')
@superadmin_required
def download_template():
    """
    Download Excel template for question import.
    URL: /question-import/download-template
    """
    try:
        import pandas as pd
        
        # Create sample data
        sample_data = {
            'kategori': ['grammar', 'vocabulary', 'reading'],
            'soru_metni': [
                'What is the correct form of the verb?',
                'Choose the synonym of "happy"',
                'Read the passage and answer'
            ],
            'secenek_a': ['goes', 'sad', 'Answer A'],
            'secenek_b': ['go', 'joyful', 'Answer B'],
            'secenek_c': ['going', 'angry', 'Answer C'],
            'secenek_d': ['gone', 'tired', 'Answer D'],
            'dogru_cevap': ['A', 'B', 'C'],
            'zorluk': ['A1', 'B1', 'B2'],
            'aciklama': ['Subject-verb agreement', 'Synonyms', 'Reading comprehension']
        }
        
        df = pd.DataFrame(sample_data)
        
        # Create Excel file in memory
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
        flash('Excel şablonu oluşturmak için pandas ve openpyxl gereklidir.', 'danger')
        return redirect(url_for('question_import.import_questions'))
    except Exception as e:
        flash(f'Şablon indirme hatası: {str(e)}', 'danger')
        return redirect(url_for('question_import.import_questions'))


@question_import_bp.route('/api/import', methods=['POST'])
@superadmin_required
def api_import_questions():
    """
    API endpoint for question import.
    URL: /question-import/api/import
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Dosya yüklenmedi'}), 400

    file = request.files['file']

    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Geçersiz dosya'}), 400

    try:
        # Save temporarily
        filename = secure_filename(file.filename)
        temp_dir = tempfile.mkdtemp()
        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)

        # Import
        try:
            from app.utils.question_importer import QuestionImporter
            importer = QuestionImporter()
            
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.xlsx', '.xls']:
                questions, stats = importer.import_from_excel(filepath)
            else:
                questions, stats = importer.import_from_csv(filepath)

            # Save to database
            if questions:
                saved, save_errors = importer.save_questions_to_db(questions)
                stats['saved'] = saved
                if save_errors:
                    stats['errors'].extend(save_errors)
            else:
                stats['saved'] = 0
                
        except ImportError:
            return jsonify({'error': 'Soru içe aktarma modülü bulunamadı'}), 500

        # Clean up
        os.remove(filepath)
        os.rmdir(temp_dir)

        return jsonify({
            'success': True,
            'saved': stats.get('saved', 0),
            'skipped': stats.get('skipped', 0),
            'errors': stats.get('errors', [])[:10]  # Limit errors
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

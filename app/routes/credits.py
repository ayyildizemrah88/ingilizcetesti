# -*- coding: utf-8 -*-
"""
Credits Management Routes - Handle credit operations for companies
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.extensions import db

credits_bp = Blueprint('credits', __name__, url_prefix='/credits')


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


@credits_bp.route('/manage')
@login_required
@superadmin_required
def manage():
    """Credits management page"""
    from app.models import Company
    
    sirketler = Company.query.filter_by(is_active=True).order_by(Company.isim).all()
    
    return render_template('credits_manage.html', sirketler=sirketler)


@credits_bp.route('/add', methods=['POST'])
@login_required
@superadmin_required
def add_credits():
    """Add credits to a company"""
    from app.models import Company, AuditLog
    
    sirket_id = request.form.get('sirket_id', type=int)
    miktar = request.form.get('miktar', type=int)
    aciklama = request.form.get('aciklama', '')
    
    if not sirket_id or not miktar:
        flash("Şirket ve miktar seçilmelidir.", "danger")
        return redirect(url_for('credits.manage'))
    
    if miktar <= 0:
        flash("Kredi miktarı pozitif olmalıdır.", "danger")
        return redirect(url_for('credits.manage'))
    
    sirket = Company.query.get(sirket_id)
    if not sirket:
        flash("Şirket bulunamadı.", "danger")
        return redirect(url_for('credits.manage'))
    
    try:
        # Add credits
        sirket.kredi = (sirket.kredi or 0) + miktar
        
        # Log the action
        try:
            log = AuditLog(
                kullanici_id=session.get('kullanici_id'),
                eylem='credit_add',
                detay=f"{sirket.isim} şirketine {miktar} kredi yüklendi. {aciklama}"
            )
            db.session.add(log)
        except:
            pass  # AuditLog might not exist
        
        db.session.commit()
        flash(f"{sirket.isim} şirketine {miktar} kredi başarıyla yüklendi.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Kredi yüklenirken hata oluştu: {str(e)}", "danger")
    
    return redirect(url_for('credits.manage'))


@credits_bp.route('/history')
@login_required
@superadmin_required
def history():
    """Credit transaction history"""
    from app.models import Company
    
    sirketler = Company.query.order_by(Company.isim).all()
    
    return render_template('credits_history.html', sirketler=sirketler)

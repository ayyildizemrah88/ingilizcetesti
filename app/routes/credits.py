# -*- coding: utf-8 -*-
"""
Credits Management Routes - Handle credit operations for companies
FIXED: Added /load route to fix 404 error
GitHub: app/routes/credits.py
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
            flash("Lutfen giris yapin.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
def superadmin_required(f):
    """Only superadmin can access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu islem sadece super admin tarafindan yapilabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated
@credits_bp.route('/')
def index():
    """Redirect to manage page"""
    return redirect(url_for('credits.manage'))
@credits_bp.route('/manage')
@login_required
@superadmin_required
def manage():
    """Credits management page"""
    from app.models import Company
    
    sirketler = []
    try:
        sirketler = Company.query.filter_by(is_active=True).order_by(Company.isim).all()
    except:
        pass
    
    return render_template('credits_manage.html', sirketler=sirketler)
@credits_bp.route('/load', methods=['GET', 'POST'])
@login_required
@superadmin_required
def load():
    """Load credits page - FIXED: Added this route to fix 404"""
    from app.models import Company
    
    if request.method == 'POST':
        sirket_id = request.form.get('sirket_id', type=int)
        miktar = request.form.get('miktar', type=int)
        
        if not sirket_id or not miktar or miktar <= 0:
            flash("Gecersiz giris.", "danger")
            return redirect(url_for('credits.load'))
        
        sirket = Company.query.get(sirket_id)
        if not sirket:
            flash("Sirket bulunamadi.", "danger")
            return redirect(url_for('credits.load'))
        
        try:
            old_kredi = sirket.kredi or 0
            sirket.kredi = old_kredi + miktar
            
            # Log the transaction
            try:
                from app.models.company import CreditTransaction
                transaction = CreditTransaction(
                    sirket_id=sirket_id,
                    islem_tipi='purchase',
                    miktar=miktar,
                    aciklama=f'{miktar} kredi manuel olarak yüklendi',
                    onceki_bakiye=old_kredi,
                    sonraki_bakiye=sirket.kredi,
                    kullanici_id=session.get('kullanici_id')
                )
                db.session.add(transaction)
            except:
                pass
            
            db.session.commit()
            flash(f"{sirket.isim} sirketine {miktar} kredi yuklendi. Yeni bakiye: {sirket.kredi}", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Hata: {str(e)}", "danger")
        
        return redirect(url_for('credits.load'))
    
    # GET request
    sirketler = []
    try:
        sirketler = Company.query.filter_by(is_active=True).order_by(Company.isim).all()
    except:
        pass
    
    return render_template('credits_load.html', sirketler=sirketler)
@credits_bp.route('/add', methods=['POST'])
@login_required
@superadmin_required
def add_credits():
    """Add credits to a company"""
    from app.models import Company
    
    sirket_id = request.form.get('sirket_id', type=int)
    miktar = request.form.get('miktar', type=int)
    
    if not sirket_id or not miktar or miktar <= 0:
        flash("Gecersiz giris.", "danger")
        return redirect(url_for('credits.manage'))
    
    sirket = Company.query.get(sirket_id)
    if not sirket:
        flash("Sirket bulunamadi.", "danger")
        return redirect(url_for('credits.manage'))
    
    try:
        sirket.kredi = (sirket.kredi or 0) + miktar
        db.session.commit()
        flash(f"{sirket.isim} sirketine {miktar} kredi yuklendi.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Hata: {str(e)}", "danger")
    
    return redirect(url_for('credits.manage'))
@credits_bp.route('/history')
@login_required
@superadmin_required
def history():
    """Credit transaction history"""
    from app.models import Company
    
    sirketler = []
    transactions = []
    
    try:
        sirketler = Company.query.order_by(Company.isim).all()
    except:
        pass
    
    # Get recent transactions
    try:
        from app.models.company import CreditTransaction
        transactions = CreditTransaction.query.order_by(
            CreditTransaction.created_at.desc()
        ).limit(100).all()
    except:
        pass
    
    return render_template('credits_history.html', sirketler=sirketler, transactions=transactions)

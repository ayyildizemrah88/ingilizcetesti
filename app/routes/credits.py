# -*- coding: utf-8 -*-
"""
Credits Routes - Credit purchase and management
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from app.extensions import db

credits_bp = Blueprint('credits', __name__, url_prefix='/credits')


def login_required(f):
    """Require login for credit routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@credits_bp.route('/')
@login_required
def index():
    """
    Credit balance and purchase options page.
    """
    from app.models.company import Company
    from app.utils.payment import CreditPackage
    
    # Get company credits
    company_id = session.get('sirket_id')
    company = Company.query.get(company_id) if company_id else None
    current_credits = company.kredi if company else 0
    
    # Get all packages
    packages = CreditPackage.get_all_packages()
    
    # Get recent transactions
    transactions = []
    if company:
        from app.models.admin import CreditTransaction
        transactions = CreditTransaction.query.filter_by(
            company_id=company_id
        ).order_by(CreditTransaction.created_at.desc()).limit(10).all()
    
    return render_template('credits/index.html',
                          current_credits=current_credits,
                          packages=packages,
                          transactions=transactions,
                          company=company)


@credits_bp.route('/purchase/<package_id>')
@login_required
def purchase(package_id):
    """
    Initiate credit purchase.
    """
    from app.models.company import Company
    from app.models.user import User
    from app.utils.payment import CreditPackage, get_payment_provider
    
    # Get package
    package = CreditPackage.get_package(package_id)
    if not package:
        flash('Geçersiz paket.', 'danger')
        return redirect(url_for('credits.index'))
    
    # Get user and company
    user = User.query.get(session['kullanici_id'])
    company = Company.query.get(session.get('sirket_id'))
    
    if not company:
        flash('Şirket bilgisi bulunamadı.', 'danger')
        return redirect(url_for('credits.index'))
    
    # Get payment provider based on region
    region = request.args.get('region', 'TR')
    provider = get_payment_provider(region)
    
    # Calculate price
    currency = 'TRY' if region == 'TR' else 'USD'
    price = CreditPackage.calculate_price(package_id, currency)
    
    # Create checkout
    callback_url = url_for('credits.payment_callback', _external=True)
    
    if region == 'TR':
        # Iyzico
        result = provider.create_checkout_form(
            amount=price,
            buyer_email=user.email,
            buyer_name=user.ad_soyad,
            buyer_id=str(user.id),
            callback_url=callback_url,
            currency=currency,
            credit_package=package_id
        )
        
        if result['success']:
            session['payment_token'] = result['token']
            session['payment_package'] = package_id
            session['payment_credits'] = package['credits']
            
            return render_template('credits/checkout_iyzico.html',
                                  checkout_form=result['checkout_form_content'],
                                  package=package,
                                  price=price,
                                  currency=currency)
        else:
            flash(f"Ödeme başlatılamadı: {result.get('error', 'Bilinmeyen hata')}", 'danger')
            return redirect(url_for('credits.index'))
    else:
        # Stripe
        success_url = url_for('credits.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = url_for('credits.index', _external=True)
        
        result = provider.create_checkout_session(
            amount=int(price * 100),  # cents
            currency=currency.lower(),
            customer_email=user.email,
            success_url=success_url,
            cancel_url=cancel_url,
            credit_amount=package['credits'],
            metadata={'company_id': str(company.id), 'package_id': package_id}
        )
        
        if result['success']:
            return redirect(result['checkout_url'])
        else:
            flash(f"Ödeme başlatılamadı: {result.get('error', 'Bilinmeyen hata')}", 'danger')
            return redirect(url_for('credits.index'))


@credits_bp.route('/callback', methods=['GET', 'POST'])
def payment_callback():
    """
    Handle Iyzico payment callback.
    """
    from app.models.company import Company
    from app.utils.payment import IyzicoPayment
    
    token = request.form.get('token') or session.get('payment_token')
    if not token:
        flash('Ödeme bilgisi bulunamadı.', 'danger')
        return redirect(url_for('credits.index'))
    
    # Verify payment
    provider = IyzicoPayment()
    result = provider.verify_payment(token)
    
    if result['success']:
        # Add credits
        company_id = session.get('sirket_id')
        credits_to_add = session.get('payment_credits', 0)
        
        if company_id and credits_to_add:
            company = Company.query.get(company_id)
            if company:
                company.kredi = (company.kredi or 0) + credits_to_add
                
                # Log transaction
                from app.models.admin import CreditTransaction
                transaction = CreditTransaction(
                    company_id=company_id,
                    amount=credits_to_add,
                    transaction_type='purchase',
                    payment_id=result.get('payment_id'),
                    description=f"Kredi satın alma - {session.get('payment_package', 'unknown')} paketi"
                )
                db.session.add(transaction)
                db.session.commit()
                
                flash(f'🎉 {credits_to_add} kredi başarıyla yüklendi!', 'success')
                
                # Clear session
                session.pop('payment_token', None)
                session.pop('payment_package', None)
                session.pop('payment_credits', None)
                
                return redirect(url_for('credits.success'))
    
    flash(f"Ödeme doğrulanamadı: {result.get('error', 'Bilinmeyen hata')}", 'danger')
    return redirect(url_for('credits.index'))


@credits_bp.route('/success')
@login_required
def payment_success():
    """
    Payment success page.
    """
    from app.models.company import Company
    
    company_id = session.get('sirket_id')
    company = Company.query.get(company_id) if company_id else None
    current_credits = company.kredi if company else 0
    
    return render_template('credits/success.html', current_credits=current_credits)


@credits_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.
    """
    from app.utils.payment import StripePayment
    from app.models.company import Company
    from app.models.admin import CreditTransaction
    
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    provider = StripePayment()
    is_valid, event = provider.verify_webhook(payload, sig_header)
    
    if not is_valid:
        return jsonify({'error': 'Invalid signature'}), 400
    
    if event['type'] == 'checkout.session.completed':
        session_data = event['data']['object']
        
        result = provider.handle_successful_payment(session_data['id'])
        
        if result['success']:
            company_id = result.get('company_id')
            credits_to_add = result.get('credit_amount', 0)
            
            if company_id and credits_to_add:
                company = Company.query.get(int(company_id))
                if company:
                    company.kredi = (company.kredi or 0) + credits_to_add
                    
                    transaction = CreditTransaction(
                        company_id=int(company_id),
                        amount=credits_to_add,
                        transaction_type='purchase',
                        payment_id=result.get('payment_intent'),
                        description=f"Stripe ödeme - {credits_to_add} kredi"
                    )
                    db.session.add(transaction)
                    db.session.commit()
    
    return jsonify({'status': 'ok'})

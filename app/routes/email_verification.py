# -*- coding: utf-8 -*-
"""
Email Verification Routes
Handles email verification for new users and email changes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.extensions import db
from datetime import datetime, timedelta
import jwt
import os

email_verification_bp = Blueprint('email_verification', __name__, url_prefix='/verify')


def generate_verification_token(user_id, email, expires_hours=24):
    """Generate a JWT token for email verification"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=expires_hours),
        'iat': datetime.utcnow(),
        'type': 'email_verification'
    }
    
    return jwt.encode(
        payload,
        os.getenv('SECRET_KEY', 'secret'),
        algorithm='HS256'
    )


def verify_token(token):
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(
            token,
            os.getenv('SECRET_KEY', 'secret'),
            algorithms=['HS256']
        )
        
        if payload.get('type') != 'email_verification':
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@email_verification_bp.route('/email/<token>')
def verify_email(token):
    """
    Verify email address
    ---
    tags:
      - Email Verification
    parameters:
      - name: token
        in: path
        type: string
        required: true
    responses:
      200:
        description: Email verified successfully
      400:
        description: Invalid or expired token
    """
    payload = verify_token(token)
    
    if not payload:
        flash("Doğrulama linki geçersiz veya süresi dolmuş.", "danger")
        return redirect(url_for('auth.login'))
    
    from app.models import User
    user = User.query.get(payload['user_id'])
    
    if not user:
        flash("Kullanıcı bulunamadı.", "danger")
        return redirect(url_for('auth.login'))
    
    # Check if email matches
    if user.email != payload['email']:
        flash("E-posta adresi eşleşmiyor.", "danger")
        return redirect(url_for('auth.login'))
    
    # Mark email as verified
    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    db.session.commit()
    
    flash("E-posta adresiniz doğrulandı! Artık giriş yapabilirsiniz.", "success")
    return redirect(url_for('auth.login'))


@email_verification_bp.route('/resend', methods=['POST'])
def resend_verification():
    """
    Resend verification email
    ---
    tags:
      - Email Verification
    """
    email = request.form.get('email', '').strip().lower()
    
    if not email:
        flash("E-posta adresi gereklidir.", "warning")
        return redirect(url_for('auth.login'))
    
    from app.models import User
    user = User.query.filter_by(email=email).first()
    
    if user and not user.email_verified:
        # Generate new token
        token = generate_verification_token(user.id, user.email)
        
        # Send verification email
        try:
            from app.tasks.email_tasks import send_verification_email
            send_verification_email.delay(user.id, token)
        except Exception as e:
            current_app.logger.error(f"Failed to send verification email: {e}")
    
    # Always show success message (security - don't reveal if email exists)
    flash("Doğrulama e-postası gönderildi. Lütfen gelen kutunuzu kontrol edin.", "success")
    return redirect(url_for('auth.login'))


def send_verification_email_now(user):
    """
    Helper function to send verification email immediately
    Called during registration
    """
    token = generate_verification_token(user.id, user.email)
    verification_url = url_for('email_verification.verify_email', token=token, _external=True)
    
    # Use the email template
    try:
        from app.utils.email_templates import get_email_verification_template
        html_content = get_email_verification_template(user.ad_soyad, verification_url)
    except ImportError:
        html_content = f"""
        <html>
        <body>
            <h2>E-posta Doğrulama</h2>
            <p>Merhaba {user.ad_soyad},</p>
            <p>Hesabınızı doğrulamak için aşağıdaki linke tıklayın:</p>
            <p><a href="{verification_url}">{verification_url}</a></p>
            <p>Bu link 24 saat geçerlidir.</p>
        </body>
        </html>
        """
    
    # Send email
    try:
        from app.tasks.email_tasks import send_email_task
        send_email_task.delay(
            to_email=user.email,
            subject="Skills Test Center - E-posta Doğrulama",
            html_content=html_content
        )
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {e}")
        return False

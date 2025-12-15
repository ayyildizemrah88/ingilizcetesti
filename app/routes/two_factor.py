# -*- coding: utf-8 -*-
"""
Two-Factor Authentication Routes
2FA setup, verification, and management
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from functools import wraps
from app.extensions import db

twofa_bp = Blueprint('twofa', __name__, url_prefix='/2fa')


def login_required(f):
    """Require login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@twofa_bp.route('/')
@login_required
def index():
    """
    2FA management page - show status and options.
    """
    from app.models.user import User
    
    user = User.query.get(session['kullanici_id'])
    
    return render_template('twofa/index.html',
                          user=user,
                          is_enabled=bool(user.totp_secret if hasattr(user, 'totp_secret') else False))


@twofa_bp.route('/setup')
@login_required
def setup():
    """
    Start 2FA setup - generate secret and show QR code.
    """
    from app.models.user import User
    from app.utils.security import TwoFactorAuth
    
    user = User.query.get(session['kullanici_id'])
    
    # Check if already enabled
    if hasattr(user, 'totp_secret') and user.totp_secret and user.totp_verified:
        flash('2FA zaten etkin.', 'info')
        return redirect(url_for('twofa.index'))
    
    # Generate new secret
    secret = TwoFactorAuth.generate_secret()
    
    # Store temporarily in session
    session['temp_totp_secret'] = secret
    
    # Generate backup codes
    backup_codes = TwoFactorAuth.generate_backup_codes(8)
    session['temp_backup_codes'] = backup_codes
    
    # Get provisioning URI for manual entry
    uri = TwoFactorAuth.get_provisioning_uri(secret, user.email)
    
    return render_template('twofa/setup.html',
                          secret=secret,
                          email=user.email,
                          backup_codes=backup_codes,
                          uri=uri)


@twofa_bp.route('/qr-code')
@login_required
def qr_code():
    """
    Generate QR code image for authenticator app.
    """
    from app.models.user import User
    from app.utils.security import TwoFactorAuth
    
    user = User.query.get(session['kullanici_id'])
    secret = session.get('temp_totp_secret')
    
    if not secret:
        return 'Secret not found', 404
    
    # Generate QR code
    qr_buffer = TwoFactorAuth.generate_qr_code(secret, user.email)
    
    return send_file(qr_buffer, mimetype='image/png')


@twofa_bp.route('/verify', methods=['POST'])
@login_required
def verify():
    """
    Verify the TOTP code and enable 2FA.
    """
    from app.models.user import User
    from app.utils.security import TwoFactorAuth
    
    code = request.form.get('code', '').strip()
    secret = session.get('temp_totp_secret')
    backup_codes = session.get('temp_backup_codes', [])
    
    if not secret:
        flash('Kurulum süresi doldu. Lütfen tekrar başlayın.', 'warning')
        return redirect(url_for('twofa.setup'))
    
    if not code or len(code) != 6:
        flash('6 haneli doğrulama kodu gereklidir.', 'warning')
        return redirect(url_for('twofa.setup'))
    
    # Verify the code
    if TwoFactorAuth.verify_code(secret, code):
        # Save to user
        user = User.query.get(session['kullanici_id'])
        user.totp_secret = secret
        user.totp_verified = True
        
        # Hash and save backup codes
        hashed_codes = [TwoFactorAuth.hash_backup_code(c) for c in backup_codes]
        user.backup_codes = ','.join(hashed_codes)
        
        db.session.commit()
        
        # Clear session
        session.pop('temp_totp_secret', None)
        session.pop('temp_backup_codes', None)
        
        # Mark as 2FA verified for this session
        session['2fa_verified'] = True
        
        flash('✅ İki faktörlü doğrulama başarıyla etkinleştirildi!', 'success')
        
        # Send confirmation email
        try:
            from app.utils.email_templates import EmailTemplates
            from app.tasks.email_tasks import send_email
            
            html = EmailTemplates.two_factor_enabled(user.ad_soyad)
            send_email.delay(user.email, '2FA Etkinleştirildi', html)
        except:
            pass
        
        return redirect(url_for('twofa.success', codes=','.join(backup_codes)))
    else:
        flash('Geçersiz doğrulama kodu. Lütfen tekrar deneyin.', 'danger')
        return redirect(url_for('twofa.setup'))


@twofa_bp.route('/success')
@login_required
def success():
    """
    2FA setup success page - show backup codes one more time.
    """
    codes = request.args.get('codes', '').split(',')
    return render_template('twofa/success.html', backup_codes=codes)


@twofa_bp.route('/disable', methods=['POST'])
@login_required
def disable():
    """
    Disable 2FA (requires current TOTP code).
    """
    from app.models.user import User
    from app.utils.security import TwoFactorAuth
    
    code = request.form.get('code', '').strip()
    
    user = User.query.get(session['kullanici_id'])
    
    if not hasattr(user, 'totp_secret') or not user.totp_secret:
        flash('2FA zaten devre dışı.', 'info')
        return redirect(url_for('twofa.index'))
    
    # Verify code before disabling
    if TwoFactorAuth.verify_code(user.totp_secret, code):
        user.totp_secret = None
        user.totp_verified = False
        user.backup_codes = None
        db.session.commit()
        
        session.pop('2fa_verified', None)
        
        flash('2FA başarıyla devre dışı bırakıldı.', 'success')
    else:
        flash('Geçersiz doğrulama kodu.', 'danger')
    
    return redirect(url_for('twofa.index'))


@twofa_bp.route('/challenge', methods=['GET', 'POST'])
def challenge():
    """
    2FA challenge page - shown after password login if 2FA is enabled.
    """
    if 'pending_2fa_user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        from app.models.user import User
        from app.utils.security import TwoFactorAuth
        
        code = request.form.get('code', '').strip()
        user_id = session['pending_2fa_user_id']
        
        user = User.query.get(user_id)
        
        if not user:
            session.pop('pending_2fa_user_id', None)
            return redirect(url_for('auth.login'))
        
        # Try TOTP code
        if TwoFactorAuth.verify_code(user.totp_secret, code):
            # Success - complete login
            session['kullanici_id'] = user.id
            session['kullanici'] = user.email
            session['rol'] = user.rol
            session['sirket_id'] = user.sirket_id
            session['2fa_verified'] = True
            
            session.pop('pending_2fa_user_id', None)
            
            flash('Giriş başarılı!', 'success')
            return redirect(url_for('admin.dashboard'))
        
        # Try backup code
        if user.backup_codes:
            hashed_input = TwoFactorAuth.hash_backup_code(code.upper())
            stored_codes = user.backup_codes.split(',')
            
            if hashed_input in stored_codes:
                # Remove used backup code
                stored_codes.remove(hashed_input)
                user.backup_codes = ','.join(stored_codes) if stored_codes else None
                db.session.commit()
                
                # Complete login
                session['kullanici_id'] = user.id
                session['kullanici'] = user.email
                session['rol'] = user.rol
                session['sirket_id'] = user.sirket_id
                session['2fa_verified'] = True
                
                session.pop('pending_2fa_user_id', None)
                
                flash('Giriş başarılı! (Yedek kod kullanıldı)', 'success')
                return redirect(url_for('admin.dashboard'))
        
        flash('Geçersiz doğrulama kodu.', 'danger')
    
    return render_template('twofa/challenge.html')

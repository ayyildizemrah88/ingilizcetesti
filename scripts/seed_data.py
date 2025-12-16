# -*- coding: utf-8 -*-
"""
Initial Seed Data - FIRST TIME SETUP ONLY
⚠️ WARNING: DO NOT COMMIT THIS FILE TO PUBLIC GITHUB!
⚠️ Change your password immediately after first login!
"""
from werkzeug.security import generate_password_hash
from datetime import datetime


def seed_superadmin():
    """
    Create initial superadmin user.
    Run this ONCE during first deployment.
    """
    from app.extensions import db
    from app.models import User
    
    # ⚠️ CHANGE THESE OR USE ENVIRONMENT VARIABLES IN PRODUCTION!
    SUPERADMIN_EMAIL = 'ayyildizemrah88@gmail.com'
    SUPERADMIN_PASSWORD = 'Gamberetto88!'
    SUPERADMIN_NAME = 'Emrah Ayyıldız'
    
    # Check if already exists
    existing = User.query.filter_by(email=SUPERADMIN_EMAIL).first()
    if existing:
        print(f"⚠️  Superadmin {SUPERADMIN_EMAIL} zaten mevcut!")
        return existing
    
    superadmin = User(
        email=SUPERADMIN_EMAIL,
        sifre=generate_password_hash(SUPERADMIN_PASSWORD),
        ad_soyad=SUPERADMIN_NAME,
        rol='superadmin',
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.session.add(superadmin)
    db.session.commit()
    
    print(f"""
✅ SUPERADMIN OLUŞTURULDU!
   Email: {SUPERADMIN_EMAIL}
   Şifre: {SUPERADMIN_PASSWORD}
   
⚠️ GÜVENLİK UYARISI: 
   Giriş yaptıktan sonra şifrenizi hemen değiştirin!
    """)
    
    return superadmin


def seed_all():
    """Run all seed functions."""
    print("🌱 Seed verileri oluşturuluyor...")
    seed_superadmin()
    print("✅ Tüm seed verileri oluşturuldu!")


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_all()

# -*- coding: utf-8 -*-
"""
One-time superadmin creation script
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash
from datetime import datetime

app = create_app()

with app.app_context():
    existing = User.query.filter_by(email='emrahayyildiz88@yahoo.com').first()
    if existing:
        print("Bu kullanici zaten mevcut!")
    else:
        superadmin = User(
            email='emrahayyildiz88@yahoo.com',
            sifre=generate_password_hash('Gamberetto88!'),
            ad_soyad='Emrah Ayyildiz',
            rol='superadmin',
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(superadmin)
        db.session.commit()
        print("Superadmin olusturuldu!")

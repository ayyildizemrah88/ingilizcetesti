#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Super Admin Oluşturma Script'i
Skills Test Center - init_admin.py

Kullanım:
    python init_admin.py

Environment Variables (opsiyonel):
    ADMIN_EMAIL - Admin email adresi (default: emrahayyildiz88@yahoo.com)
    ADMIN_PASSWORD - Admin şifresi (default: Gamberetto88!)
    ADMIN_NAME - Admin adı soyadı (default: Super Admin)
"""

import os
import sys

def create_superadmin():
    """Super admin kullanıcısı oluştur veya güncelle"""
    
    try:
        from app import create_app
        from app.models import User
        from app.extensions import db
        from werkzeug.security import generate_password_hash
    except ImportError as e:
        print(f"❌ Import hatası: {e}")
        print("Lütfen Flask uygulamasının doğru yapılandırıldığından emin olun.")
        sys.exit(1)
    
    # Environment variables veya default değerler
    email = os.getenv('ADMIN_EMAIL', 'emrahayyildiz88@yahoo.com')
    password = os.getenv('ADMIN_PASSWORD', 'Gamberetto88!')
    name = os.getenv('ADMIN_NAME', 'Super Admin')
    
    print("=" * 50)
    print("🔐 Skills Test Center - Super Admin Oluşturma")
    print("=" * 50)
    print(f"📧 Email: {email}")
    print(f"👤 Ad Soyad: {name}")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Mevcut kullanıcıyı kontrol et
            existing = User.query.filter_by(email=email).first()
            
            if existing:
                # Mevcut kullanıcıyı güncelle
                existing.rol = 'superadmin'
                existing.is_active = True
                
                # Şifre hash'leme (hangi alan varsa)
                if hasattr(existing, 'sifre_hash'):
                    existing.sifre_hash = generate_password_hash(password)
                elif hasattr(existing, 'password_hash'):
                    existing.password_hash = generate_password_hash(password)
                elif hasattr(existing, 'set_password'):
                    existing.set_password(password)
                else:
                    existing.sifre_hash = generate_password_hash(password)
                
                if hasattr(existing, 'ad_soyad'):
                    existing.ad_soyad = name
                
                db.session.commit()
                print(f"✅ Mevcut kullanıcı SUPERADMIN olarak güncellendi!")
                print(f"   ID: {existing.id}")
                print(f"   Email: {existing.email}")
                print(f"   Rol: {existing.rol}")
                
            else:
                # Yeni kullanıcı oluştur
                user = User(
                    email=email,
                    rol='superadmin',
                    is_active=True
                )
                
                # Ad soyad varsa ekle
                if hasattr(user, 'ad_soyad'):
                    user.ad_soyad = name
                
                # Şifre hash'leme
                if hasattr(user, 'set_password'):
                    user.set_password(password)
                elif hasattr(user, 'sifre_hash'):
                    user.sifre_hash = generate_password_hash(password)
                elif hasattr(user, 'password_hash'):
                    user.password_hash = generate_password_hash(password)
                else:
                    user.sifre_hash = generate_password_hash(password)
                
                db.session.add(user)
                db.session.commit()
                
                print(f"✅ Yeni SUPERADMIN oluşturuldu!")
                print(f"   ID: {user.id}")
                print(f"   Email: {user.email}")
                print(f"   Rol: {user.rol}")
            
            print("=" * 50)
            print("🎉 İşlem başarıyla tamamlandı!")
            print("=" * 50)
            print(f"\n📝 Giriş Bilgileri:")
            print(f"   URL: https://skillstestcenter.com/giris")
            print(f"   Email: {email}")
            print(f"   Şifre: {password}")
            print("")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Hata oluştu: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def list_users():
    """Tüm kullanıcıları listele"""
    
    try:
        from app import create_app
        from app.models import User
    except ImportError as e:
        print(f"❌ Import hatası: {e}")
        sys.exit(1)
    
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        print("=" * 70)
        print("📋 TÜM KULLANICILAR")
        print("=" * 70)
        print(f"{'ID':<5} {'Email':<35} {'Rol':<15} {'Aktif':<8}")
        print("-" * 70)
        
        for user in users:
            is_active = getattr(user, 'is_active', True)
            ad_soyad = getattr(user, 'ad_soyad', '-')
            print(f"{user.id:<5} {user.email:<35} {user.rol:<15} {'✅' if is_active else '❌':<8}")
        
        print("-" * 70)
        print(f"Toplam: {len(users)} kullanıcı")
        print("=" * 70)


def reset_password(email, new_password):
    """Kullanıcı şifresini sıfırla"""
    
    try:
        from app import create_app
        from app.models import User
        from app.extensions import db
        from werkzeug.security import generate_password_hash
    except ImportError as e:
        print(f"❌ Import hatası: {e}")
        sys.exit(1)
    
    app = create_app()
    
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ Kullanıcı bulunamadı: {email}")
            sys.exit(1)
        
        # Şifre güncelle
        if hasattr(user, 'set_password'):
            user.set_password(new_password)
        elif hasattr(user, 'sifre_hash'):
            user.sifre_hash = generate_password_hash(new_password)
        elif hasattr(user, 'password_hash'):
            user.password_hash = generate_password_hash(new_password)
        
        db.session.commit()
        
        print(f"✅ Şifre güncellendi: {email}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Skills Test Center - Admin Yönetimi')
    parser.add_argument('--list', '-l', action='store_true', help='Tüm kullanıcıları listele')
    parser.add_argument('--reset', '-r', nargs=2, metavar=('EMAIL', 'PASSWORD'), help='Şifre sıfırla')
    parser.add_argument('--email', '-e', type=str, help='Admin email adresi')
    parser.add_argument('--password', '-p', type=str, help='Admin şifresi')
    parser.add_argument('--name', '-n', type=str, help='Admin adı soyadı')
    
    args = parser.parse_args()
    
    if args.list:
        list_users()
    elif args.reset:
        reset_password(args.reset[0], args.reset[1])
    else:
        # Environment variables'ı override et
        if args.email:
            os.environ['ADMIN_EMAIL'] = args.email
        if args.password:
            os.environ['ADMIN_PASSWORD'] = args.password
        if args.name:
            os.environ['ADMIN_NAME'] = args.name
        
        create_superadmin()

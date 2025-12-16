# -*- coding: utf-8 -*-
"""
Demo Data Setup Script
Creates demo companies, users, and exam templates for testing.
"""
import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from datetime import datetime
import secrets
import string


def generate_api_key():
    """Generate a unique API key."""
    return 'sk_' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))


def generate_entry_code():
    """Generate unique exam entry code."""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))


# ══════════════════════════════════════════════════════════════════
# TGS DEMO DATA
# ══════════════════════════════════════════════════════════════════

TGS_SPEAKING_QUESTIONS = [
    {
        'soru_metni': "Please introduce yourself. Tell us about your name, where you're from, and what you do for a living.",
        'kategori': 'speaking',
        'zorluk': 'A2',
        'speaking_time': 180,  # 3 dakika
        'preparation_time': 30,
        'allow_early_submit': True  # Erken kaydet butonu
    },
    {
        'soru_metni': "Describe your typical workday. What time do you start, what tasks do you do, and when do you finish?",
        'kategori': 'speaking',
        'zorluk': 'B1',
        'speaking_time': 180,  # 3 dakika
        'preparation_time': 30,
        'allow_early_submit': True
    },
    {
        'soru_metni': "Talk about a challenging situation you faced at work and how you handled it. What did you learn from this experience?",
        'kategori': 'speaking',
        'zorluk': 'B2',
        'speaking_time': 180,  # 3 dakika
        'preparation_time': 30,
        'allow_early_submit': True
    },
    {
        'soru_metni': "If you could change one thing about your job, what would it be and why? How would this change improve your work life?",
        'kategori': 'speaking',
        'zorluk': 'B2',
        'speaking_time': 180,  # 3 dakika
        'preparation_time': 30,
        'allow_early_submit': True
    },
    {
        'soru_metni': "Where do you see yourself professionally in five years? What steps are you taking to achieve those goals?",
        'kategori': 'speaking',
        'zorluk': 'B1',
        'speaking_time': 180,  # 3 dakika
        'preparation_time': 30,
        'allow_early_submit': True
    }
]


@click.command('create-tgs-demo')
@with_appcontext
def create_tgs_demo():
    """
    Create TGS demo company with speaking exam.
    
    Usage: flask create-tgs-demo
    """
    from app.extensions import db
    from app.models import Company, User, Question
    
    click.echo("🚀 TGS Demo Hesabı Oluşturuluyor...")
    
    # Check if TGS already exists
    existing = Company.query.filter_by(isim='TGS').first()
    if existing:
        click.echo("⚠️  TGS şirketi zaten mevcut!")
        return
    
    try:
        # 1. Create Company
        tgs_company = Company(
            isim='TGS',
            email='demo@tgs.com',
            telefon='+90 212 555 0000',
            adres='İstanbul, Türkiye',
            api_key=generate_api_key(),
            kredi=10,  # 10 demo sınav kredisi
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(tgs_company)
        db.session.flush()  # Get ID
        
        click.echo(f"✅ Şirket oluşturuldu: TGS (ID: {tgs_company.id})")
        
        # 2. Create Admin User
        demo_password = 'TGS2024Demo!'
        tgs_admin = User(
            email='admin@tgs.com',
            sifre=generate_password_hash(demo_password),
            ad_soyad='TGS Yetkili',
            rol='customer',  # Müşteri rolü
            sirket_id=tgs_company.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(tgs_admin)
        
        click.echo(f"✅ Admin kullanıcı oluşturuldu: admin@tgs.com")
        
        # 3. Create Speaking Questions
        for i, q_data in enumerate(TGS_SPEAKING_QUESTIONS, 1):
            question = Question(
                soru_metni=q_data['soru_metni'],
                kategori=q_data['kategori'],
                zorluk=q_data['zorluk'],
                soru_tipi='speaking',
                sirket_id=tgs_company.id,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(question)
            click.echo(f"  📝 Soru {i}: {q_data['zorluk']} seviye speaking sorusu")
        
        db.session.commit()
        
        # Print summary
        click.echo("\n" + "="*50)
        click.echo("🎉 TGS DEMO HESABI BAŞARIYLA OLUŞTURULDU!")
        click.echo("="*50)
        click.echo(f"""
📋 GİRİŞ BİLGİLERİ:
   Email: admin@tgs.com
   Şifre: {demo_password}

🏢 ŞİRKET BİLGİLERİ:
   Şirket: TGS
   API Key: {tgs_company.api_key}
   Kredi: 100 sınav

📝 SINAV BİLGİLERİ:
   Tür: Speaking (Konuşma)
   Soru Sayısı: 5
   Seviyeler: A2, B1, B2
        """)
        
    except Exception as e:
        db.session.rollback()
        click.echo(f"❌ Hata: {e}")
        raise


@click.command('create-demo-candidate')
@click.option('--company', default='TGS', help='Company name')
@click.option('--name', default='Test Aday', help='Candidate name')
@with_appcontext
def create_demo_candidate(company, name):
    """
    Create a demo candidate for testing.
    
    Usage: flask create-demo-candidate --company TGS --name "Ahmet Yılmaz"
    """
    from app.extensions import db
    from app.models import Company, Candidate
    
    comp = Company.query.filter_by(isim=company).first()
    if not comp:
        click.echo(f"❌ {company} şirketi bulunamadı!")
        return
    
    entry_code = generate_entry_code()
    
    candidate = Candidate(
        ad_soyad=name,
        email=f'test@{company.lower()}.com',
        giris_kodu=entry_code,
        sinav_suresi=30,
        soru_limiti=5,
        sirket_id=comp.id,
        sinav_durumu='beklemede',
        created_at=datetime.utcnow()
    )
    
    db.session.add(candidate)
    db.session.commit()
    
    click.echo(f"""
🎓 DEMO ADAY OLUŞTURULDU!
   Ad: {name}
   Giriş Kodu: {entry_code}
   Şirket: {company}
    """)


def register_demo_commands(app):
    """Register CLI commands with Flask app."""
    app.cli.add_command(create_tgs_demo)
    app.cli.add_command(create_demo_candidate)


# ══════════════════════════════════════════════════════════════════
# STANDALONE SCRIPT (for direct execution)
# ══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("""
Bu script Flask CLI komutu olarak çalışır:
    flask create-tgs-demo
    flask create-demo-candidate --company TGS --name "Test Kullanıcı"
    """)

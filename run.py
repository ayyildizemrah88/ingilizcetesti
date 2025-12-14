# -*- coding: utf-8 -*-
"""
Skills Test Center - Application Entry Point

This is the new modular entry point for the application.
For development, run: python run.py
For production, use: gunicorn run:app
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create and configure the application
from app import create_app
from config import get_config

app = create_app(get_config())


# ══════════════════════════════════════════════════════════════
# CLI COMMANDS
# ══════════════════════════════════════════════════════════════

@app.cli.command('init-db')
def init_db():
    """Initialize the database with tables"""
    from app.extensions import db
    db.create_all()
    print("Database tables created.")


@app.cli.command('create-admin')
def create_admin():
    """Create initial admin user"""
    from app.models import User, Company
    from app.extensions import db
    
    email = input("Admin email: ")
    password = input("Admin password: ")
    company_name = input("Company name: ")
    
    # Create company
    company = Company(isim=company_name, email=email)
    db.session.add(company)
    db.session.flush()
    
    # Create admin user
    admin = User(
        email=email,
        rol='superadmin',
        sirket_id=company.id
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    
    print(f"Admin user '{email}' created successfully.")


@app.cli.command('seed-demo')
def seed_demo():
    """Seed database with demo data"""
    from app.models import Question, Company
    from app.extensions import db
    
    company = Company.query.first()
    if not company:
        print("Error: No company found. Run create-admin first.")
        return
    
    # Sample questions
    demo_questions = [
        {"soru_metni": "What ___ your name?", "secenek_a": "is", "secenek_b": "are", "secenek_c": "am", "secenek_d": "be", "dogru_cevap": "A", "kategori": "grammar", "zorluk": "A1"},
        {"soru_metni": "She ___ to school every day.", "secenek_a": "go", "secenek_b": "goes", "secenek_c": "going", "secenek_d": "gone", "dogru_cevap": "B", "kategori": "grammar", "zorluk": "A2"},
        {"soru_metni": "I have been working here ___ five years.", "secenek_a": "since", "secenek_b": "for", "secenek_c": "from", "secenek_d": "during", "dogru_cevap": "B", "kategori": "grammar", "zorluk": "B1"},
        {"soru_metni": "The synonym of 'happy' is:", "secenek_a": "sad", "secenek_b": "joyful", "secenek_c": "angry", "secenek_d": "tired", "dogru_cevap": "B", "kategori": "vocabulary", "zorluk": "A2"},
        {"soru_metni": "Choose the correct sentence:", "secenek_a": "He don't like coffee", "secenek_b": "He doesn't likes coffee", "secenek_c": "He doesn't like coffee", "secenek_d": "He not like coffee", "dogru_cevap": "C", "kategori": "grammar", "zorluk": "B1"},
    ]
    
    for q in demo_questions:
        question = Question(**q, sirket_id=company.id)
        db.session.add(question)
    
    db.session.commit()
    print(f"Added {len(demo_questions)} demo questions.")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           SKILLS TEST CENTER - International Testing         ║
║══════════════════════════════════════════════════════════════║
║  Running on: http://localhost:{port}                            ║
║  API Docs:   http://localhost:{port}/apidocs                    ║
║  Debug Mode: {debug}                                           ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)

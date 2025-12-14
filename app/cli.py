# -*- coding: utf-8 -*-
"""
CLI Commands for Skills Test Center
Usage: flask <command>
"""
import os
import click
from flask import current_app
from flask.cli import with_appcontext


def register_commands(app):
    """Register CLI commands with Flask app."""
    app.cli.add_command(create_admin)
    app.cli.add_command(create_superadmin)
    app.cli.add_command(init_db)
    app.cli.add_command(seed_questions)
    app.cli.add_command(run_backup)
    app.cli.add_command(show_config)
    app.cli.add_command(generate_secret_key)


@click.command('create-admin')
@click.option('--email', prompt='Email', help='Admin email address')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--name', prompt='Full Name', help='Admin full name')
@with_appcontext
def create_admin(email, password, name):
    """Create a new admin user (customer role)."""
    from app.extensions import db
    from app.models.user import User
    import bcrypt
    
    # Check if user exists
    existing = User.query.filter_by(email=email).first()
    if existing:
        click.echo(click.style(f'❌ User with email {email} already exists!', fg='red'))
        return
    
    # Create user
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user = User(
        email=email,
        sifre=hashed_password,
        ad_soyad=name,
        rol='customer',
        aktif=True
    )
    
    db.session.add(user)
    db.session.commit()
    
    click.echo(click.style(f'✅ Admin user created successfully!', fg='green'))
    click.echo(f'   Email: {email}')
    click.echo(f'   Role: customer')


@click.command('create-superadmin')
@click.option('--email', prompt='Email', help='Superadmin email address')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Superadmin password')
@click.option('--name', prompt='Full Name', help='Superadmin full name')
@with_appcontext
def create_superadmin(email, password, name):
    """Create a new superadmin user."""
    from app.extensions import db
    from app.models.user import User
    import bcrypt
    
    # Check if user exists
    existing = User.query.filter_by(email=email).first()
    if existing:
        click.echo(click.style(f'❌ User with email {email} already exists!', fg='red'))
        return
    
    # Create superadmin
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user = User(
        email=email,
        sifre=hashed_password,
        ad_soyad=name,
        rol='superadmin',
        aktif=True
    )
    
    db.session.add(user)
    db.session.commit()
    
    click.echo(click.style(f'✅ Superadmin created successfully!', fg='green'))
    click.echo(f'   Email: {email}')
    click.echo(f'   Role: superadmin')


@click.command('init-db')
@click.option('--drop', is_flag=True, help='Drop existing tables first')
@with_appcontext
def init_db(drop):
    """Initialize the database."""
    from app.extensions import db
    
    if drop:
        if click.confirm('⚠️  This will DELETE all data. Are you sure?'):
            db.drop_all()
            click.echo(click.style('Tables dropped.', fg='yellow'))
        else:
            click.echo('Cancelled.')
            return
    
    db.create_all()
    click.echo(click.style('✅ Database initialized!', fg='green'))


@click.command('seed-questions')
@click.option('--count', default=50, help='Number of sample questions to create')
@with_appcontext
def seed_questions(count):
    """Seed the database with sample questions."""
    from app.extensions import db
    from app.models.question import Question
    
    categories = ['grammar', 'vocabulary', 'reading', 'listening']
    levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    
    created = 0
    for i in range(count):
        q = Question(
            soru_metni=f"Sample question {i+1}: What is the correct answer?",
            kategori=categories[i % len(categories)],
            zorluk=levels[i % len(levels)],
            dogru_cevap='A',
            secenek_a='Option A (correct)',
            secenek_b='Option B',
            secenek_c='Option C',
            secenek_d='Option D',
            aktif=True
        )
        db.session.add(q)
        created += 1
    
    db.session.commit()
    click.echo(click.style(f'✅ Created {created} sample questions!', fg='green'))


@click.command('run-backup')
@with_appcontext
def run_backup():
    """Manually trigger a database backup."""
    from app.tasks.backup_tasks import backup_database
    
    click.echo('Starting backup...')
    result = backup_database.delay()
    click.echo(f'Backup task queued with ID: {result.id}')
    click.echo('Check Celery worker for progress.')


@click.command('show-config')
@with_appcontext
def show_config():
    """Show current configuration (safe values only)."""
    from flask import current_app
    
    click.echo('\n' + '='*50)
    click.echo('CURRENT CONFIGURATION')
    click.echo('='*50)
    
    safe_keys = [
        'DEBUG', 'TESTING', 'ENV', 
        'SESSION_TYPE', 'PERMANENT_SESSION_LIFETIME',
        'SQLALCHEMY_TRACK_MODIFICATIONS',
        'RATELIMIT_DEFAULT',
        'MAX_CONTENT_LENGTH'
    ]
    
    for key in safe_keys:
        value = current_app.config.get(key, 'Not set')
        click.echo(f'{key}: {value}')
    
    # Show status of sensitive configs
    click.echo('\n--- Sensitive Configs (status only) ---')
    
    secret_key = os.getenv('SECRET_KEY', '')
    click.echo(f"SECRET_KEY: {'✅ Set' if len(secret_key) >= 32 else '⚠️ Weak or not set'}")
    
    db_url = os.getenv('DATABASE_URL', '')
    click.echo(f"DATABASE_URL: {'✅ Set' if db_url else '❌ Not set'}")
    
    gemini_key = os.getenv('GEMINI_API_KEY', '')
    click.echo(f"GEMINI_API_KEY: {'✅ Set' if gemini_key else '⚠️ Not set'}")
    
    sendgrid_key = os.getenv('SENDGRID_API_KEY', '')
    click.echo(f"SENDGRID_API_KEY: {'✅ Set' if sendgrid_key else '⚠️ Not set'}")
    
    sentry_dsn = os.getenv('SENTRY_DSN', '')
    click.echo(f"SENTRY_DSN: {'✅ Set' if sentry_dsn else '⚠️ Not set'}")
    
    click.echo('='*50 + '\n')


@click.command('generate-secret-key')
def generate_secret_key():
    """Generate a secure random SECRET_KEY."""
    import secrets
    
    key = secrets.token_hex(32)  # 64 characters
    
    click.echo('\n' + '='*50)
    click.echo('GENERATED SECRET KEY')
    click.echo('='*50)
    click.echo(f'\n{key}\n')
    click.echo('Add this to your .env file:')
    click.echo(click.style(f'SECRET_KEY={key}', fg='green'))
    click.echo('='*50 + '\n')

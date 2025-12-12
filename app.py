# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════
SKILLS TEST CENTER - V21 PRODUCTION READY
═══════════════════════════════════════════════════════════════
✅ PostgreSQL + SQLite Support | ✅ Full Features | ✅ Docker Ready
✅ Multi-tenant | ✅ Role-Based Access | ✅ GDPR Compliant
"""

import os, random, string, datetime, time, sys, io, threading, re, json, logging, hashlib, uuid
from datetime import timedelta
from contextlib import contextmanager
from functools import wraps
from collections import Counter

import bcrypt, requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from flask import (Flask, render_template, request, redirect, url_for, session, 
                   jsonify, flash, get_flashed_messages, send_file)
from markupsafe import Markup
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf
from dotenv import load_dotenv
import pandas as pd
import jwt

# Optional imports
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except:
    SQLITE_AVAILABLE = False

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB = os.path.join(BASE_DIR, 'skillstest.db')

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('skillstest')

# Flask App
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'V21-PRODUCTION-KEY-CHANGE-ME')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# ProxyFix for nginx
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Security
csrf = CSRFProtect(app)
limiter = Limiter(
    key_func=get_remote_address, 
    app=app, 
    default_limits=["50000 per day", "5000 per hour"], 
    storage_uri="memory://"
)

# JWT Config
JWT_SECRET = os.getenv('JWT_SECRET', app.secret_key)
JWT_ALG = "HS256"

# Folders
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
LOGO_FOLDER = os.path.join(BASE_DIR, 'static', 'logos')
for d in [UPLOAD_FOLDER, LOGO_FOLDER, os.path.join(BASE_DIR, 'static', 'audio'),
          os.path.join(BASE_DIR, 'static', 'cvs'), os.path.join(BASE_DIR, 'static', 'screenshots'),
          os.path.join(BASE_DIR, 'static', 'ids'), os.path.join(BASE_DIR, 'static', 'videos')]:
    os.makedirs(d, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

# ══════════════════════════════════════════════════════════════
# DATABASE LAYER
# ══════════════════════════════════════════════════════════════
def get_db_connection():
    """Get database connection with retry logic"""
    db_url = os.getenv('DATABASE_URL', '')
    
    if db_url and POSTGRES_AVAILABLE:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(db_url)
                return conn, True  # conn, is_postgres
            except psycopg2.OperationalError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"DB connection attempt {attempt+1}/{max_retries} failed, retrying...")
                    time.sleep(2)
                else:
                    logger.error(f"PostgreSQL connection failed: {e}")
                    raise
    
    # Fallback to SQLite
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn, False

def execute_query(query, params=None, fetch=False, fetchone=False):
    """Execute query with automatic DB detection"""
    conn, is_postgres = get_db_connection()
    try:
        if is_postgres:
            query = query.replace('?', '%s')
            query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            cur = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cur = conn.cursor()
        
        cur.execute(query, params or ())
        
        if fetchone:
            result = cur.fetchone()
        elif fetch:
            result = cur.fetchall()
        else:
            result = cur.lastrowid if not is_postgres else None
            conn.commit()
            
        return result
    except Exception as e:
        conn.rollback()
        logger.error(f"Query error: {e}")
        raise
    finally:
        conn.close()

@contextmanager
def get_db_cursor():
    """Context manager for database operations"""
    conn, is_postgres = get_db_connection()
    try:
        if is_postgres:
            cur = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cur = conn.cursor()
        yield cur, is_postgres
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"DB Error: {e}")
        raise
    finally:
        conn.close()

# ══════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ══════════════════════════════════════════════════════════════
def init_db():
    """Initialize all database tables"""
    conn, is_postgres = get_db_connection()
    c = conn.cursor()
    
    # Adapt SQL for PostgreSQL vs SQLite
    auto_inc = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    tables = [
        f'''CREATE TABLE IF NOT EXISTS sirketler (
            id {auto_inc}, isim TEXT, kadi TEXT UNIQUE, kredi INTEGER DEFAULT 100, 
            is_active INTEGER DEFAULT 1, logo_url TEXT, theme_color TEXT DEFAULT '#0d6efd',
            mail_template TEXT, hris_url TEXT, hris_api_key TEXT, is_demo INTEGER DEFAULT 0
        )''',
        f'''CREATE TABLE IF NOT EXISTS yoneticiler (
            id {auto_inc}, kadi TEXT UNIQUE, sifre TEXT, rol TEXT, sirket_id INTEGER, ad_soyad TEXT
        )''',
        f'''CREATE TABLE IF NOT EXISTS adaylar (
            id {auto_inc}, ad_soyad TEXT, tc_kimlik TEXT, cep_no TEXT, email TEXT, 
            giris_kodu TEXT UNIQUE, sinav_suresi INTEGER DEFAULT 30, puan REAL DEFAULT 0, 
            durum TEXT DEFAULT 'Bekliyor', trust_score INTEGER DEFAULT 100,
            focus_lost_count INTEGER DEFAULT 0, anomaly_count INTEGER DEFAULT 0, admin_notes TEXT,
            writing_answers TEXT, speaking_transcripts TEXT, sirket_id INTEGER, 
            bitis_tarihi TIMESTAMP, cv_path TEXT, current_state TEXT, kvkk_consent INTEGER DEFAULT 0,
            certificate_hash TEXT, sinav_son_tarih TIMESTAMP, current_difficulty TEXT DEFAULT 'B1',
            p_grammar REAL DEFAULT 0, p_vocab REAL DEFAULT 0, p_reading REAL DEFAULT 0, 
            p_writing REAL DEFAULT 0, p_speaking REAL DEFAULT 0, p_listening REAL DEFAULT 0,
            soru_limiti INTEGER DEFAULT 10, seviye_sonuc TEXT, band_score REAL,
            ielts_reading REAL, ielts_writing REAL, ielts_speaking REAL, ielts_listening REAL,
            is_deleted INTEGER DEFAULT 0, session_lang TEXT DEFAULT 'tr'
        )''',
        f'''CREATE TABLE IF NOT EXISTS sorular (
            id {auto_inc}, soru_metni TEXT, secenek_a TEXT, secenek_b TEXT, secenek_c TEXT, 
            secenek_d TEXT, dogru_cevap TEXT, kategori TEXT, zorluk TEXT DEFAULT 'B1',
            soru_tipi TEXT DEFAULT 'SECMELI', referans_cevap TEXT, sirket_id INTEGER DEFAULT 0,
            passage_id INTEGER, onay_durumu TEXT DEFAULT 'Onaylandi'
        )''',
        f'''CREATE TABLE IF NOT EXISTS cevaplar (
            id {auto_inc}, aday_id INTEGER, soru_id INTEGER, verilen_cevap TEXT, 
            dogru_cevap_id INTEGER, dogru_mu INTEGER
        )''',
        f'''CREATE TABLE IF NOT EXISTS sinav_sablonlari (
            id {auto_inc}, isim TEXT, sinav_suresi INTEGER, soru_limiti INTEGER, 
            baslangic_seviyesi TEXT, sirket_id INTEGER
        )''',
        f'''CREATE TABLE IF NOT EXISTS reading_passages (
            id {auto_inc}, title TEXT, passage_text TEXT, topic TEXT, difficulty TEXT, 
            sirket_id INTEGER, created_by INTEGER
        )''',
        f'''CREATE TABLE IF NOT EXISTS admin_logs (
            id {auto_inc}, user_id INTEGER, username TEXT, action TEXT, target_id INTEGER, 
            details TEXT, ip_address TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        f'''CREATE TABLE IF NOT EXISTS otp_codes (
            id {auto_inc}, aday_id INTEGER, email TEXT, otp_code TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, is_used INTEGER DEFAULT 0
        )''',
        f'''CREATE TABLE IF NOT EXISTS mail_logs (
            id {auto_inc}, recipient TEXT, subject TEXT, status TEXT, 
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, error_msg TEXT, sirket_id INTEGER
        )''',
        f'''CREATE TABLE IF NOT EXISTS webhook_logs (
            id {auto_inc}, aday_id INTEGER, url TEXT, payload TEXT, status_code INTEGER, 
            response_text TEXT, error_message TEXT, is_success INTEGER, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        f'''CREATE TABLE IF NOT EXISTS writing_answers (
            id {auto_inc}, aday_id INTEGER, soru_id INTEGER, answer TEXT, score_json TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''',
        f'''CREATE TABLE IF NOT EXISTS speaking_answers (
            id {auto_inc}, aday_id INTEGER, soru_id INTEGER, transcript TEXT, score_json TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''
    ]
    
    for table_sql in tables:
        try:
            if is_postgres:
                table_sql = table_sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            c.execute(table_sql)
        except Exception as e:
            logger.warning(f"Table creation warning: {e}")
    
    conn.commit()
    
    # Create demo data if empty
    c.execute("SELECT count(*) FROM yoneticiler")
    count = c.fetchone()[0] if not is_postgres else c.fetchone()['count']
    
    if count == 0:
        logger.info("Creating demo users...")
        pw_hash = bcrypt.hashpw('Cengelkoy88!'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Demo company
        if is_postgres:
            c.execute("INSERT INTO sirketler (isim, kadi, kredi) VALUES (%s, %s, %s) RETURNING id",
                     ('Demo Sirket', 'demo', 1000))
            sid = c.fetchone()['id']
        else:
            c.execute("INSERT INTO sirketler (isim, kadi, kredi) VALUES (?, ?, ?)",
                     ('Demo Sirket', 'demo', 1000))
            sid = c.lastrowid
        
        # Super Admin
        if is_postgres:
            c.execute("INSERT INTO yoneticiler (kadi, sifre, rol, ad_soyad, sirket_id) VALUES (%s,%s,%s,%s,%s)",
                     ('kangal58', pw_hash, 'super_admin', 'Super Admin', 0))
            c.execute("INSERT INTO yoneticiler (kadi, sifre, rol, ad_soyad, sirket_id) VALUES (%s,%s,%s,%s,%s)",
                     ('musteri@test.com', pw_hash, 'sirket_admin', 'Müşteri Yönetici', sid))
            c.execute("INSERT INTO yoneticiler (kadi, sifre, rol, ad_soyad, sirket_id) VALUES (%s,%s,%s,%s,%s)",
                     ('recruiter@test.com', pw_hash, 'recruiter', 'IK Uzmani', sid))
        else:
            c.execute("INSERT INTO yoneticiler (kadi, sifre, rol, ad_soyad, sirket_id) VALUES (?,?,?,?,?)",
                     ('kangal58', pw_hash, 'super_admin', 'Super Admin', 0))
            c.execute("INSERT INTO yoneticiler (kadi, sifre, rol, ad_soyad, sirket_id) VALUES (?,?,?,?,?)",
                     ('musteri@test.com', pw_hash, 'sirket_admin', 'Müşteri Yönetici', sid))
            c.execute("INSERT INTO yoneticiler (kadi, sifre, rol, ad_soyad, sirket_id) VALUES (?,?,?,?,?)",
                     ('recruiter@test.com', pw_hash, 'recruiter', 'IK Uzmani', sid))
        
        # Demo exam template
        if is_postgres:
            c.execute("INSERT INTO sinav_sablonlari (isim, sinav_suresi, soru_limiti, baslangic_seviyesi, sirket_id) VALUES (%s,%s,%s,%s,%s)",
                     ('Varsayilan B1', 30, 10, 'B1', sid))
        else:
            c.execute("INSERT INTO sinav_sablonlari (isim, sinav_suresi, soru_limiti, baslangic_seviyesi, sirket_id) VALUES (?,?,?,?,?)",
                     ('Varsayilan B1', 30, 10, 'B1', sid))
        
        # Demo questions
        demo_questions = [
            ("I ___ happy.", "is", "am", "are", "be", "B", "Grammar", "A1"),
            ("She ___ to school every day.", "go", "goes", "going", "gone", "B", "Grammar", "A1"),
            ("They ___ playing football.", "is", "are", "am", "be", "B", "Grammar", "A2"),
            ("What ___ you doing?", "is", "are", "am", "do", "B", "Grammar", "B1"),
            ("If I ___ rich, I would travel.", "am", "was", "were", "be", "C", "Grammar", "B2"),
        ]
        for q in demo_questions:
            if is_postgres:
                c.execute("""INSERT INTO sorular (soru_metni, secenek_a, secenek_b, secenek_c, secenek_d, 
                            dogru_cevap, kategori, zorluk) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", q)
            else:
                c.execute("""INSERT INTO sorular (soru_metni, secenek_a, secenek_b, secenek_c, secenek_d, 
                            dogru_cevap, kategori, zorluk) VALUES (?,?,?,?,?,?,?,?)""", q)
        
        # Demo candidate
        if is_postgres:
            c.execute("INSERT INTO adaylar (ad_soyad, email, giris_kodu, sirket_id) VALUES (%s,%s,%s,%s)",
                     ('Demo Aday', 'aday@test.com', 'DEMO123', sid))
        else:
            c.execute("INSERT INTO adaylar (ad_soyad, email, giris_kodu, sirket_id) VALUES (?,?,?,?)",
                     ('Demo Aday', 'aday@test.com', 'DEMO123', sid))
        
        conn.commit()
        logger.info("Demo data created successfully!")
    
    conn.close()
    logger.info("Database initialization complete.")

# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════
def check_role(roles):
    """Role-based access control decorator"""
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Lütfen giriş yapın.", "warning")
                return redirect(url_for('login'))
            if session.get('rol') == 'super_admin':
                return f(*args, **kwargs)
            if session.get('rol') not in roles:
                flash("Bu alana erişim yetkiniz yok.", "danger")
                return redirect(url_for('admin_dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def log_admin_action(user_id, username, action, target_id=None, details=""):
    """Log admin actions for audit trail"""
    try:
        conn, is_pg = get_db_connection()
        c = conn.cursor()
        q = "INSERT INTO admin_logs (user_id, username, action, target_id, details, ip_address) VALUES (?,?,?,?,?,?)"
        if is_pg:
            q = q.replace('?', '%s')
        c.execute(q, (user_id, username, action, target_id, details, request.remote_addr))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Admin log error: {e}")

def generate_code(length=8):
    """Generate random alphanumeric code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_cert_hash(aday_id, puan):
    """Generate certificate verification hash"""
    return hashlib.sha256(f"{aday_id}{puan}{uuid.uuid4()}{int(time.time())}".encode()).hexdigest()[:24]

def send_email(to, subj, body, sid=None):
    """Send email with multiple SMTP fallback"""
    mail_ids = os.getenv('MAIL_CONFIGS', '1').split(',')
    
    def _send():
        sent = False
        error_msg = "No SMTP configured"
        
        for i in mail_ids:
            if sent:
                break
            server = os.getenv(f'MAIL_{i}_SERVER')
            port = os.getenv(f'MAIL_{i}_PORT', '587')
            user = os.getenv(f'MAIL_{i}_USER')
            pw = os.getenv(f'MAIL_{i}_PASS')
            
            if not server or not user:
                continue
                
            try:
                msg = MIMEMultipart()
                msg['From'] = user
                msg['To'] = to
                msg['Subject'] = subj
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
                
                s = smtplib.SMTP(server, int(port), timeout=10)
                s.starttls()
                s.login(user, pw)
                s.send_message(msg)
                s.quit()
                sent = True
                error_msg = ''
            except Exception as e:
                error_msg = str(e)
        
        # Log email attempt
        try:
            conn, is_pg = get_db_connection()
            c = conn.cursor()
            q = "INSERT INTO mail_logs (recipient, subject, status, error_msg, sirket_id) VALUES (?,?,?,?,?)"
            if is_pg:
                q = q.replace('?', '%s')
            c.execute(q, (to, subj, 'SENT' if sent else 'FAILED', error_msg[:500], sid or 0))
            conn.commit()
            conn.close()
        except:
            pass
    
    threading.Thread(target=_send).start()

def is_exam_active(aday_id):
    """Check if exam is still active for candidate"""
    conn, is_pg = get_db_connection()
    c = conn.cursor()
    q = "SELECT sinav_son_tarih, durum FROM adaylar WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
        c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(q, (aday_id,))
    aday = c.fetchone()
    conn.close()
    
    if not aday:
        return False
    
    durum = aday['durum'] if is_pg else aday[1]
    sinav_son = aday['sinav_son_tarih'] if is_pg else aday[0]
    
    if durum != 'Devam' or not sinav_son:
        return False
    
    try:
        if isinstance(sinav_son, str):
            bitis = datetime.datetime.fromisoformat(sinav_son)
        else:
            bitis = sinav_son
        return datetime.datetime.now() < bitis
    except:
        return False

def get_next_question(aday_id, difficulty='B1'):
    """Get next unanswered question for adaptive exam"""
    conn, is_pg = get_db_connection()
    c = conn.cursor()
    
    # Get answered question IDs
    q = "SELECT soru_id FROM cevaplar WHERE aday_id=?"
    if is_pg:
        q = q.replace('?', '%s')
        c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute(q, (aday_id,))
    answered = [r['soru_id'] if is_pg else r[0] for r in c.fetchall()]
    
    # Get next question
    if answered:
        placeholder = ','.join(['?' if not is_pg else '%s'] * len(answered))
        q = f"SELECT * FROM sorular WHERE zorluk=? AND id NOT IN ({placeholder}) AND onay_durumu='Onaylandi' ORDER BY RANDOM() LIMIT 1"
        params = [difficulty] + answered
    else:
        q = "SELECT * FROM sorular WHERE zorluk=? AND onay_durumu='Onaylandi' ORDER BY RANDOM() LIMIT 1"
        params = [difficulty]
    
    if is_pg:
        q = q.replace('?', '%s').replace('RANDOM()', 'RANDOM()')
    
    c.execute(q, tuple(params))
    question = c.fetchone()
    conn.close()
    return dict(question) if question else None

# ══════════════════════════════════════════════════════════════
# ROUTES - PUBLIC
# ══════════════════════════════════════════════════════════════
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint for Docker/Kubernetes"""
    try:
        conn, _ = get_db_connection()
        conn.close()
        return jsonify({"status": "healthy", "version": "V21"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@csrf.exempt
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash("Email ve şifre gereklidir.", "danger")
            return render_template('login.html')
        
        try:
            conn, is_pg = get_db_connection()
            if is_pg:
                c = conn.cursor(cursor_factory=RealDictCursor)
            else:
                c = conn.cursor()
            
            q = "SELECT * FROM yoneticiler WHERE kadi=?"
            if is_pg:
                q = q.replace('?', '%s')
            c.execute(q, (email,))
            user = c.fetchone()
            conn.close()
            
            if user:
                stored_pw = user['sifre'] if is_pg else user[2]
                if bcrypt.checkpw(password.encode('utf-8'), stored_pw.encode('utf-8')):
                    session['user_id'] = user['id'] if is_pg else user[0]
                    session['rol'] = user['rol'] if is_pg else user[3]
                    session['ad_soyad'] = user['ad_soyad'] if is_pg else user[5]
                    session['sirket_id'] = user['sirket_id'] if is_pg else user[4]
                    session.permanent = True
                    
                    log_admin_action(session['user_id'], session['ad_soyad'], 'LOGIN')
                    flash(f"Hoş geldiniz, {session['ad_soyad']}!", "success")
                    return redirect(url_for('admin_dashboard'))
                    
            flash("Hatalı email veya şifre.", "danger")
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash("Giriş sırasında hata oluştu.", "danger")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        log_admin_action(session.get('user_id'), session.get('ad_soyad', 'Unknown'), 'LOGOUT')
    session.clear()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for('index'))

@csrf.exempt
@app.route('/sinav-giris', methods=['GET', 'POST'])
def sinav_giris():
    if request.method == 'POST':
        giris_kodu = request.form.get('giris_kodu', '').strip().upper()
        
        if not giris_kodu:
            flash("Giriş kodu zorunludur.", "danger")
            return render_template('sinav_giris.html')
        
        conn, is_pg = get_db_connection()
        if is_pg:
            c = conn.cursor(cursor_factory=RealDictCursor)
        else:
            c = conn.cursor()
        
        q = "SELECT * FROM adaylar WHERE giris_kodu=? AND is_deleted=0"
        if is_pg:
            q = q.replace('?', '%s')
        c.execute(q, (giris_kodu,))
        aday = c.fetchone()
        conn.close()
        
        if aday:
            aday_id = aday['id'] if is_pg else aday[0]
            ad_soyad = aday['ad_soyad'] if is_pg else aday[1]
            durum = aday['durum'] if is_pg else aday[8]
            
            if durum == 'Tamamlandi':
                flash("Bu sınav daha önce tamamlanmış.", "warning")
                return render_template('sinav_giris.html')
            
            session['aday_id'] = aday_id
            session['aday_ad'] = ad_soyad
            
            # Start exam if not started
            if durum == 'Bekliyor':
                sinav_suresi = aday['sinav_suresi'] if is_pg else aday[6]
                if not sinav_suresi:
                    sinav_suresi = 30
                son_tarih = datetime.datetime.now() + timedelta(minutes=sinav_suresi)
                
                conn, is_pg = get_db_connection()
                c = conn.cursor()
                q = "UPDATE adaylar SET durum='Devam', sinav_son_tarih=? WHERE id=?"
                if is_pg:
                    q = q.replace('?', '%s')
                c.execute(q, (son_tarih.isoformat(), aday_id))
                conn.commit()
                conn.close()
            
            flash(f"Hoş geldiniz, {ad_soyad}!", "success")
            return redirect(url_for('sinav'))
        else:
            flash("Geçersiz giriş kodu.", "danger")
    
    return render_template('sinav_giris.html')

@app.route('/sinav', methods=['GET', 'POST'])
def sinav():
    aday_id = session.get('aday_id')
    if not aday_id:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for('sinav_giris'))
    
    if not is_exam_active(aday_id):
        return redirect(url_for('sinav_bitir'))
    
    # Get candidate info
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    q = "SELECT * FROM adaylar WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (aday_id,))
    aday = c.fetchone()
    
    # Count answered
    q = "SELECT COUNT(*) as cnt FROM cevaplar WHERE aday_id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (aday_id,))
    answered_count = c.fetchone()
    answered = answered_count['cnt'] if is_pg else answered_count[0]
    conn.close()
    
    soru_limiti = aday['soru_limiti'] if is_pg else aday[17] or 10
    difficulty = aday['current_difficulty'] if is_pg else aday[22] or 'B1'
    
    if answered >= soru_limiti:
        return redirect(url_for('sinav_bitir'))
    
    if request.method == 'POST':
        soru_id = request.form.get('soru_id')
        cevap = request.form.get('cevap', '').upper()
        
        if soru_id and cevap:
            # Get correct answer
            conn, is_pg = get_db_connection()
            if is_pg:
                c = conn.cursor(cursor_factory=RealDictCursor)
            else:
                c = conn.cursor()
            
            q = "SELECT dogru_cevap, zorluk FROM sorular WHERE id=?"
            if is_pg:
                q = q.replace('?', '%s')
            c.execute(q, (soru_id,))
            soru = c.fetchone()
            
            if soru:
                dogru = soru['dogru_cevap'] if is_pg else soru[0]
                zorluk = soru['zorluk'] if is_pg else soru[1]
                dogru_mu = 1 if cevap == dogru else 0
                
                # Save answer
                q = "INSERT INTO cevaplar (aday_id, soru_id, verilen_cevap, dogru_mu) VALUES (?,?,?,?)"
                if is_pg:
                    q = q.replace('?', '%s')
                c.execute(q, (aday_id, soru_id, cevap, dogru_mu))
                
                # Adaptive difficulty
                levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
                current_idx = levels.index(zorluk) if zorluk in levels else 2
                
                if dogru_mu and current_idx < len(levels) - 1:
                    new_diff = levels[current_idx + 1]
                elif not dogru_mu and current_idx > 0:
                    new_diff = levels[current_idx - 1]
                else:
                    new_diff = zorluk
                
                q = "UPDATE adaylar SET current_difficulty=? WHERE id=?"
                if is_pg:
                    q = q.replace('?', '%s')
                c.execute(q, (new_diff, aday_id))
                
                conn.commit()
            conn.close()
            
            # Check if completed
            if answered + 1 >= soru_limiti:
                return redirect(url_for('sinav_bitir'))
    
    # Get next question
    question = get_next_question(aday_id, difficulty)
    
    if not question:
        # Try other difficulties
        for lvl in ['B1', 'A2', 'B2', 'A1', 'C1', 'C2']:
            question = get_next_question(aday_id, lvl)
            if question:
                break
    
    if not question:
        return redirect(url_for('sinav_bitir'))
    
    # Calculate remaining time
    sinav_son = aday['sinav_son_tarih'] if is_pg else aday[14]
    if sinav_son:
        if isinstance(sinav_son, str):
            son_dt = datetime.datetime.fromisoformat(sinav_son)
        else:
            son_dt = sinav_son
        remaining = int((son_dt - datetime.datetime.now()).total_seconds())
    else:
        remaining = 1800  # 30 min default
    
    return render_template('sinav.html', 
                          soru=question, 
                          soru_no=answered + 1, 
                          toplam=soru_limiti,
                          kalan_sure=max(0, remaining))

@app.route('/sinav-bitir')
def sinav_bitir():
    aday_id = session.get('aday_id')
    if not aday_id:
        return redirect(url_for('index'))
    
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    # Calculate score
    q = "SELECT COUNT(*) as total, SUM(dogru_mu) as dogru FROM cevaplar WHERE aday_id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (aday_id,))
    result = c.fetchone()
    
    total = result['total'] if is_pg else result[0]
    dogru = result['dogru'] if is_pg else result[1]
    dogru = dogru or 0
    
    puan = round((dogru / total * 100), 1) if total > 0 else 0
    
    # Determine level
    if puan >= 90:
        seviye = 'C2'
    elif puan >= 80:
        seviye = 'C1'
    elif puan >= 70:
        seviye = 'B2'
    elif puan >= 60:
        seviye = 'B1'
    elif puan >= 50:
        seviye = 'A2'
    else:
        seviye = 'A1'
    
    cert_hash = generate_cert_hash(aday_id, puan)
    
    q = "UPDATE adaylar SET durum='Tamamlandi', puan=?, seviye_sonuc=?, bitis_tarihi=?, certificate_hash=? WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (puan, seviye, datetime.datetime.now().isoformat(), cert_hash, aday_id))
    conn.commit()
    conn.close()
    
    session.pop('aday_id', None)
    session.pop('aday_ad', None)
    
    return render_template('sinav_bitti.html', puan=puan, seviye=seviye, dogru=dogru, total=total, cert_hash=cert_hash)

@app.route('/cert/verify/<cert_hash>')
def cert_verify(cert_hash):
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    q = "SELECT ad_soyad, puan, seviye_sonuc, bitis_tarihi FROM adaylar WHERE certificate_hash=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (cert_hash,))
    aday = c.fetchone()
    conn.close()
    
    return render_template('cert_verify.html', aday=aday, cert_hash=cert_hash)

# ══════════════════════════════════════════════════════════════
# ROUTES - ADMIN
# ══════════════════════════════════════════════════════════════
@app.route('/admin')
@app.route('/admin/dashboard')
@check_role(['super_admin', 'sirket_admin', 'recruiter'])
def admin_dashboard():
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    rol = session.get('rol')
    sid = session.get('sirket_id')
    
    if rol == 'super_admin':
        c.execute("SELECT COUNT(*) as cnt FROM adaylar WHERE is_deleted=0")
        aday_sayisi = c.fetchone()['cnt'] if is_pg else c.fetchone()[0]
        c.execute("SELECT COUNT(*) as cnt FROM sorular")
        soru_sayisi = c.fetchone()['cnt'] if is_pg else c.fetchone()[0]
        c.execute("SELECT COUNT(*) as cnt FROM sirketler")
        sirket_sayisi = c.fetchone()['cnt'] if is_pg else c.fetchone()[0]
    else:
        q = "SELECT COUNT(*) as cnt FROM adaylar WHERE sirket_id=? AND is_deleted=0"
        if is_pg:
            q = q.replace('?', '%s')
        c.execute(q, (sid,))
        aday_sayisi = c.fetchone()['cnt'] if is_pg else c.fetchone()[0]
        q = "SELECT COUNT(*) as cnt FROM sorular WHERE sirket_id=? OR sirket_id=0"
        if is_pg:
            q = q.replace('?', '%s')
        c.execute(q, (sid,))
        soru_sayisi = c.fetchone()['cnt'] if is_pg else c.fetchone()[0]
        sirket_sayisi = 1
    
    conn.close()
    
    return render_template('dashboard.html', 
                          aday_sayisi=aday_sayisi, 
                          soru_sayisi=soru_sayisi,
                          sirket_sayisi=sirket_sayisi)

@app.route('/admin/adaylar')
@check_role(['super_admin', 'sirket_admin', 'recruiter'])
def admin_adaylar():
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    if session['rol'] == 'super_admin':
        c.execute("SELECT * FROM adaylar WHERE is_deleted=0 ORDER BY id DESC")
    else:
        q = "SELECT * FROM adaylar WHERE sirket_id=? AND is_deleted=0 ORDER BY id DESC"
        if is_pg:
            q = q.replace('?', '%s')
        c.execute(q, (session['sirket_id'],))
    
    adaylar = c.fetchall()
    conn.close()
    
    return render_template('adaylar.html', adaylar=adaylar)

@app.route('/admin/aday-ekle', methods=['GET', 'POST'])
@check_role(['super_admin', 'sirket_admin', 'recruiter'])
def admin_aday_ekle():
    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '').strip()
        email = request.form.get('email', '').strip()
        tc = request.form.get('tc_kimlik', '').strip()
        cep = request.form.get('cep_no', '').strip()
        sinav_suresi = int(request.form.get('sinav_suresi', 30))
        soru_limiti = int(request.form.get('soru_limiti', 10))
        
        if not ad_soyad:
            flash("Ad Soyad zorunludur.", "danger")
            return render_template('aday_form.html', aday=None)
        
        giris_kodu = generate_code(8)
        
        conn, is_pg = get_db_connection()
        c = conn.cursor()
        
        q = """INSERT INTO adaylar (ad_soyad, email, tc_kimlik, cep_no, giris_kodu, 
               sinav_suresi, soru_limiti, sirket_id) VALUES (?,?,?,?,?,?,?,?)"""
        if is_pg:
            q = q.replace('?', '%s')
        
        try:
            c.execute(q, (ad_soyad, email, tc, cep, giris_kodu, sinav_suresi, soru_limiti, session['sirket_id']))
            conn.commit()
            
            log_admin_action(session['user_id'], session['ad_soyad'], 'ADAY_EKLE', None, f"Aday: {ad_soyad}")
            
            # Send email if configured
            if email:
                send_email(email, "Sınav Davetiyesi", 
                          f"Merhaba {ad_soyad},\n\nSınav giriş kodunuz: {giris_kodu}\n\nBaşarılar!", 
                          session['sirket_id'])
            
            flash(f"Aday eklendi. Giriş Kodu: {giris_kodu}", "success")
            return redirect(url_for('admin_adaylar'))
        except Exception as e:
            conn.rollback()
            flash(f"Hata: {str(e)}", "danger")
        finally:
            conn.close()
    
    return render_template('aday_form.html', aday=None)

@app.route('/admin/aday-sil/<int:id>')
@check_role(['super_admin', 'sirket_admin'])
def admin_aday_sil(id):
    conn, is_pg = get_db_connection()
    c = conn.cursor()
    
    q = "UPDATE adaylar SET is_deleted=1 WHERE id=?"
    if is_pg:
        q = q.replace('?', '%s')
    c.execute(q, (id,))
    conn.commit()
    conn.close()
    
    log_admin_action(session['user_id'], session['ad_soyad'], 'ADAY_SIL', id)
    flash("Aday silindi.", "success")
    return redirect(url_for('admin_adaylar'))

@app.route('/admin/sorular')
@check_role(['super_admin', 'sirket_admin'])
def admin_sorular():
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    if session['rol'] == 'super_admin':
        c.execute("SELECT * FROM sorular ORDER BY id DESC")
    else:
        q = "SELECT * FROM sorular WHERE sirket_id=? OR sirket_id=0 ORDER BY id DESC"
        if is_pg:
            q = q.replace('?', '%s')
        c.execute(q, (session['sirket_id'],))
    
    sorular = c.fetchall()
    conn.close()
    
    return render_template('sorular.html', sorular=sorular)

@app.route('/admin/soru-ekle', methods=['GET', 'POST'])
@check_role(['super_admin', 'sirket_admin'])
def admin_soru_ekle():
    if request.method == 'POST':
        soru_metni = request.form.get('soru_metni', '').strip()
        secenek_a = request.form.get('secenek_a', '').strip()
        secenek_b = request.form.get('secenek_b', '').strip()
        secenek_c = request.form.get('secenek_c', '').strip()
        secenek_d = request.form.get('secenek_d', '').strip()
        dogru_cevap = request.form.get('dogru_cevap', '').upper()
        kategori = request.form.get('kategori', 'Grammar')
        zorluk = request.form.get('zorluk', 'B1')
        
        if not soru_metni or not dogru_cevap:
            flash("Soru metni ve doğru cevap zorunludur.", "danger")
            return render_template('soru_form.html', soru=None)
        
        conn, is_pg = get_db_connection()
        c = conn.cursor()
        
        sirket_id = 0 if session['rol'] == 'super_admin' else session['sirket_id']
        
        q = """INSERT INTO sorular (soru_metni, secenek_a, secenek_b, secenek_c, secenek_d, 
               dogru_cevap, kategori, zorluk, sirket_id) VALUES (?,?,?,?,?,?,?,?,?)"""
        if is_pg:
            q = q.replace('?', '%s')
        
        c.execute(q, (soru_metni, secenek_a, secenek_b, secenek_c, secenek_d, dogru_cevap, kategori, zorluk, sirket_id))
        conn.commit()
        conn.close()
        
        log_admin_action(session['user_id'], session['ad_soyad'], 'SORU_EKLE')
        flash("Soru eklendi.", "success")
        return redirect(url_for('admin_sorular'))
    
    return render_template('soru_form.html', soru=None)

@app.route('/admin/sablonlar')
@check_role(['super_admin', 'sirket_admin'])
def admin_sablonlar():
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    if session['rol'] == 'super_admin':
        c.execute("SELECT * FROM sinav_sablonlari ORDER BY id DESC")
    else:
        q = "SELECT * FROM sinav_sablonlari WHERE sirket_id=?"
        if is_pg:
            q = q.replace('?', '%s')
        c.execute(q, (session['sirket_id'],))
    
    sablonlar = c.fetchall()
    conn.close()
    
    return render_template('sablonlar.html', sablonlar=sablonlar)

@app.route('/admin/sablon-ekle', methods=['GET', 'POST'])
@check_role(['super_admin', 'sirket_admin'])
def admin_sablon_ekle():
    if request.method == 'POST':
        isim = request.form.get('isim', '').strip()
        sinav_suresi = int(request.form.get('sinav_suresi', 30))
        soru_limiti = int(request.form.get('soru_limiti', 10))
        baslangic_seviyesi = request.form.get('baslangic_seviyesi', 'B1')
        
        conn, is_pg = get_db_connection()
        c = conn.cursor()
        
        q = "INSERT INTO sinav_sablonlari (isim, sinav_suresi, soru_limiti, baslangic_seviyesi, sirket_id) VALUES (?,?,?,?,?)"
        if is_pg:
            q = q.replace('?', '%s')
        
        c.execute(q, (isim, sinav_suresi, soru_limiti, baslangic_seviyesi, session['sirket_id']))
        conn.commit()
        conn.close()
        
        flash("Şablon eklendi.", "success")
        return redirect(url_for('admin_sablonlar'))
    
    return render_template('sablon_form.html', sablon=None)

@app.route('/admin/raporlar')
@check_role(['super_admin', 'sirket_admin'])
def admin_raporlar():
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    sid = session['sirket_id']
    rol = session['rol']
    
    # Get completed exams
    if rol == 'super_admin':
        c.execute("SELECT * FROM adaylar WHERE durum='Tamamlandi' AND is_deleted=0 ORDER BY bitis_tarihi DESC LIMIT 100")
    else:
        q = "SELECT * FROM adaylar WHERE sirket_id=? AND durum='Tamamlandi' AND is_deleted=0 ORDER BY bitis_tarihi DESC LIMIT 100"
        if is_pg:
            q = q.replace('?', '%s')
        c.execute(q, (sid,))
    
    tamamlananlar = c.fetchall()
    conn.close()
    
    return render_template('raporlar.html', tamamlananlar=tamamlananlar)

@app.route('/admin/export')
@check_role(['super_admin', 'sirket_admin'])
def admin_export():
    format = request.args.get('format', 'csv')
    
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    if session['rol'] == 'super_admin':
        c.execute("SELECT ad_soyad, email, puan, seviye_sonuc, durum, bitis_tarihi FROM adaylar WHERE is_deleted=0")
    else:
        q = "SELECT ad_soyad, email, puan, seviye_sonuc, durum, bitis_tarihi FROM adaylar WHERE sirket_id=? AND is_deleted=0"
        if is_pg:
            q = q.replace('?', '%s')
        c.execute(q, (session['sirket_id'],))
    
    data = c.fetchall()
    conn.close()
    
    if is_pg:
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame(data, columns=['ad_soyad', 'email', 'puan', 'seviye_sonuc', 'durum', 'bitis_tarihi'])
    
    out = io.BytesIO()
    
    if format == 'xlsx':
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        filename = 'adaylar.xlsx'
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif format == 'json':
        out.write(df.to_json(orient='records', force_ascii=False).encode('utf-8'))
        filename = 'adaylar.json'
        mimetype = 'application/json'
    else:
        out.write(df.to_csv(index=False).encode('utf-8'))
        filename = 'adaylar.csv'
        mimetype = 'text/csv'
    
    out.seek(0)
    return send_file(out, download_name=filename, as_attachment=True, mimetype=mimetype)

@app.route('/admin/bulk-upload', methods=['POST'])
@check_role(['super_admin', 'sirket_admin'])
def admin_bulk_upload():
    if 'file' not in request.files:
        flash("Dosya seçilmedi.", "danger")
        return redirect(url_for('admin_adaylar'))
    
    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        flash("Sadece Excel dosyaları kabul edilir.", "danger")
        return redirect(url_for('admin_adaylar'))
    
    try:
        df = pd.read_excel(file)
        required = {'ad_soyad'}
        
        if not required.issubset(set(df.columns)):
            flash("Excel dosyasında 'ad_soyad' kolonu zorunludur.", "danger")
            return redirect(url_for('admin_adaylar'))
        
        conn, is_pg = get_db_connection()
        c = conn.cursor()
        
        count = 0
        for _, row in df.iterrows():
            ad_soyad = str(row.get('ad_soyad', '')).strip()
            email = str(row.get('email', '')).strip() if 'email' in df.columns else ''
            tc = str(row.get('tc_kimlik', '')).strip() if 'tc_kimlik' in df.columns else ''
            giris_kodu = generate_code(8)
            
            q = "INSERT INTO adaylar (ad_soyad, email, tc_kimlik, giris_kodu, sirket_id) VALUES (?,?,?,?,?)"
            if is_pg:
                q = q.replace('?', '%s')
            
            try:
                c.execute(q, (ad_soyad, email, tc, giris_kodu, session['sirket_id']))
                count += 1
            except:
                continue
        
        conn.commit()
        conn.close()
        
        flash(f"{count} aday başarıyla eklendi.", "success")
    except Exception as e:
        flash(f"Hata: {str(e)}", "danger")
    
    return redirect(url_for('admin_adaylar'))

# GDPR/KVKK Privacy Routes
@app.route('/candidate/privacy', methods=['GET', 'POST'])
def candidate_privacy():
    aday_id = session.get('aday_id')
    if not aday_id:
        flash("Önce giriş yapmalısınız.", "warning")
        return redirect(url_for('sinav_giris'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        conn, is_pg = get_db_connection()
        if is_pg:
            c = conn.cursor(cursor_factory=RealDictCursor)
        else:
            c = conn.cursor()
        
        if action == 'download':
            q = "SELECT * FROM adaylar WHERE id=?"
            if is_pg:
                q = q.replace('?', '%s')
            c.execute(q, (aday_id,))
            aday = c.fetchone()
            conn.close()
            
            if is_pg:
                df = pd.DataFrame([dict(aday)])
            else:
                df = pd.DataFrame([dict(zip([d[0] for d in c.description], aday))])
            
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            out.seek(0)
            
            return send_file(out, download_name='my_data.xlsx', as_attachment=True)
        
        elif action == 'delete':
            q = "UPDATE adaylar SET is_deleted=1 WHERE id=?"
            if is_pg:
                q = q.replace('?', '%s')
            c.execute(q, (aday_id,))
            conn.commit()
            conn.close()
            
            session.clear()
            flash("Verileriniz silindi.", "success")
            return redirect(url_for('index'))
        
        conn.close()
    
    return render_template('privacy.html')

# Super Admin Routes
@app.route('/admin/super-rapor')
@check_role(['super_admin'])
def admin_super_rapor():
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    c.execute("SELECT COUNT(*) as cnt FROM sirketler")
    sirket = c.fetchone()['cnt'] if is_pg else c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) as cnt FROM adaylar WHERE is_deleted=0")
    aday = c.fetchone()['cnt'] if is_pg else c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) as cnt FROM adaylar WHERE durum='Tamamlandi' AND is_deleted=0")
    tamamlanan = c.fetchone()['cnt'] if is_pg else c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) as cnt FROM adaylar WHERE anomaly_count > 5 AND is_deleted=0")
    fraud = c.fetchone()['cnt'] if is_pg else c.fetchone()[0]
    
    c.execute("SELECT SUM(kredi) as total FROM sirketler")
    kredi = c.fetchone()['total'] if is_pg else c.fetchone()[0]
    kredi = kredi or 0
    
    conn.close()
    
    return render_template('super_rapor.html', 
                          sirket=sirket, aday=aday, 
                          tamamlanan=tamamlanan, fraud=fraud, kredi=kredi)

@app.route('/admin/fraud-heatmap')
@check_role(['super_admin'])
def admin_fraud_heatmap():
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    c.execute("SELECT id, ad_soyad, anomaly_count, trust_score, bitis_tarihi FROM adaylar WHERE anomaly_count > 0 ORDER BY anomaly_count DESC LIMIT 100")
    frauds = c.fetchall()
    conn.close()
    
    return render_template('fraud_heatmap.html', frauds=frauds)

@app.route('/admin/logs')
@check_role(['super_admin'])
def admin_logs():
    conn, is_pg = get_db_connection()
    if is_pg:
        c = conn.cursor(cursor_factory=RealDictCursor)
    else:
        c = conn.cursor()
    
    c.execute("SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT 200")
    logs = c.fetchall()
    conn.close()
    
    return render_template('admin_logs.html', logs=logs)

@app.route('/company/onboard')
def company_onboard():
    return render_template('onboard.html')

# ══════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ══════════════════════════════════════════════════════════════
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return render_template('500.html'), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded", "message": str(e.description)}), 429

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)

# -*- coding: utf-8 -*-
"""
Exam Routes - Exam interface and flow
DÜZELTME: Demo modu desteği eklendi
GitHub: app/routes/exam.py
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from app.extensions import db
import random
from datetime import datetime

exam_bp = Blueprint('exam', __name__)


def exam_required(f):
    """Require active exam session - FIXED: candidate_auth.sinav_giris"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'aday_id' not in session:
            flash("Lütfen sınav giriş kodunuzu girin.", "warning")
            return redirect(url_for('candidate_auth.sinav_giris'))
        return f(*args, **kwargs)
    return decorated


def login_required(f):
    """Require admin login"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash("Lütfen giriş yapın.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    """Only superadmin can access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'superadmin':
            flash("Bu işlem sadece süper admin tarafından yapılabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════
# SINAV SAYFALARI
# ══════════════════════════════════════════════════════════════

@exam_bp.route('/')
@exam_bp.route('/sinav')
@exam_required
def sinav():
    """Main exam page - displays current question"""
    from app.models import Candidate, Question, ExamAnswer
    
    aday_id = session.get('aday_id')
    sinav_modu = session.get('sinav_modu', 'gercek')
    
    # ══════════════════════════════════════════════════════════════
    # DEMO MODU: Veritabanı sorgusu yapmadan demo sınav göster
    # ══════════════════════════════════════════════════════════════
    if sinav_modu == 'demo' or aday_id == 'demo':
        return render_demo_exam()
    
    # ══════════════════════════════════════════════════════════════
    # GERÇEK SINAV: Aday ID'nin integer olduğunu kontrol et
    # ══════════════════════════════════════════════════════════════
    try:
        aday_id = int(aday_id)
    except (ValueError, TypeError):
        session.clear()
        flash("Geçersiz sınav oturumu. Lütfen tekrar giriş yapın.", "warning")
        return redirect(url_for('candidate_auth.sinav_giris'))
    
    candidate = Candidate.query.get(aday_id)
    
    if not candidate:
        session.clear()
        flash("Aday bulunamadı. Lütfen tekrar giriş yapın.", "warning")
        return redirect(url_for('candidate_auth.sinav_giris'))
    
    # Sınav başlama tarihi kontrolü
    if not candidate.baslama_tarihi:
        candidate.baslama_tarihi = datetime.utcnow()
        candidate.sinav_durumu = 'devam_ediyor'
        db.session.commit()
    
    # Süre kontrolü
    elapsed = datetime.utcnow() - candidate.baslama_tarihi
    sinav_suresi = candidate.sinav_suresi or 30  # Default 30 dakika
    remaining = (sinav_suresi * 60) - elapsed.total_seconds()
    
    if remaining <= 0:
        return redirect(url_for('exam.sinav_bitti'))
    
    # Cevaplanan soruları al
    answered_ids = [a.soru_id for a in ExamAnswer.query.filter_by(aday_id=aday_id).all()]
    
    # Soru limiti kontrolü
    soru_limiti = candidate.soru_limiti or 25
    if len(answered_ids) >= soru_limiti:
        return redirect(url_for('exam.sinav_bitti'))
    
    # Sonraki soruyu seç
    question = select_next_question(candidate, answered_ids)
    
    if not question:
        return redirect(url_for('exam.sinav_bitti'))
    
    # SECURITY: Store active question ID to prevent manipulation
    session['active_question_id'] = question.id
    session['question_started_at'] = datetime.utcnow().isoformat()
    
    soru_no = len(answered_ids) + 1
    
    return render_template('sinav.html',
                          soru=question,
                          soru_no=soru_no,
                          toplam=soru_limiti,
                          kalan_sure=int(remaining),
                          soru_suresi=candidate.soru_suresi or 0,
                          is_demo=False)


def render_demo_exam():
    """Demo sınavı render et - veritabanı kullanmadan"""
    from app.models import Question
    
    # Demo soru sayısını session'dan al veya başlat
    demo_soru_no = session.get('demo_soru_no', 1)
    demo_cevaplar = session.get('demo_cevaplar', [])
    
    # Demo sınav 10 soru
    if demo_soru_no > 10:
        return redirect(url_for('exam.demo_sonuc'))
    
    # Demo sorular - rastgele veritabanından veya sabit sorular
    try:
        # Önce veritabanından rastgele soru almayı dene
        question = Question.query.filter_by(is_active=True).order_by(db.func.random()).first()
        
        if question:
            session['demo_active_question_id'] = question.id
        else:
            # Veritabanında soru yoksa demo soru oluştur
            question = create_demo_question(demo_soru_no)
            session['demo_active_question_id'] = 'demo'
            
    except Exception as e:
        current_app.logger.warning(f"Demo soru alınamadı: {e}")
        question = create_demo_question(demo_soru_no)
        session['demo_active_question_id'] = 'demo'
    
    return render_template('sinav.html',
                          soru=question,
                          soru_no=demo_soru_no,
                          toplam=10,
                          kalan_sure=1800,  # 30 dakika (demo için sabit)
                          soru_suresi=0,
                          is_demo=True)


def create_demo_question(soru_no):
    """Veritabanı olmadan demo soru oluştur"""
    demo_sorular = [
        {
            'id': 'demo',
            'soru_metni': 'She _____ to the office every day.',
            'secenekler': '{"A": "go", "B": "goes", "C": "going", "D": "gone"}',
            'dogru_cevap': 'B',
            'zorluk': 'A2'
        },
        {
            'id': 'demo',
            'soru_metni': 'I have been living here _____ 2010.',
            'secenekler': '{"A": "for", "B": "since", "C": "from", "D": "at"}',
            'dogru_cevap': 'B',
            'zorluk': 'B1'
        },
        {
            'id': 'demo',
            'soru_metni': 'If I _____ rich, I would travel the world.',
            'secenekler': '{"A": "am", "B": "was", "C": "were", "D": "be"}',
            'dogru_cevap': 'C',
            'zorluk': 'B2'
        },
        {
            'id': 'demo',
            'soru_metni': 'The book _____ by millions of people.',
            'secenekler': '{"A": "has read", "B": "has been read", "C": "is reading", "D": "reads"}',
            'dogru_cevap': 'B',
            'zorluk': 'B2'
        },
        {
            'id': 'demo',
            'soru_metni': 'What _____ you doing when I called?',
            'secenekler': '{"A": "are", "B": "was", "C": "were", "D": "did"}',
            'dogru_cevap': 'C',
            'zorluk': 'A2'
        },
        {
            'id': 'demo',
            'soru_metni': 'He suggested _____ a new approach.',
            'secenekler': '{"A": "to try", "B": "trying", "C": "try", "D": "tried"}',
            'dogru_cevap': 'B',
            'zorluk': 'B1'
        },
        {
            'id': 'demo',
            'soru_metni': 'The meeting _____ postponed until next week.',
            'secenekler': '{"A": "is", "B": "has", "C": "was", "D": "been"}',
            'dogru_cevap': 'C',
            'zorluk': 'B1'
        },
        {
            'id': 'demo',
            'soru_metni': '_____ you ever visited Paris?',
            'secenekler': '{"A": "Did", "B": "Have", "C": "Are", "D": "Do"}',
            'dogru_cevap': 'B',
            'zorluk': 'A2'
        },
        {
            'id': 'demo',
            'soru_metni': 'I wish I _____ more time to finish the project.',
            'secenekler': '{"A": "have", "B": "had", "C": "has", "D": "having"}',
            'dogru_cevap': 'B',
            'zorluk': 'B2'
        },
        {
            'id': 'demo',
            'soru_metni': 'She is _____ intelligent than her brother.',
            'secenekler': '{"A": "most", "B": "more", "C": "much", "D": "many"}',
            'dogru_cevap': 'B',
            'zorluk': 'A2'
        }
    ]
    
    # Soru numarasına göre soru seç
    idx = (soru_no - 1) % len(demo_sorular)
    soru_data = demo_sorular[idx]
    
    # Mock Question object oluştur
    class MockQuestion:
        def __init__(self, data):
            self.id = data['id']
            self.soru_metni = data['soru_metni']
            self.secenekler = data['secenekler']
            self.dogru_cevap = data['dogru_cevap']
            self.zorluk = data['zorluk']
            self.soru_tipi = 'SECMELI'
    
    return MockQuestion(soru_data)


def select_next_question(candidate, answered_ids):
    """Select next question using CAT algorithm or random"""
    from app.models import Question
    
    # Query available questions
    query = Question.query.filter(
        Question.is_active == True
    )
    
    # Şirket ID varsa filtrele
    if candidate.sirket_id:
        # Şirkete özel veya genel soruları al
        query = query.filter(
            db.or_(
                Question.sirket_id == candidate.sirket_id,
                Question.sirket_id == None
            )
        )
    
    if answered_ids:
        query = query.filter(~Question.id.in_(answered_ids))
    
    # Filter by current difficulty (CAT)
    difficulty = candidate.current_difficulty or 'B1'
    questions_at_level = query.filter_by(zorluk=difficulty).all()
    
    if questions_at_level:
        return random.choice(questions_at_level)
    
    # Fallback to any available question
    all_questions = query.all()
    if all_questions:
        return random.choice(all_questions)
    
    return None


# ══════════════════════════════════════════════════════════════
# CEVAP GÖNDERİMİ
# ══════════════════════════════════════════════════════════════

@exam_bp.route('/sinav', methods=['POST'])
@exam_required
def sinav_cevap():
    """Submit answer and get next question"""
    from app.models import Candidate, Question, ExamAnswer
    
    aday_id = session.get('aday_id')
    sinav_modu = session.get('sinav_modu', 'gercek')
    
    # ══════════════════════════════════════════════════════════════
    # DEMO MODU: Veritabanına kaydetmeden devam et
    # ══════════════════════════════════════════════════════════════
    if sinav_modu == 'demo' or aday_id == 'demo':
        return handle_demo_answer()
    
    # ══════════════════════════════════════════════════════════════
    # GERÇEK SINAV
    # ══════════════════════════════════════════════════════════════
    try:
        aday_id = int(aday_id)
    except (ValueError, TypeError):
        session.clear()
        flash("Geçersiz sınav oturumu.", "warning")
        return redirect(url_for('candidate_auth.sinav_giris'))
    
    soru_id = request.form.get('soru_id', type=int)
    cevap = request.form.get('cevap', '').upper()
    
    # SECURITY: Validate question ID matches session
    active_question_id = session.get('active_question_id')
    if not active_question_id or soru_id != active_question_id:
        flash("Geçersiz soru ID. Lütfen tekrar deneyin.", "warning")
        return redirect(url_for('exam.sinav'))
    
    # Get question
    question = Question.query.get(soru_id)
    if not question:
        return redirect(url_for('exam.sinav'))
    
    # Check answer
    is_correct = cevap == question.dogru_cevap.upper()
    
    # Save answer
    answer = ExamAnswer(
        aday_id=aday_id,
        soru_id=soru_id,
        verilen_cevap=cevap,
        dogru_mu=is_correct
    )
    db.session.add(answer)
    
    # Update CAT difficulty
    candidate = Candidate.query.get(aday_id)
    if candidate:
        update_cat_difficulty(candidate, question.zorluk, is_correct)
    
    # Clear active question from session
    session.pop('active_question_id', None)
    session.pop('question_started_at', None)
    
    db.session.commit()
    
    return redirect(url_for('exam.sinav'))


def handle_demo_answer():
    """Demo cevabını işle"""
    cevap = request.form.get('cevap', '').upper()
    
    # Demo cevapları kaydet
    demo_cevaplar = session.get('demo_cevaplar', [])
    demo_cevaplar.append(cevap)
    session['demo_cevaplar'] = demo_cevaplar
    
    # Soru numarasını artır
    demo_soru_no = session.get('demo_soru_no', 1)
    session['demo_soru_no'] = demo_soru_no + 1
    
    # Son soru mu?
    if demo_soru_no >= 10:
        return redirect(url_for('exam.demo_sonuc'))
    
    return redirect(url_for('exam.sinav'))


def update_cat_difficulty(candidate, question_difficulty, is_correct):
    """Update candidate difficulty level based on answer"""
    difficulty_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    
    current = candidate.current_difficulty or 'B1'
    if current not in difficulty_levels:
        current = 'B1'
    
    current_idx = difficulty_levels.index(current)
    
    if is_correct and current_idx < len(difficulty_levels) - 1:
        candidate.current_difficulty = difficulty_levels[current_idx + 1]
    elif not is_correct and current_idx > 0:
        candidate.current_difficulty = difficulty_levels[current_idx - 1]


# ══════════════════════════════════════════════════════════════
# SINAV BİTİŞ
# ══════════════════════════════════════════════════════════════

@exam_bp.route('/sinav-bitti')
@exam_required
def sinav_bitti():
    """Exam finished - show results"""
    from app.models import Candidate, ExamAnswer
    
    aday_id = session.get('aday_id')
    sinav_modu = session.get('sinav_modu', 'gercek')
    
    # Demo modu için demo sonuç sayfasına yönlendir
    if sinav_modu == 'demo' or aday_id == 'demo':
        return redirect(url_for('exam.demo_sonuc'))
    
    try:
        aday_id = int(aday_id)
    except (ValueError, TypeError):
        session.clear()
        return redirect(url_for('candidate_auth.sinav_giris'))
    
    candidate = Candidate.query.get(aday_id)
    
    if not candidate:
        session.clear()
        return redirect(url_for('candidate_auth.sinav_giris'))
    
    # Sınavı tamamla ve sonuçları hesapla
    if candidate.sinav_durumu != 'tamamlandi':
        calculate_exam_results(candidate)
    
    return render_template('sinav_sonuc.html', 
                          aday=candidate,
                          is_demo=False)


@exam_bp.route('/demo-sonuc')
def demo_sonuc():
    """Demo sınav sonucu"""
    demo_cevaplar = session.get('demo_cevaplar', [])
    demo_soru_no = session.get('demo_soru_no', 1)
    
    # Basit hesaplama
    dogru_sayisi = len(demo_cevaplar)  # Demo için tüm cevapları doğru say
    toplam_soru = max(demo_soru_no - 1, 1)
    
    # Sonuç verisi oluştur
    sonuc = {
        'ad_soyad': session.get('aday_ad', 'Demo Kullanıcı'),
        'dogru_sayisi': dogru_sayisi,
        'toplam_soru': toplam_soru,
        'puan': int((dogru_sayisi / toplam_soru) * 100) if toplam_soru > 0 else 0,
        'seviye': 'B1',  # Demo için sabit seviye
        'is_demo': True
    }
    
    # Demo session'ı temizle
    session.pop('demo_soru_no', None)
    session.pop('demo_cevaplar', None)
    session.pop('demo_active_question_id', None)
    
    return render_template('demo_sonuc.html', sonuc=sonuc)


def calculate_exam_results(candidate):
    """Sınav sonuçlarını hesapla ve kaydet"""
    from app.models import ExamAnswer
    
    answers = ExamAnswer.query.filter_by(aday_id=candidate.id).all()
    
    if not answers:
        candidate.puan = 0
        candidate.seviye_sonuc = 'A1'
        candidate.sinav_durumu = 'tamamlandi'
        candidate.bitis_tarihi = datetime.utcnow()
        db.session.commit()
        return
    
    # Doğru cevap sayısı
    dogru_sayisi = sum(1 for a in answers if a.dogru_mu)
    toplam = len(answers)
    
    # Puan hesapla
    puan = int((dogru_sayisi / toplam) * 100) if toplam > 0 else 0
    candidate.puan = puan
    
    # Seviye belirle
    if puan >= 90:
        candidate.seviye_sonuc = 'C2'
    elif puan >= 80:
        candidate.seviye_sonuc = 'C1'
    elif puan >= 70:
        candidate.seviye_sonuc = 'B2'
    elif puan >= 60:
        candidate.seviye_sonuc = 'B1'
    elif puan >= 50:
        candidate.seviye_sonuc = 'A2'
    else:
        candidate.seviye_sonuc = 'A1'
    
    candidate.sinav_durumu = 'tamamlandi'
    candidate.bitis_tarihi = datetime.utcnow()
    
    db.session.commit()


# ══════════════════════════════════════════════════════════════
# SINAV YÖNETİMİ (ADMIN)
# ══════════════════════════════════════════════════════════════

@exam_bp.route('/admin/reset/<int:aday_id>', methods=['POST'])
@login_required
@superadmin_required
def reset_exam(aday_id):
    """Reset exam for a candidate"""
    from app.models import Candidate, ExamAnswer
    
    candidate = Candidate.query.get_or_404(aday_id)
    
    # Cevapları sil
    ExamAnswer.query.filter_by(aday_id=aday_id).delete()
    
    # Aday durumunu sıfırla
    candidate.sinav_durumu = 'beklemede'
    candidate.baslama_tarihi = None
    candidate.bitis_tarihi = None
    candidate.puan = None
    candidate.seviye_sonuc = None
    candidate.current_difficulty = 'B1'
    
    db.session.commit()
    
    flash(f"{candidate.ad_soyad} adayının sınavı sıfırlandı.", "success")
    return redirect(url_for('admin.aday_detay', aday_id=aday_id))


@exam_bp.route('/admin/extend-time/<int:aday_id>', methods=['POST'])
@login_required
@superadmin_required
def extend_time(aday_id):
    """Extend exam time for a candidate"""
    from app.models import Candidate
    
    candidate = Candidate.query.get_or_404(aday_id)
    extra_minutes = request.form.get('extra_minutes', 10, type=int)
    
    candidate.sinav_suresi = (candidate.sinav_suresi or 30) + extra_minutes
    db.session.commit()
    
    flash(f"{candidate.ad_soyad} adayının sınav süresi {extra_minutes} dakika uzatıldı.", "success")
    return redirect(url_for('admin.aday_detay', aday_id=aday_id))


# ══════════════════════════════════════════════════════════════
# SINAV ÇIKIŞ
# ══════════════════════════════════════════════════════════════

@exam_bp.route('/cikis')
def sinav_cikis():
    """Sınavdan çık"""
    # Sadece sınav session'larını temizle
    session.pop('aday_id', None)
    session.pop('aday_ad', None)
    session.pop('sinav_modu', None)
    session.pop('active_question_id', None)
    session.pop('question_started_at', None)
    session.pop('demo_soru_no', None)
    session.pop('demo_cevaplar', None)
    session.pop('demo_active_question_id', None)
    
    flash("Sınavdan çıkış yaptınız.", "info")
    return redirect(url_for('main.index'))

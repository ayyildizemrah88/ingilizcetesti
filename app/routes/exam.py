# -*- coding: utf-8 -*-
"""
Exam Routes - Exam interface and flow
GitHub: app/routes/exam.py
GÜNCELLENDİ:
- calculate_exam_results fonksiyonuna error handling eklendi
- sinav_bitti route'una try-except eklendi
- Bölme hatası koruması eklendi
- sinav_sonuc.html -> sinav_bitti.html düzeltildi
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from app.extensions import db
import random
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

exam_bp = Blueprint('exam', __name__)


def exam_required(f):
    """Require active exam session"""
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
        if session.get('rol') not in ['superadmin', 'super_admin', 'admin']:
            flash("Bu işlem sadece admin tarafından yapılabilir.", "danger")
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════
# SINAV SAYFASI
# ═══════════════════════════════════════════════════════════

@exam_bp.route('/')
@exam_bp.route('/sinav')
@exam_required
def sinav():
    """Main exam page - displays current question"""
    from app.models import Candidate, Question, ExamAnswer

    aday_id = session.get('aday_id')

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


def select_next_question(candidate, answered_ids):
    """Select next question using CAT algorithm or random"""
    from app.models import Question

    query = Question.query.filter(
        Question.is_active == True
    )

    # Şirket ID varsa filtrele
    if candidate.sirket_id:
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


# ═══════════════════════════════════════════════════════════
# CEVAP GÖNDERME
# ═══════════════════════════════════════════════════════════

@exam_bp.route('/sinav', methods=['POST'])
@exam_required
def sinav_cevap():
    """Submit answer and get next question"""
    from app.models import Candidate, Question, ExamAnswer

    aday_id = session.get('aday_id')

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


# ═══════════════════════════════════════════════════════════
# SINAV BİTİŞİ VE SONUÇ - HATA DÜZELTİLDİ
# ═══════════════════════════════════════════════════════════

@exam_bp.route('/sinav-bitti')
@exam_required
def sinav_bitti():
    """Exam finished - show results"""
    from app.models import Candidate, ExamAnswer

    aday_id = session.get('aday_id')

    try:
        aday_id = int(aday_id)
    except (ValueError, TypeError):
        session.clear()
        flash("Geçersiz sınav oturumu.", "warning")
        return redirect(url_for('candidate_auth.sinav_giris'))

    try:
        candidate = Candidate.query.get(aday_id)

        if not candidate:
            session.clear()
            flash("Aday bulunamadı.", "warning")
            return redirect(url_for('candidate_auth.sinav_giris'))

        # Sınavı tamamla ve sonuçları hesapla
        if candidate.sinav_durumu != 'tamamlandi':
            try:
                calculate_exam_results(candidate)
            except Exception as calc_error:
                logger.error(f"Sonuç hesaplama hatası (aday_id={aday_id}): {calc_error}")
                # Hata olsa bile minimum sonuç ata
                candidate.sinav_durumu = 'tamamlandi'
                candidate.bitis_tarihi = datetime.utcnow()
                if not candidate.puan:
                    candidate.puan = 0
                if not candidate.seviye_sonuc:
                    candidate.seviye_sonuc = 'A1'
                db.session.commit()

        # DÜZELTİLDİ: sinav_sonuc.html -> sinav_bitti.html
        return render_template('sinav_bitti.html',
                              aday=candidate,
                              is_demo=False)

    except Exception as e:
        logger.error(f"sinav_bitti hatası (aday_id={aday_id}): {e}")
        flash("Sonuç sayfası yüklenirken bir hata oluştu.", "danger")
        return redirect(url_for('main.index'))


@exam_bp.route('/sonuc/<giris_kodu>')
def sonuc(giris_kodu):
    """Sınav sonucu görüntüleme"""
    from app.models import Candidate

    candidate = Candidate.query.filter_by(giris_kodu=giris_kodu).first_or_404()

    if candidate.sinav_durumu != 'tamamlandi':
        flash('Bu sınav henüz tamamlanmamış.', 'warning')
        return redirect(url_for('main.index'))

    # DÜZELTİLDİ: sinav_sonuc.html -> sinav_bitti.html
    return render_template('sinav_bitti.html', aday=candidate, is_demo=False)


def calculate_exam_results(candidate):
    """
    Sınav sonuçlarını hesapla ve kaydet
    GÜNCELLENDİ: Error handling ve edge case kontrolü eklendi
    """
    from app.models import ExamAnswer

    try:
        answers = ExamAnswer.query.filter_by(aday_id=candidate.id).all()

        # Cevap yoksa varsayılan değerler ata
        if not answers:
            logger.warning(f"Aday {candidate.id} için cevap bulunamadı")
            candidate.puan = 0
            candidate.seviye_sonuc = 'A1'
            candidate.sinav_durumu = 'tamamlandi'
            candidate.bitis_tarihi = datetime.utcnow()
            db.session.commit()
            return

        # Doğru cevap sayısı
        dogru_sayisi = sum(1 for a in answers if a.dogru_mu)
        toplam = len(answers)

        # Bölme hatası koruması
        if toplam > 0:
            puan = int((dogru_sayisi / toplam) * 100)
        else:
            puan = 0

        # Puan sınırları kontrolü
        puan = max(0, min(100, puan))
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
        logger.info(f"Aday {candidate.id} sınav tamamlandı: Puan={puan}, Seviye={candidate.seviye_sonuc}")

    except Exception as e:
        logger.error(f"calculate_exam_results hatası (aday_id={candidate.id}): {e}")
        # Minimum değerler ata ve kaydet
        try:
            candidate.puan = 0
            candidate.seviye_sonuc = 'A1'
            candidate.sinav_durumu = 'tamamlandi'
            candidate.bitis_tarihi = datetime.utcnow()
            db.session.commit()
        except Exception as commit_error:
            logger.error(f"Commit hatası: {commit_error}")
            db.session.rollback()
        raise  # Üst katmana hatayı ilet


# ═══════════════════════════════════════════════════════════
# PAUSE / RESUME
# ═══════════════════════════════════════════════════════════

@exam_bp.route('/sinav/pause', methods=['POST'])
@exam_required
def pause_exam():
    """Sınavı duraklat"""
    from app.models import Candidate

    aday_id = session.get('aday_id')

    try:
        aday_id = int(aday_id)
        candidate = Candidate.query.get(aday_id)

        if not candidate:
            return jsonify({'status': 'error', 'message': 'Aday bulunamadı'}), 404

        if candidate.sinav_durumu == 'duraklatildi':
            return jsonify({'status': 'already_paused', 'message': 'Sınav zaten duraklatılmış'})

        candidate.sinav_durumu = 'duraklatildi'
        db.session.commit()

        return jsonify({'status': 'paused', 'message': 'Sınav duraklatıldı. Kaldığınız yerden devam edebilirsiniz.'})

    except Exception as e:
        logger.error(f"Pause hatası: {e}")
        return jsonify({'status': 'error', 'message': 'Duraklatma başarısız'}), 500


# ═══════════════════════════════════════════════════════════
# ADMIN FONKSİYONLARI
# ═══════════════════════════════════════════════════════════

@exam_bp.route('/admin/reset/<int:aday_id>', methods=['POST'])
@login_required
@superadmin_required
def reset_exam(aday_id):
    """Reset exam for a candidate - ONLY ADMIN"""
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
    """Extend exam time for a candidate - ONLY ADMIN"""
    from app.models import Candidate

    candidate = Candidate.query.get_or_404(aday_id)
    extra_minutes = request.form.get('extra_minutes', 10, type=int)

    candidate.sinav_suresi = (candidate.sinav_suresi or 30) + extra_minutes
    db.session.commit()

    flash(f"{candidate.ad_soyad} adayının sınav süresi {extra_minutes} dakika uzatıldı.", "success")
    return redirect(url_for('admin.aday_detay', aday_id=aday_id))


# ═══════════════════════════════════════════════════════════
# DEMO SINAV
# ═══════════════════════════════════════════════════════════

@exam_bp.route('/admin/demo-baslat', methods=['POST'])
@login_required
@superadmin_required
def start_demo():
    """Demo sınav başlat - SADECE ADMIN"""
    ad = request.form.get('ad', 'Demo')
    soyad = request.form.get('soyad', 'Kullanıcı')
    email = request.form.get('email', 'demo@example.com')

    session['aday_id'] = 'demo'
    session['aday_ad'] = f"{ad} {soyad}"
    session['sinav_modu'] = 'demo'
    session['demo_soru_no'] = 1
    session['demo_cevaplar'] = []

    flash(f'Demo sınav başlatıldı: {ad} {soyad}', 'success')
    return redirect(url_for('exam.demo_sinav'))


@exam_bp.route('/demo')
def demo_sinav():
    """Demo sınav sayfası"""
    sinav_modu = session.get('sinav_modu')

    if sinav_modu != 'demo':
        return render_template('demo_bilgi.html')

    demo_soru_no = session.get('demo_soru_no', 1)

    if demo_soru_no > 10:
        return redirect(url_for('exam.demo_sonuc'))

    question = create_demo_question(demo_soru_no)

    return render_template('sinav.html',
                          soru=question,
                          soru_no=demo_soru_no,
                          toplam=10,
                          kalan_sure=1800,
                          soru_suresi=0,
                          is_demo=True)


@exam_bp.route('/demo', methods=['POST'])
def demo_cevap():
    """Demo cevabını işle"""
    sinav_modu = session.get('sinav_modu')

    if sinav_modu != 'demo':
        flash('Geçersiz demo oturumu.', 'warning')
        return redirect(url_for('main.index'))

    cevap = request.form.get('cevap', '').upper()

    demo_cevaplar = session.get('demo_cevaplar', [])
    demo_cevaplar.append(cevap)
    session['demo_cevaplar'] = demo_cevaplar

    demo_soru_no = session.get('demo_soru_no', 1)
    session['demo_soru_no'] = demo_soru_no + 1

    if demo_soru_no >= 10:
        return redirect(url_for('exam.demo_sonuc'))

    return redirect(url_for('exam.demo_sinav'))


@exam_bp.route('/demo-sonuc')
def demo_sonuc():
    """Demo sınav sonucu"""
    demo_cevaplar = session.get('demo_cevaplar', [])
    demo_soru_no = session.get('demo_soru_no', 1)

    dogru_cevaplar = ['B', 'B', 'C', 'B', 'C', 'B', 'C', 'B', 'B', 'B']
    dogru_sayisi = sum(1 for i, c in enumerate(demo_cevaplar) if i < len(dogru_cevaplar) and c == dogru_cevaplar[i])
    toplam_soru = max(demo_soru_no - 1, 1)

    puan = int((dogru_sayisi / toplam_soru) * 100) if toplam_soru > 0 else 0

    if puan >= 80:
        seviye = 'B2'
    elif puan >= 60:
        seviye = 'B1'
    elif puan >= 40:
        seviye = 'A2'
    else:
        seviye = 'A1'

    sonuc = {
        'ad_soyad': session.get('aday_ad', 'Demo Kullanıcı'),
        'dogru_sayisi': dogru_sayisi,
        'toplam_soru': toplam_soru,
        'puan': puan,
        'seviye': seviye,
        'is_demo': True
    }

    # Demo session'ı temizle
    session.pop('demo_soru_no', None)
    session.pop('demo_cevaplar', None)
    session.pop('demo_active_question_id', None)
    session.pop('sinav_modu', None)
    session.pop('aday_id', None)

    return render_template('demo_sonuc.html', sonuc=sonuc)


def create_demo_question(soru_no):
    """Veritabanı olmadan demo soru oluştur"""
    demo_sorular = [
        {
            'id': 'demo',
            'soru_metni': 'She _____ to the office every day.',
            'secenek_a': 'go',
            'secenek_b': 'goes',
            'secenek_c': 'going',
            'secenek_d': 'gone',
            'dogru_cevap': 'B',
            'zorluk': 'A2'
        },
        {
            'id': 'demo',
            'soru_metni': 'I have been living here _____ 2010.',
            'secenek_a': 'for',
            'secenek_b': 'since',
            'secenek_c': 'from',
            'secenek_d': 'at',
            'dogru_cevap': 'B',
            'zorluk': 'B1'
        },
        {
            'id': 'demo',
            'soru_metni': 'If I _____ rich, I would travel the world.',
            'secenek_a': 'am',
            'secenek_b': 'was',
            'secenek_c': 'were',
            'secenek_d': 'be',
            'dogru_cevap': 'C',
            'zorluk': 'B2'
        },
        {
            'id': 'demo',
            'soru_metni': 'The book _____ by millions of people.',
            'secenek_a': 'has read',
            'secenek_b': 'has been read',
            'secenek_c': 'is reading',
            'secenek_d': 'reads',
            'dogru_cevap': 'B',
            'zorluk': 'B2'
        },
        {
            'id': 'demo',
            'soru_metni': 'What _____ you doing when I called?',
            'secenek_a': 'are',
            'secenek_b': 'was',
            'secenek_c': 'were',
            'secenek_d': 'did',
            'dogru_cevap': 'C',
            'zorluk': 'A2'
        },
        {
            'id': 'demo',
            'soru_metni': 'He suggested _____ a new approach.',
            'secenek_a': 'to try',
            'secenek_b': 'trying',
            'secenek_c': 'try',
            'secenek_d': 'tried',
            'dogru_cevap': 'B',
            'zorluk': 'B1'
        },
        {
            'id': 'demo',
            'soru_metni': 'The meeting _____ postponed until next week.',
            'secenek_a': 'is',
            'secenek_b': 'has',
            'secenek_c': 'was',
            'secenek_d': 'been',
            'dogru_cevap': 'C',
            'zorluk': 'B1'
        },
        {
            'id': 'demo',
            'soru_metni': '_____ you ever visited Paris?',
            'secenek_a': 'Did',
            'secenek_b': 'Have',
            'secenek_c': 'Are',
            'secenek_d': 'Do',
            'dogru_cevap': 'B',
            'zorluk': 'A2'
        },
        {
            'id': 'demo',
            'soru_metni': 'I wish I _____ more time to finish the project.',
            'secenek_a': 'have',
            'secenek_b': 'had',
            'secenek_c': 'has',
            'secenek_d': 'having',
            'dogru_cevap': 'B',
            'zorluk': 'B2'
        },
        {
            'id': 'demo',
            'soru_metni': 'She is _____ intelligent than her brother.',
            'secenek_a': 'most',
            'secenek_b': 'more',
            'secenek_c': 'much',
            'secenek_d': 'many',
            'dogru_cevap': 'B',
            'zorluk': 'A2'
        }
    ]

    idx = (soru_no - 1) % len(demo_sorular)
    soru_data = demo_sorular[idx]

    class MockQuestion:
        def __init__(self, data):
            self.id = data['id']
            self.soru_metni = data['soru_metni']
            self.secenek_a = data['secenek_a']
            self.secenek_b = data['secenek_b']
            self.secenek_c = data['secenek_c']
            self.secenek_d = data['secenek_d']
            self.dogru_cevap = data['dogru_cevap']
            self.zorluk = data['zorluk']
            self.soru_tipi = 'SECMELI'

    return MockQuestion(soru_data)


# ═══════════════════════════════════════════════════════════
# ÇIKIŞ
# ═══════════════════════════════════════════════════════════

@exam_bp.route('/cikis')
def sinav_cikis():
    """Sınavdan çık"""
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

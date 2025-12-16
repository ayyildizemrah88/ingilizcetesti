# -*- coding: utf-8 -*-
"""
API Routes - REST API endpoints with Swagger documentation
Version: 1.0 (API versioning enabled with /api/v1 prefix)
"""
from flask import Blueprint, request, jsonify, session
from app.extensions import db, limiter

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


# ══════════════════════════════════════════════════════════════
# CANDIDATES API
# ══════════════════════════════════════════════════════════════

@api_bp.route('/candidates', methods=['GET'])
@limiter.limit("100 per minute")
def list_candidates():
    """
    List all candidates
    ---
    tags:
      - Candidates
    security:
      - ApiKeyAuth: []
    parameters:
      - name: page
        in: query
        type: integer
        description: Page number
      - name: per_page
        in: query
        type: integer
        description: Items per page (max 100)
      - name: status
        in: query
        type: string
        enum: [beklemede, devam_ediyor, tamamlandi]
    responses:
      200:
        description: List of candidates
        schema:
          type: object
          properties:
            candidates:
              type: array
            total:
              type: integer
            page:
              type: integer
    """
    from app.models import Candidate
    
    api_key = request.headers.get('X-API-KEY')
    sirket_id = validate_api_key(api_key)
    
    if not sirket_id:
        return jsonify({'error': 'Invalid API key'}), 401
    
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    status = request.args.get('status')
    
    query = Candidate.query.filter_by(sirket_id=sirket_id, is_deleted=False)
    
    if status:
        query = query.filter_by(sinav_durumu=status)
    
    candidates = query.order_by(Candidate.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'candidates': [c.to_dict() for c in candidates.items],
        'total': candidates.total,
        'page': page,
        'pages': candidates.pages
    })


@api_bp.route('/candidates', methods=['POST'])
@limiter.limit("50 per minute")
def create_candidate():
    """
    Create a new candidate
    ---
    tags:
      - Candidates
    security:
      - ApiKeyAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - ad_soyad
          properties:
            ad_soyad:
              type: string
              description: Full name
            email:
              type: string
              format: email
            tc_kimlik:
              type: string
            sinav_suresi:
              type: integer
              description: Exam duration in minutes
            send_email:
              type: boolean
              description: Send invitation email
    responses:
      201:
        description: Candidate created
        schema:
          type: object
          properties:
            id:
              type: integer
            giris_kodu:
              type: string
      400:
        description: Validation error
      401:
        description: Invalid API key
    """
    from app.models import Candidate
    import string
    import random
    
    api_key = request.headers.get('X-API-KEY')
    sirket_id = validate_api_key(api_key)
    
    if not sirket_id:
        return jsonify({'error': 'Invalid API key'}), 401
    
    data = request.get_json()
    
    if not data or not data.get('ad_soyad'):
        return jsonify({'error': 'ad_soyad is required'}), 400
    
    giris_kodu = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    candidate = Candidate(
        ad_soyad=data.get('ad_soyad'),
        email=data.get('email'),
        tc_kimlik=data.get('tc_kimlik'),
        cep_no=data.get('cep_no'),
        giris_kodu=giris_kodu,
        sinav_suresi=data.get('sinav_suresi', 30),
        soru_limiti=data.get('soru_limiti', 25),
        sirket_id=sirket_id
    )
    
    db.session.add(candidate)
    db.session.commit()
    
    # Send email if requested
    if data.get('send_email') and candidate.email:
        from app.tasks.email_tasks import send_exam_invitation
        send_exam_invitation.delay(candidate.id)
    
    return jsonify({
        'id': candidate.id,
        'giris_kodu': giris_kodu,
        'status': 'created'
    }), 201


@api_bp.route('/candidates/<int:id>', methods=['GET'])
def get_candidate(id):
    """
    Get candidate details
    ---
    tags:
      - Candidates
    security:
      - ApiKeyAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Candidate details
      404:
        description: Candidate not found
    """
    from app.models import Candidate
    
    api_key = request.headers.get('X-API-KEY')
    sirket_id = validate_api_key(api_key)
    
    if not sirket_id:
        return jsonify({'error': 'Invalid API key'}), 401
    
    candidate = Candidate.query.filter_by(id=id, sirket_id=sirket_id).first()
    
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    return jsonify(candidate.to_dict())


@api_bp.route('/candidates/<int:id>/results', methods=['GET'])
def get_candidate_results(id):
    """
    Get candidate exam results
    ---
    tags:
      - Candidates
    security:
      - ApiKeyAuth: []
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Exam results with skill breakdown
    """
    from app.models import Candidate
    
    api_key = request.headers.get('X-API-KEY')
    sirket_id = validate_api_key(api_key)
    
    if not sirket_id:
        return jsonify({'error': 'Invalid API key'}), 401
    
    candidate = Candidate.query.filter_by(id=id, sirket_id=sirket_id).first()
    
    if not candidate:
        return jsonify({'error': 'Candidate not found'}), 404
    
    if candidate.sinav_durumu != 'tamamlandi':
        return jsonify({'error': 'Exam not completed'}), 400
    
    return jsonify({
        'id': candidate.id,
        'ad_soyad': candidate.ad_soyad,
        'puan': candidate.puan,
        'cefr_level': candidate.seviye_sonuc,
        'band_score': candidate.band_score,
        'skills': {
            'grammar': candidate.p_grammar,
            'vocabulary': candidate.p_vocabulary,
            'reading': candidate.p_reading,
            'listening': candidate.p_listening,
            'writing': candidate.p_writing,
            'speaking': candidate.p_speaking
        },
        'ielts': {
            'reading': candidate.ielts_reading,
            'writing': candidate.ielts_writing,
            'speaking': candidate.ielts_speaking,
            'listening': candidate.ielts_listening
        },
        'completed_at': candidate.bitis_tarihi.isoformat() if candidate.bitis_tarihi else None,
        'certificate_hash': candidate.certificate_hash
    })


# ══════════════════════════════════════════════════════════════
# QUESTIONS API
# ══════════════════════════════════════════════════════════════

@api_bp.route('/questions', methods=['GET'])
def list_questions():
    """
    List questions in question bank
    ---
    tags:
      - Questions
    security:
      - ApiKeyAuth: []
    parameters:
      - name: category
        in: query
        type: string
        enum: [grammar, vocabulary, reading]
      - name: difficulty
        in: query
        type: string
        enum: [A1, A2, B1, B2, C1, C2]
    responses:
      200:
        description: List of questions
    """
    from app.models import Question
    
    api_key = request.headers.get('X-API-KEY')
    sirket_id = validate_api_key(api_key)
    
    if not sirket_id:
        return jsonify({'error': 'Invalid API key'}), 401
    
    query = Question.query.filter_by(sirket_id=sirket_id, is_active=True)
    
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    
    if category:
        query = query.filter_by(kategori=category)
    if difficulty:
        query = query.filter_by(zorluk=difficulty)
    
    questions = query.limit(100).all()
    
    return jsonify({
        'questions': [q.to_dict() for q in questions],
        'count': len(questions)
    })


@api_bp.route('/questions', methods=['POST'])
def create_question():
    """
    Create a new question
    ---
    tags:
      - Questions
    security:
      - ApiKeyAuth: []
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - soru_metni
            - dogru_cevap
          properties:
            soru_metni:
              type: string
            secenek_a:
              type: string
            secenek_b:
              type: string
            secenek_c:
              type: string
            secenek_d:
              type: string
            dogru_cevap:
              type: string
              enum: [A, B, C, D]
            kategori:
              type: string
            zorluk:
              type: string
              enum: [A1, A2, B1, B2, C1, C2]
    responses:
      201:
        description: Question created
    """
    from app.models import Question
    
    api_key = request.headers.get('X-API-KEY')
    sirket_id = validate_api_key(api_key)
    
    if not sirket_id:
        return jsonify({'error': 'Invalid API key'}), 401
    
    data = request.get_json()
    
    question = Question(
        soru_metni=data.get('soru_metni'),
        secenek_a=data.get('secenek_a'),
        secenek_b=data.get('secenek_b'),
        secenek_c=data.get('secenek_c'),
        secenek_d=data.get('secenek_d'),
        dogru_cevap=data.get('dogru_cevap'),
        kategori=data.get('kategori'),
        zorluk=data.get('zorluk', 'B1'),
        sirket_id=sirket_id
    )
    
    db.session.add(question)
    db.session.commit()
    
    return jsonify({'id': question.id, 'status': 'created'}), 201


# ══════════════════════════════════════════════════════════════
# WEBHOOKS API
# ══════════════════════════════════════════════════════════════

@api_bp.route('/webhooks/test', methods=['POST'])
def test_webhook():
    """
    Test webhook endpoint
    ---
    tags:
      - Webhooks
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: Webhook test triggered
    """
    api_key = request.headers.get('X-API-KEY')
    sirket_id = validate_api_key(api_key)
    
    if not sirket_id:
        return jsonify({'error': 'Invalid API key'}), 401
    
    from app.tasks.webhook_tasks import send_test_webhook
    send_test_webhook.delay(sirket_id)
    
    return jsonify({'status': 'test webhook queued'})


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def validate_api_key(api_key):
    """
    Validate API key and return company ID.
    Uses Redis caching to reduce database queries.
    Cache TTL: 10 minutes
    """
    if not api_key:
        return None
    
    import os
    import hashlib
    
    # Try to use Redis cache
    try:
        import redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        
        # Create cache key from hashed API key (for security)
        cache_key = f"api_key:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
        
        # Check cache first
        cached_company_id = r.get(cache_key)
        if cached_company_id is not None:
            if cached_company_id == b'invalid':
                return None
            return int(cached_company_id)
        
        # Cache miss - query database
        from app.models import Company
        company = Company.query.filter_by(api_key=api_key, is_active=True).first()
        
        if company:
            # Cache valid key for 10 minutes
            r.setex(cache_key, 600, str(company.id))
            return company.id
        else:
            # Cache invalid key for 5 minutes (prevent brute force)
            r.setex(cache_key, 300, 'invalid')
            return None
            
    except Exception:
        # Redis unavailable - fall back to database
        from app.models import Company
        company = Company.query.filter_by(api_key=api_key, is_active=True).first()
        return company.id if company else None


def invalidate_api_key_cache(old_api_key):
    """
    Invalidate cached API key when it's changed or revoked.
    SECURITY: Call this when API key is rotated in admin panel.
    
    Args:
        old_api_key: The API key being invalidated
    """
    if not old_api_key:
        return False
    
    import os
    import hashlib
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        import redis
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        
        # Delete the cache key
        cache_key = f"api_key:{hashlib.sha256(old_api_key.encode()).hexdigest()[:16]}"
        deleted = r.delete(cache_key)
        
        logger.info(f"API key cache invalidated: {deleted > 0}")
        return deleted > 0
        
    except Exception as e:
        logger.warning(f"Failed to invalidate API key cache: {e}")
        return False


def send_async_email_safe(task_func, *args, **kwargs):
    """
    Safely send async email with error handling.
    RELIABILITY: Prevents silent failures when Celery/Redis is down.
    
    Args:
        task_func: The Celery task function (e.g., send_exam_invitation)
        *args: Positional arguments for the task
        **kwargs: Keyword arguments for the task
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        task_func.delay(*args, **kwargs)
        return True, None
    except Exception as e:
        error_msg = f"Failed to queue email task: {str(e)}"
        logger.error(error_msg)
        
        # Optionally save to database for retry
        try:
            from app.models.email_queue import EmailQueue
            email_queue = EmailQueue(
                task_name=task_func.name,
                args=str(args),
                kwargs=str(kwargs),
                status='failed',
                error=str(e)
            )
            db.session.add(email_queue)
            db.session.commit()
        except Exception:
            pass  # Email queue table might not exist
        
        return False, error_msg


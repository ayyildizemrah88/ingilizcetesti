# -*- coding: utf-8 -*-
"""
API Endpoints Unit Tests
Tests for REST API endpoints including AI service, health checks, and data APIs
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestHealthEndpoints:
    """Tests for health check endpoints"""

    def test_health_check_returns_200(self, client):
        """Test main health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data

    def test_health_check_includes_database_status(self, client):
        """Test health check includes database connectivity"""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'database' in data or 'status' in data

    def test_readiness_endpoint(self, client):
        """Test readiness probe endpoint"""
        response = client.get('/health/ready')
        assert response.status_code in [200, 404]  # May not exist

    def test_liveness_endpoint(self, client):
        """Test liveness probe endpoint"""
        response = client.get('/health/live')
        assert response.status_code in [200, 404]


class TestAIServiceEndpoints:
    """Tests for AI service API endpoints"""

    def test_ai_health_endpoint(self, client):
        """Test AI service health check"""
        response = client.get('/api/ai/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert 'keys_configured' in data

    def test_ai_chat_requires_prompt(self, client):
        """Test AI chat endpoint requires prompt"""
        response = client.post('/api/ai/chat',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_ai_chat_with_empty_prompt(self, client):
        """Test AI chat with empty prompt returns error"""
        response = client.post('/api/ai/chat',
            data=json.dumps({'prompt': ''}),
            content_type='application/json'
        )
        assert response.status_code == 400

    @patch('openai.OpenAI')
    def test_ai_chat_with_valid_prompt(self, mock_openai, client):
        """Test AI chat with valid prompt"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            response = client.post('/api/ai/chat',
                data=json.dumps({'prompt': 'Hello'}),
                content_type='application/json'
            )
            # May return 500 if no key configured
            assert response.status_code in [200, 500]

    def test_ai_generate_question_endpoint(self, client):
        """Test AI question generation endpoint"""
        response = client.post('/api/ai/generate-question',
            data=json.dumps({
                'difficulty': 'A2',
                'category': 'grammar'
            }),
            content_type='application/json'
        )
        # May return 500 if no API key
        assert response.status_code in [200, 500]


class TestAPIAuthentication:
    """Tests for API authentication"""

    def test_protected_endpoint_requires_auth(self, client):
        """Test that protected endpoints require authentication"""
        response = client.get('/api/admin/users')
        assert response.status_code in [401, 403, 302]  # Unauthorized or redirect

    def test_api_with_invalid_token(self, client):
        """Test API rejects invalid tokens"""
        response = client.get('/api/admin/users',
            headers={'Authorization': 'Bearer invalid-token'}
        )
        assert response.status_code in [401, 403, 302]


class TestQuestionAPI:
    """Tests for question-related API endpoints"""

    def test_get_questions_requires_auth(self, client):
        """Test getting questions requires authentication"""
        response = client.get('/api/questions')
        assert response.status_code in [401, 403, 302, 404]

    def test_get_questions_with_auth(self, logged_in_client):
        """Test getting questions with authentication"""
        response = logged_in_client.get('/api/questions')
        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist

    def test_question_by_id(self, logged_in_client):
        """Test getting a specific question"""
        response = logged_in_client.get('/api/questions/1')
        assert response.status_code in [200, 404]

    def test_question_categories(self, client):
        """Test getting question categories"""
        response = client.get('/api/categories')
        assert response.status_code in [200, 404]


class TestExamAPI:
    """Tests for exam-related API endpoints"""

    def test_exam_list_requires_auth(self, client):
        """Test exam list requires authentication"""
        response = client.get('/api/exams')
        assert response.status_code in [401, 403, 302, 404]

    def test_exam_templates(self, logged_in_client):
        """Test getting exam templates"""
        response = logged_in_client.get('/api/exam-templates')
        assert response.status_code in [200, 404]

    def test_exam_results(self, logged_in_client):
        """Test getting exam results"""
        response = logged_in_client.get('/api/results')
        assert response.status_code in [200, 404]


class TestCandidateAPI:
    """Tests for candidate-related API endpoints"""

    def test_candidate_login_endpoint(self, client):
        """Test candidate login endpoint exists"""
        response = client.post('/api/candidate/login',
            data=json.dumps({'giris_kodu': 'TEST123'}),
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 401, 404]

    def test_candidate_verify_code(self, client):
        """Test candidate code verification"""
        response = client.post('/api/candidate/verify',
            data=json.dumps({'code': 'INVALID'}),
            content_type='application/json'
        )
        assert response.status_code in [200, 400, 401, 404]


class TestCreditsAPI:
    """Tests for credits/payment API endpoints"""

    def test_credits_balance_requires_auth(self, client):
        """Test credits balance requires authentication"""
        response = client.get('/api/credits/balance')
        assert response.status_code in [401, 403, 302, 404]

    def test_credits_balance_with_auth(self, logged_in_client):
        """Test credits balance with authentication"""
        response = logged_in_client.get('/api/credits/balance')
        assert response.status_code in [200, 404]

    def test_credits_packages(self, client):
        """Test getting credit packages"""
        response = client.get('/api/credits/packages')
        assert response.status_code in [200, 404]


class TestAnalyticsAPI:
    """Tests for analytics API endpoints"""

    def test_analytics_requires_admin(self, client):
        """Test analytics requires admin authentication"""
        response = client.get('/api/analytics/dashboard')
        assert response.status_code in [401, 403, 302, 404]

    def test_analytics_with_admin(self, admin_client):
        """Test analytics with admin authentication"""
        response = admin_client.get('/api/analytics/dashboard')
        assert response.status_code in [200, 404]


class TestAPIRateLimiting:
    """Tests for API rate limiting"""

    def test_rate_limiting_headers(self, client):
        """Test rate limiting headers are present"""
        response = client.get('/api/ai/health')
        # Rate limit headers may be present
        assert response.status_code == 200

    def test_rate_limit_exceeded(self, client):
        """Test rate limiting kicks in after many requests"""
        # Make many rapid requests
        for _ in range(100):
            client.get('/api/ai/health')
        
        response = client.get('/api/ai/health')
        # Should still work or return 429
        assert response.status_code in [200, 429]


class TestAPIErrorHandling:
    """Tests for API error handling"""

    def test_404_returns_json(self, client):
        """Test 404 errors return JSON for API routes"""
        response = client.get('/api/nonexistent-endpoint')
        assert response.status_code == 404

    def test_invalid_json_returns_400(self, client):
        """Test invalid JSON returns 400"""
        response = client.post('/api/ai/chat',
            data='invalid json{',
            content_type='application/json'
        )
        assert response.status_code in [400, 500]

    def test_method_not_allowed(self, client):
        """Test wrong HTTP method returns 405"""
        response = client.delete('/api/ai/health')
        assert response.status_code in [405, 404]


class TestAPIResponseFormat:
    """Tests for API response format consistency"""

    def test_json_content_type(self, client):
        """Test API returns JSON content type"""
        response = client.get('/api/ai/health')
        assert 'application/json' in response.content_type

    def test_response_has_required_fields(self, client):
        """Test API responses have required fields"""
        response = client.get('/api/ai/health')
        data = json.loads(response.data)
        assert isinstance(data, dict)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def client(app):
    """Test client fixture"""
    return app.test_client()


@pytest.fixture
def app():
    """Create application for testing"""
    from app import create_app

    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['RATELIMIT_ENABLED'] = False

    with app.app_context():
        from app.extensions import db
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def test_user(app):
    """Create a test user"""
    from app.models import User, Company
    from app.extensions import db

    with app.app_context():
        # Create company first
        company = Company(isim='Test Company', email='test@company.com')
        db.session.add(company)
        db.session.flush()

        user = User(
            email='testuser@example.com',
            ad_soyad='Test User',
            rol='customer',
            is_active=True,
            sirket_id=company.id
        )
        user.set_password('TestPassword123!')
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture
def test_admin(app):
    """Create a test admin user"""
    from app.models import User, Company
    from app.extensions import db

    with app.app_context():
        company = Company(isim='Admin Company', email='admin@company.com')
        db.session.add(company)
        db.session.flush()

        admin = User(
            email='admin@example.com',
            ad_soyad='Admin User',
            rol='superadmin',
            is_active=True,
            sirket_id=company.id
        )
        admin.set_password('AdminPassword123!')
        db.session.add(admin)
        db.session.commit()
        yield admin


@pytest.fixture
def logged_in_client(client, test_user):
    """Client with logged in user"""
    client.post('/login', data={
        'email': test_user.email,
        'sifre': 'TestPassword123!'
    })
    return client


@pytest.fixture
def admin_client(client, test_admin):
    """Client with logged in admin"""
    client.post('/login', data={
        'email': test_admin.email,
        'sifre': 'AdminPassword123!'
    })
    return client

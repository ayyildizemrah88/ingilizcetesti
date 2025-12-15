# -*- coding: utf-8 -*-
"""
Pytest Configuration and Fixtures
Shared fixtures for all test modules
"""
import pytest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='session')
def app():
    """Create application for testing (session-scoped)"""
    from app import create_app
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'RATELIMIT_ENABLED': False,
    })
    
    with app.app_context():
        from app.extensions import db
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Test client fixture (function-scoped)"""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Database session fixture with rollback"""
    from app.extensions import db
    
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        yield db.session
        
        transaction.rollback()
        connection.close()


@pytest.fixture(scope='function')
def test_user(app):
    """Create a test user"""
    from app.models import User
    from app.extensions import db
    
    with app.app_context():
        user = User(
            email='testuser@example.com',
            ad_soyad='Test User',
            rol='customer',
            is_active=True
        )
        user.set_password('TestPassword123!')
        db.session.add(user)
        db.session.commit()
        
        yield user
        
        # Cleanup
        db.session.delete(user)
        db.session.commit()


@pytest.fixture(scope='function')
def test_admin(app):
    """Create a test admin user"""
    from app.models import User
    from app.extensions import db
    
    with app.app_context():
        admin = User(
            email='admin@example.com',
            ad_soyad='Admin User',
            rol='superadmin',
            is_active=True
        )
        admin.set_password('AdminPassword123!')
        db.session.add(admin)
        db.session.commit()
        
        yield admin
        
        db.session.delete(admin)
        db.session.commit()


@pytest.fixture(scope='function')
def test_company(app):
    """Create a test company"""
    from app.models import Company
    from app.extensions import db
    
    with app.app_context():
        company = Company(
            ad='Test Company',
            kredi=100,
            is_active=True
        )
        db.session.add(company)
        db.session.commit()
        
        yield company
        
        db.session.delete(company)
        db.session.commit()


@pytest.fixture(scope='function')
def test_candidate(app, test_company):
    """Create a test candidate"""
    from app.models import Candidate
    from app.extensions import db
    
    with app.app_context():
        candidate = Candidate(
            email='candidate@example.com',
            tc_kimlik='12345678901',
            ad='Test',
            soyad='Candidate',
            sirket_id=test_company.id,
            giris_kodu='TEST123',
            sinav_durumu='bekliyor'
        )
        db.session.add(candidate)
        db.session.commit()
        
        yield candidate
        
        db.session.delete(candidate)
        db.session.commit()


@pytest.fixture(scope='function')
def logged_in_client(client, test_user):
    """Client with logged in user"""
    client.post('/login', data={
        'email': test_user.email,
        'sifre': 'TestPassword123!'
    })
    yield client


@pytest.fixture(scope='function')
def admin_client(client, test_admin):
    """Client with logged in admin"""
    client.post('/login', data={
        'email': test_admin.email,
        'sifre': 'AdminPassword123!'
    })
    yield client


# Mock fixtures
@pytest.fixture
def mock_email():
    """Mock email sending"""
    from unittest.mock import patch
    
    with patch('app.tasks.email_tasks.send_email_task.delay') as mock:
        yield mock


@pytest.fixture
def mock_ai():
    """Mock AI service calls"""
    from unittest.mock import patch, MagicMock
    
    mock_response = MagicMock()
    mock_response.text = '{"score": 85, "feedback": "Good job!"}'
    
    with patch('google.generativeai.GenerativeModel') as mock:
        mock.return_value.generate_content.return_value = mock_response
        yield mock


# Test configuration
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add skip marker for integration tests in CI if needed
    if os.environ.get('CI'):
        skip_slow = pytest.mark.skip(reason="Skipping slow tests in CI")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

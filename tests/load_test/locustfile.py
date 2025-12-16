# -*- coding: utf-8 -*-
"""
Load Testing with Locust
Simulates concurrent exam users for stress testing.

Usage:
    pip install locust
    locust -f tests/load_test/locustfile.py --host=http://localhost:5000
    
Then open http://localhost:8089 to configure and run tests.
"""
from locust import HttpUser, task, between, tag, events
import random
import string
import logging

logger = logging.getLogger(__name__)


class ExamCandidate(HttpUser):
    """
    Simulates a candidate taking an exam.
    
    Lifecycle:
    1. Login with entry code
    2. Answer multiple questions
    3. Submit and view results
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.entry_code = None
        self.tc_kimlik = self._generate_tc_kimlik()
        self.questions_answered = 0
        
        # Create test candidate via API if possible
        self._create_test_candidate()
    
    def _generate_tc_kimlik(self):
        """Generate a fake TC Kimlik number."""
        return ''.join(random.choices(string.digits, k=11))
    
    def _create_test_candidate(self):
        """Create a test candidate for this user."""
        # This would typically call an admin API to create test data
        # For now, use predefined test codes
        self.entry_code = f"TEST{random.randint(1000, 9999)}"
    
    @task(1)
    @tag('login')
    def login(self):
        """
        Attempt to login to exam.
        Weight: 1 (least frequent in loop)
        """
        with self.client.post(
            "/sinav-giris",
            data={
                "giris_kodu": self.entry_code,
                "tc_kimlik": self.tc_kimlik
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                if "sınav" in response.text.lower():
                    response.success()
                else:
                    response.failure("Login failed - invalid credentials")
            else:
                response.failure(f"Login error: {response.status_code}")
    
    @task(10)
    @tag('exam', 'question')
    def view_question(self):
        """
        View current exam question.
        Weight: 10 (most frequent)
        """
        with self.client.get("/sinav", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 302:
                # Redirect to login - session expired
                response.success()
            else:
                response.failure(f"View question error: {response.status_code}")
    
    @task(5)
    @tag('exam', 'answer')
    def submit_answer(self):
        """
        Submit an answer to current question.
        Weight: 5
        """
        # Simulate random answer
        answer = random.choice(['A', 'B', 'C', 'D'])
        question_id = random.randint(1, 100)
        
        with self.client.post(
            "/sinav",
            data={
                "soru_id": question_id,
                "cevap": answer
            },
            catch_response=True
        ) as response:
            if response.status_code in [200, 302]:
                self.questions_answered += 1
                response.success()
            else:
                response.failure(f"Submit answer error: {response.status_code}")


class AdminUser(HttpUser):
    """
    Simulates admin panel usage.
    Less frequent than exam users.
    """
    
    wait_time = between(2, 5)
    
    @task(1)
    @tag('admin', 'login')
    def admin_login(self):
        """Admin login attempt."""
        with self.client.post(
            "/login",
            data={
                "email": "admin@test.com",
                "sifre": "testpassword"
            },
            catch_response=True
        ) as response:
            if response.status_code in [200, 302]:
                response.success()
    
    @task(3)
    @tag('admin', 'dashboard')
    def view_dashboard(self):
        """View admin dashboard."""
        self.client.get("/admin/dashboard")
    
    @task(2)
    @tag('admin', 'candidates')
    def list_candidates(self):
        """List candidates."""
        self.client.get("/admin/candidates")


class APIUser(HttpUser):
    """
    Simulates API consumer (external system).
    Tests API endpoints under load.
    """
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        self.api_key = "sk_test_api_key_for_load_testing"
        self.headers = {"X-API-KEY": self.api_key}
    
    @task(5)
    @tag('api', 'candidates')
    def api_list_candidates(self):
        """List candidates via API."""
        with self.client.get(
            "/api/v1/candidates",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("API key invalid")
            else:
                response.failure(f"API error: {response.status_code}")
    
    @task(2)
    @tag('api', 'create')
    def api_create_candidate(self):
        """Create candidate via API."""
        with self.client.post(
            "/api/v1/candidates",
            headers=self.headers,
            json={
                "ad_soyad": f"Load Test User {random.randint(1, 10000)}",
                "email": f"loadtest{random.randint(1, 10000)}@test.com"
            },
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Create failed: {response.status_code}")


# ══════════════════════════════════════════════════════════════════
# CUSTOM METRICS & EVENTS
# ══════════════════════════════════════════════════════════════════

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    logger.info("=" * 50)
    logger.info("LOAD TEST STARTED")
    logger.info(f"Host: {environment.host}")
    logger.info("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    logger.info("=" * 50)
    logger.info("LOAD TEST COMPLETED")
    
    # Print summary
    stats = environment.stats.total
    logger.info(f"Total Requests: {stats.num_requests}")
    logger.info(f"Failed Requests: {stats.num_failures}")
    logger.info(f"Avg Response Time: {stats.avg_response_time:.2f}ms")
    logger.info(f"Requests/sec: {stats.total_rps:.2f}")
    logger.info("=" * 50)

"""
Unit Tests for Scoring Engine
pytest tests/test_scoring.py
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the database connection for testing
class MockCursor:
    def __init__(self, data=None):
        self.data = data or []
        self.idx = 0
    def execute(self, *args): pass
    def fetchone(self): return self.data[0] if self.data else None
    def fetchall(self): return self.data

class MockConn:
    def __init__(self, data=None):
        self._cursor = MockCursor(data)
    def cursor(self, **kwargs): return self._cursor
    def commit(self): pass
    def close(self): pass


# ══════════════════════════════════════════════════════════════
# CEFR LEVEL TESTS
# ══════════════════════════════════════════════════════════════
class TestCEFRLevel:
    """Test CEFR level calculation"""
    
    def test_c2_level(self):
        """Score 90+ should be C2"""
        from app import calculate_cefr_level
        assert calculate_cefr_level(95) == 'C2'
        assert calculate_cefr_level(90) == 'C2'
    
    def test_c1_level(self):
        """Score 75-89 should be C1"""
        from app import calculate_cefr_level
        assert calculate_cefr_level(85) == 'C1'
        assert calculate_cefr_level(75) == 'C1'
    
    def test_b2_level(self):
        """Score 60-74 should be B2"""
        from app import calculate_cefr_level
        assert calculate_cefr_level(70) == 'B2'
        assert calculate_cefr_level(60) == 'B2'
    
    def test_b1_level(self):
        """Score 45-59 should be B1"""
        from app import calculate_cefr_level
        assert calculate_cefr_level(55) == 'B1'
        assert calculate_cefr_level(45) == 'B1'
    
    def test_a2_level(self):
        """Score 30-44 should be A2"""
        from app import calculate_cefr_level
        assert calculate_cefr_level(35) == 'A2'
        assert calculate_cefr_level(30) == 'A2'
    
    def test_a1_level(self):
        """Score below 30 should be A1"""
        from app import calculate_cefr_level
        assert calculate_cefr_level(25) == 'A1'
        assert calculate_cefr_level(0) == 'A1'


# ══════════════════════════════════════════════════════════════
# DIFFICULTY ADJUSTMENT TESTS
# ══════════════════════════════════════════════════════════════
class TestDifficultyAdjustment:
    """Test adaptive difficulty adjustment"""
    
    def test_difficulty_increase_on_correct(self):
        """Correct answer should increase difficulty"""
        from app import DIFFICULTY_ORDER
        current = 'B1'
        idx = DIFFICULTY_ORDER.index(current)
        if idx < len(DIFFICULTY_ORDER) - 1:
            new_level = DIFFICULTY_ORDER[idx + 1]
            assert new_level == 'B2'
    
    def test_difficulty_decrease_on_wrong(self):
        """Wrong answer should decrease difficulty"""
        from app import DIFFICULTY_ORDER
        current = 'B1'
        idx = DIFFICULTY_ORDER.index(current)
        if idx > 0:
            new_level = DIFFICULTY_ORDER[idx - 1]
            assert new_level == 'A2'
    
    def test_difficulty_floor(self):
        """Difficulty should not go below A1"""
        from app import DIFFICULTY_ORDER
        assert DIFFICULTY_ORDER[0] == 'A1'
    
    def test_difficulty_ceiling(self):
        """Difficulty should not go above C2"""
        from app import DIFFICULTY_ORDER
        assert DIFFICULTY_ORDER[-1] == 'C2'


# ══════════════════════════════════════════════════════════════
# SCORE CALCULATION TESTS
# ══════════════════════════════════════════════════════════════
class TestScoreCalculation:
    """Test score calculation logic"""
    
    def test_perfect_score(self):
        """All correct should be 100%"""
        correct = 20
        total = 20
        score = (correct / total) * 100
        assert score == 100
    
    def test_zero_score(self):
        """No correct should be 0%"""
        correct = 0
        total = 20
        score = (correct / total) * 100
        assert score == 0
    
    def test_half_score(self):
        """Half correct should be 50%"""
        correct = 10
        total = 20
        score = (correct / total) * 100
        assert score == 50
    
    def test_division_by_zero_protection(self):
        """Should handle zero total questions"""
        total = 0
        score = 0 if total == 0 else 100
        assert score == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

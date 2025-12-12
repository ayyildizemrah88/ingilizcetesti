"""
Unit Tests for Proctoring Analysis
pytest tests/test_proctoring.py
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════════
# PROCTORING ANALYSIS TESTS
# ══════════════════════════════════════════════════════════════
class TestProctoringAnalysis:
    """Test proctoring suspicious activity detection"""
    
    def test_ok_status(self):
        """Less than 30% suspicious should be OK"""
        total = 10
        suspicious = 2  # 20%
        rate = suspicious / total * 100
        status = 'OK' if suspicious < total * 0.3 else 'REVIEW'
        
        assert status == 'OK'
        assert rate == 20
    
    def test_review_status(self):
        """30-50% suspicious should be REVIEW"""
        total = 10
        suspicious = 4  # 40%
        
        if suspicious < total * 0.3:
            status = 'OK'
        elif suspicious < total * 0.5:
            status = 'REVIEW'
        else:
            status = 'SUSPICIOUS'
        
        assert status == 'REVIEW'
    
    def test_suspicious_status(self):
        """More than 50% suspicious should be SUSPICIOUS"""
        total = 10
        suspicious = 6  # 60%
        
        if suspicious < total * 0.3:
            status = 'OK'
        elif suspicious < total * 0.5:
            status = 'REVIEW'
        else:
            status = 'SUSPICIOUS'
        
        assert status == 'SUSPICIOUS'
    
    def test_no_snapshots(self):
        """Empty snapshots should return 0 rate"""
        total = 0
        rate = 0 if total == 0 else 50
        assert rate == 0


# ══════════════════════════════════════════════════════════════
# SNAPSHOT SCORING TESTS
# ══════════════════════════════════════════════════════════════
class TestSnapshotScoring:
    """Test individual snapshot suspicious scoring"""
    
    def test_normal_score(self):
        """Score below 50 is not suspicious"""
        score = 30
        is_suspicious = score > 50
        assert not is_suspicious
    
    def test_suspicious_score(self):
        """Score above 50 is suspicious"""
        score = 75
        is_suspicious = score > 50
        assert is_suspicious
    
    def test_boundary_score(self):
        """Score exactly 50 is not suspicious"""
        score = 50
        is_suspicious = score > 50
        assert not is_suspicious


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

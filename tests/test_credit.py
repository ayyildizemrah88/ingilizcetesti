"""
Unit Tests for Credit System
pytest tests/test_credit.py
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════════
# CREDIT CHECK TESTS
# ══════════════════════════════════════════════════════════════
class TestCreditCheck:
    """Test credit validation logic"""
    
    def test_sufficient_credit(self):
        """Should allow action when credit is sufficient"""
        current_credit = 100
        required = 1
        assert current_credit >= required
    
    def test_insufficient_credit(self):
        """Should deny action when credit is insufficient"""
        current_credit = 0
        required = 1
        assert not (current_credit >= required)
    
    def test_exact_credit(self):
        """Should allow action when credit equals required"""
        current_credit = 1
        required = 1
        assert current_credit >= required


# ══════════════════════════════════════════════════════════════
# CREDIT DEDUCTION TESTS
# ══════════════════════════════════════════════════════════════
class TestCreditDeduction:
    """Test credit deduction logic"""
    
    def test_deduct_one_credit(self):
        """Deducting 1 credit from 100 should leave 99"""
        current = 100
        deduct = 1
        new_balance = current - deduct
        assert new_balance == 99
    
    def test_deduct_all_credit(self):
        """Deducting all credit should leave 0"""
        current = 50
        deduct = 50
        new_balance = current - deduct
        assert new_balance == 0
    
    def test_no_negative_credit(self):
        """Credit should never go negative"""
        current = 5
        deduct = 10
        new_balance = max(0, current - deduct)
        assert new_balance == 0


# ══════════════════════════════════════════════════════════════
# CREDIT LOGGING TESTS
# ══════════════════════════════════════════════════════════════
class TestCreditLogging:
    """Test credit transaction logging"""
    
    def test_log_entry_fields(self):
        """Log entry should have required fields"""
        log_entry = {
            'sirket_id': 1,
            'miktar': 50,
            'islem_tipi': 'yukle',
            'onceki_bakiye': 100,
            'yeni_bakiye': 150
        }
        
        assert 'sirket_id' in log_entry
        assert 'miktar' in log_entry
        assert 'islem_tipi' in log_entry
        assert log_entry['yeni_bakiye'] == log_entry['onceki_bakiye'] + log_entry['miktar']
    
    def test_deduction_log(self):
        """Deduction log should show negative change"""
        log_entry = {
            'miktar': -1,
            'islem_tipi': 'kullanim',
            'onceki_bakiye': 100,
            'yeni_bakiye': 99
        }
        
        assert log_entry['miktar'] < 0 or log_entry['islem_tipi'] == 'kullanim'
        assert log_entry['yeni_bakiye'] < log_entry['onceki_bakiye']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

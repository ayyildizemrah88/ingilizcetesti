# -*- coding: utf-8 -*-
"""
CAT Algorithm Tests - Comprehensive testing for Computerized Adaptive Testing
"""
import pytest
from unittest.mock import MagicMock, patch


class TestCATDifficultyUpdate:
    """Test CAT difficulty adjustment logic"""
    
    def test_difficulty_increases_on_correct_answer(self):
        """Difficulty should increase when answer is correct"""
        from app.routes.exam import update_cat_difficulty
        
        candidate = MagicMock()
        candidate.current_difficulty = 'B1'
        
        update_cat_difficulty(candidate, 'B1', is_correct=True)
        
        assert candidate.current_difficulty == 'B2'
    
    def test_difficulty_decreases_on_wrong_answer(self):
        """Difficulty should decrease when answer is wrong"""
        from app.routes.exam import update_cat_difficulty
        
        candidate = MagicMock()
        candidate.current_difficulty = 'B2'
        
        update_cat_difficulty(candidate, 'B2', is_correct=False)
        
        assert candidate.current_difficulty == 'B1'
    
    def test_difficulty_stays_at_minimum(self):
        """Difficulty should not go below A1"""
        from app.routes.exam import update_cat_difficulty
        
        candidate = MagicMock()
        candidate.current_difficulty = 'A1'
        
        update_cat_difficulty(candidate, 'A1', is_correct=False)
        
        assert candidate.current_difficulty == 'A1'
    
    def test_difficulty_stays_at_maximum(self):
        """Difficulty should not go above C2"""
        from app.routes.exam import update_cat_difficulty
        
        candidate = MagicMock()
        candidate.current_difficulty = 'C2'
        
        update_cat_difficulty(candidate, 'C2', is_correct=True)
        
        assert candidate.current_difficulty == 'C2'
    
    def test_difficulty_progression_sequence(self):
        """Test full progression from A1 to C2"""
        from app.routes.exam import update_cat_difficulty
        
        expected_sequence = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        
        candidate = MagicMock()
        candidate.current_difficulty = 'A1'
        
        # Answer correctly 5 times to reach C2
        for i in range(5):
            update_cat_difficulty(candidate, candidate.current_difficulty, is_correct=True)
        
        assert candidate.current_difficulty == 'C2'


class TestQuestionSelection:
    """Test question selection algorithm"""
    
    @patch('app.routes.exam.Question')
    def test_selects_question_at_current_difficulty(self, mock_question):
        """Should select questions matching current difficulty"""
        from app.routes.exam import select_next_question
        
        candidate = MagicMock()
        candidate.sirket_id = 1
        candidate.current_difficulty = 'B1'
        
        mock_query = MagicMock()
        mock_question.query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter_by.return_value.all.return_value = [
            MagicMock(id=1, zorluk='B1'),
            MagicMock(id=2, zorluk='B1'),
        ]
        
        result = select_next_question(candidate, [])
        
        assert result is not None
    
    @patch('app.routes.exam.Question')
    def test_excludes_already_answered_questions(self, mock_question):
        """Should not return questions already answered"""
        from app.routes.exam import select_next_question
        
        candidate = MagicMock()
        candidate.sirket_id = 1
        candidate.current_difficulty = 'B1'
        
        answered_ids = [1, 2, 3]
        
        mock_query = MagicMock()
        mock_question.query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Simulate filtered questions
        mock_query.filter_by.return_value.all.return_value = []
        mock_query.all.return_value = [MagicMock(id=4, zorluk='B2')]
        
        result = select_next_question(candidate, answered_ids)
        
        assert result.id == 4
    
    @patch('app.routes.exam.Question')
    def test_returns_none_when_no_questions_available(self, mock_question):
        """Should return None when all questions exhausted"""
        from app.routes.exam import select_next_question
        
        candidate = MagicMock()
        candidate.sirket_id = 1
        candidate.current_difficulty = 'B1'
        
        mock_query = MagicMock()
        mock_question.query.filter.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.filter_by.return_value.all.return_value = []
        mock_query.all.return_value = []
        
        result = select_next_question(candidate, [1, 2, 3, 4, 5])
        
        assert result is None


class TestCEFRLevelCalculation:
    """Test CEFR level calculation from scores"""
    
    def test_c2_threshold(self):
        """Score >= 90 should give C2"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        candidate.puan = 90
        
        assert candidate.get_cefr_level() == 'C2'
    
    def test_c1_threshold(self):
        """Score >= 75 should give C1"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        candidate.puan = 75
        
        assert candidate.get_cefr_level() == 'C1'
    
    def test_b2_threshold(self):
        """Score >= 60 should give B2"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        candidate.puan = 60
        
        assert candidate.get_cefr_level() == 'B2'
    
    def test_b1_threshold(self):
        """Score >= 40 should give B1"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        candidate.puan = 40
        
        assert candidate.get_cefr_level() == 'B1'
    
    def test_a2_threshold(self):
        """Score >= 20 should give A2"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        candidate.puan = 20
        
        assert candidate.get_cefr_level() == 'A2'
    
    def test_a1_threshold(self):
        """Score < 20 should give A1"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        candidate.puan = 15
        
        assert candidate.get_cefr_level() == 'A1'
    
    def test_zero_score(self):
        """Zero score should give A1"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        candidate.puan = 0
        
        assert candidate.get_cefr_level() == 'A1'


class TestScoreCalculation:
    """Test weighted score calculation"""
    
    def test_perfect_scores_give_100(self):
        """All 100s should give 100 total"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        candidate.p_grammar = 100
        candidate.p_vocabulary = 100
        candidate.p_reading = 100
        candidate.p_listening = 100
        candidate.p_writing = 100
        candidate.p_speaking = 100
        
        result = candidate.calculate_total_score()
        
        assert result == 100.0
    
    def test_zero_scores_give_zero(self):
        """All 0s should give 0 total"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        candidate.p_grammar = 0
        candidate.p_vocabulary = 0
        candidate.p_reading = 0
        candidate.p_listening = 0
        candidate.p_writing = 0
        candidate.p_speaking = 0
        
        result = candidate.calculate_total_score()
        
        assert result == 0.0
    
    def test_weighted_average(self):
        """Test weighted calculation"""
        from app.models.candidate import Candidate
        
        candidate = Candidate()
        # Reading and Listening have 20% weight each
        candidate.p_reading = 100
        candidate.p_listening = 100
        # Others have 15% weight each
        candidate.p_grammar = 0
        candidate.p_vocabulary = 0
        candidate.p_writing = 0
        candidate.p_speaking = 0
        
        result = candidate.calculate_total_score()
        
        # 100*0.2 + 100*0.2 = 40
        assert result == 40.0

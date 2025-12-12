# -*- coding: utf-8 -*-
"""
══════════════════════════════════════════════════════════════
CAT ENGINE - Computerized Adaptive Testing using IRT
══════════════════════════════════════════════════════════════
Implements 3-Parameter Logistic Model (3PL) for question selection
"""

import math
import random
from collections import defaultdict

# CEFR Level difficulty parameters (b parameter in IRT)
DIFFICULTY_MAP = {
    'A1': -2.0,
    'A2': -1.0,
    'B1': 0.0,
    'B2': 1.0,
    'C1': 2.0,
    'C2': 3.0
}

# Discrimination parameter (a) - how well item differentiates ability
DEFAULT_DISCRIMINATION = 1.0

# Guessing parameter (c) - probability of correct answer by guessing
DEFAULT_GUESSING = 0.25  # For 4-choice MCQ

class CATEngine:
    """
    Computerized Adaptive Testing Engine using Item Response Theory (IRT)
    Uses 3-Parameter Logistic (3PL) Model
    """
    
    def __init__(self, initial_ability=0.0, se_threshold=0.3, max_questions=30, min_questions=10):
        """
        Initialize CAT Engine
        
        Args:
            initial_ability: Starting theta (ability estimate), 0 = B1 level
            se_threshold: Standard error threshold to stop (lower = more precise)
            max_questions: Maximum questions before stopping
            min_questions: Minimum questions before allowing early stop
        """
        self.ability = initial_ability
        self.se_threshold = se_threshold
        self.max_questions = max_questions
        self.min_questions = min_questions
        self.responses = []  # List of (item_difficulty, is_correct)
        self.ability_history = [initial_ability]
        self.se_history = [1.0]
        
    def probability_correct(self, theta, b, a=DEFAULT_DISCRIMINATION, c=DEFAULT_GUESSING):
        """
        Calculate probability of correct response using 3PL model
        
        P(θ) = c + (1-c) / (1 + e^(-a(θ-b)))
        
        Args:
            theta: Ability parameter
            b: Difficulty parameter
            a: Discrimination parameter
            c: Guessing parameter
        """
        exponent = -a * (theta - b)
        return c + (1 - c) / (1 + math.exp(exponent))
    
    def information(self, theta, b, a=DEFAULT_DISCRIMINATION, c=DEFAULT_GUESSING):
        """
        Calculate Fisher Information for an item at given ability level
        
        Higher information = item is more informative at this ability level
        """
        p = self.probability_correct(theta, b, a, c)
        q = 1 - p
        
        # Avoid division by zero
        if p <= c or p >= 1:
            return 0.0
            
        numerator = (a ** 2) * ((p - c) ** 2) * q
        denominator = ((1 - c) ** 2) * p
        
        return numerator / denominator if denominator > 0 else 0.0
    
    def estimate_ability(self):
        """
        Estimate ability using Maximum Likelihood Estimation (MLE)
        Uses Newton-Raphson method
        """
        if not self.responses:
            return self.ability
            
        theta = self.ability
        
        # Newton-Raphson iterations
        for _ in range(20):  # Max iterations
            numerator = 0
            denominator = 0
            
            for difficulty, is_correct in self.responses:
                b = difficulty
                a = DEFAULT_DISCRIMINATION
                c = DEFAULT_GUESSING
                
                p = self.probability_correct(theta, b, a, c)
                q = 1 - p
                
                # First derivative
                w = a * (p - c) / (1 - c)
                if is_correct:
                    numerator += w * (1 - p) / p if p > 0 else 0
                else:
                    numerator -= w * p / q if q > 0 else 0
                
                # Second derivative (for denominator)
                info = self.information(theta, b, a, c)
                denominator += info
            
            if abs(denominator) < 0.0001:
                break
                
            delta = numerator / denominator
            theta += delta
            
            # Clamp theta to reasonable bounds
            theta = max(-4, min(4, theta))
            
            if abs(delta) < 0.001:
                break
        
        self.ability = theta
        self.ability_history.append(theta)
        return theta
    
    def calculate_se(self):
        """
        Calculate Standard Error of ability estimate
        SE = 1 / sqrt(sum of information)
        """
        if not self.responses:
            return 1.0
            
        total_info = sum(
            self.information(self.ability, diff)
            for diff, _ in self.responses
        )
        
        se = 1 / math.sqrt(total_info) if total_info > 0 else 1.0
        self.se_history.append(se)
        return se
    
    def select_next_item(self, available_items):
        """
        Select the next item using Maximum Information criterion
        
        Args:
            available_items: List of dicts with 'id' and 'difficulty' keys
            
        Returns:
            The item dict with maximum information at current ability
        """
        if not available_items:
            return None
            
        best_item = None
        max_info = -1
        
        for item in available_items:
            diff = item.get('difficulty', 'B1')
            b = DIFFICULTY_MAP.get(diff, 0.0)
            info = self.information(self.ability, b)
            
            # Add small random noise to break ties
            info += random.uniform(0, 0.01)
            
            if info > max_info:
                max_info = info
                best_item = item
        
        return best_item
    
    def record_response(self, difficulty, is_correct):
        """
        Record a response and update ability estimate
        
        Args:
            difficulty: CEFR level string (A1-C2) or numeric difficulty
            is_correct: Boolean indicating if answer was correct
        """
        if isinstance(difficulty, str):
            b = DIFFICULTY_MAP.get(difficulty, 0.0)
        else:
            b = float(difficulty)
            
        self.responses.append((b, is_correct))
        self.estimate_ability()
        return self.calculate_se()
    
    def should_stop(self):
        """
        Check if test should be terminated
        
        Returns:
            (should_stop, reason) tuple
        """
        n = len(self.responses)
        
        # Check minimum questions
        if n < self.min_questions:
            return False, "minimum_not_reached"
        
        # Check maximum questions
        if n >= self.max_questions:
            return True, "max_questions_reached"
        
        # Check SE threshold
        se = self.calculate_se()
        if se <= self.se_threshold:
            return True, "precision_reached"
        
        return False, "continue"
    
    def get_cefr_level(self):
        """
        Convert ability estimate to CEFR level
        """
        theta = self.ability
        
        if theta < -1.5:
            return 'A1'
        elif theta < -0.5:
            return 'A2'
        elif theta < 0.5:
            return 'B1'
        elif theta < 1.5:
            return 'B2'
        elif theta < 2.5:
            return 'C1'
        else:
            return 'C2'
    
    def get_score_percentage(self):
        """
        Convert ability to approximate percentage score
        """
        theta = self.ability
        # Map theta (-4, 4) to percentage (0, 100)
        percentage = (theta + 4) / 8 * 100
        return max(0, min(100, percentage))
    
    def get_summary(self):
        """
        Get a summary of the CAT session
        """
        if not self.responses:
            return {
                'total_questions': 0,
                'correct_answers': 0,
                'ability': self.ability,
                'cefr_level': self.get_cefr_level(),
                'score_percentage': 50,
                'standard_error': 1.0
            }
            
        return {
            'total_questions': len(self.responses),
            'correct_answers': sum(1 for _, correct in self.responses if correct),
            'ability': round(self.ability, 3),
            'cefr_level': self.get_cefr_level(),
            'score_percentage': round(self.get_score_percentage(), 1),
            'standard_error': round(self.calculate_se(), 3),
            'ability_history': [round(a, 3) for a in self.ability_history]
        }


# ══════════════════════════════════════════════════════════════
# Helper functions for Flask integration
# ══════════════════════════════════════════════════════════════

def create_cat_session(initial_level='B1'):
    """Create a new CAT session with initial ability based on CEFR level"""
    initial_ability = DIFFICULTY_MAP.get(initial_level, 0.0)
    return CATEngine(initial_ability=initial_ability)

def difficulty_to_cefr(difficulty_value):
    """Convert numeric difficulty to CEFR level"""
    if difficulty_value < -1.5:
        return 'A1'
    elif difficulty_value < -0.5:
        return 'A2'
    elif difficulty_value < 0.5:
        return 'B1'
    elif difficulty_value < 1.5:
        return 'B2'
    elif difficulty_value < 2.5:
        return 'C1'
    else:
        return 'C2'

def cefr_to_band(cefr_level):
    """Convert CEFR level to IELTS-style band score"""
    band_map = {
        'A1': 2.5,
        'A2': 3.5,
        'B1': 5.0,
        'B2': 6.5,
        'C1': 7.5,
        'C2': 9.0
    }
    return band_map.get(cefr_level, 5.0)

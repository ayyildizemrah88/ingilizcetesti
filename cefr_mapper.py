# -*- coding: utf-8 -*-
"""
══════════════════════════════════════════════════════════════
CEFR MAPPER - Common European Framework of Reference for Languages
══════════════════════════════════════════════════════════════
Maps scores to CEFR levels with skill-specific can-do statements
"""

# ══════════════════════════════════════════════════════════════
# CEFR LEVEL THRESHOLDS
# ══════════════════════════════════════════════════════════════

CEFR_THRESHOLDS = {
    'A1': (0, 19),
    'A2': (20, 39),
    'B1': (40, 59),
    'B2': (60, 74),
    'C1': (75, 89),
    'C2': (90, 100)
}

# ══════════════════════════════════════════════════════════════
# CAN-DO STATEMENTS (Council of Europe official descriptors)
# ══════════════════════════════════════════════════════════════

CAN_DO_STATEMENTS = {
    'A1': {
        'general': 'Basic User - Beginner',
        'reading': 'Can understand familiar names, words and very simple sentences.',
        'listening': 'Can recognise familiar words and basic phrases when spoken slowly and clearly.',
        'writing': 'Can write a short, simple postcard and fill in forms with personal details.',
        'speaking': 'Can interact in a simple way provided the other person repeats slowly.',
        'grammar': 'Can use basic sentence patterns with memorised phrases.',
        'vocabulary': 'Has a basic vocabulary repertoire of isolated words and phrases.'
    },
    'A2': {
        'general': 'Basic User - Elementary',
        'reading': 'Can read very short, simple texts and find specific information in simple everyday material.',
        'listening': 'Can understand phrases and high frequency vocabulary related to immediate personal relevance.',
        'writing': 'Can write short, simple notes and messages relating to matters of immediate need.',
        'speaking': 'Can communicate in simple and routine tasks requiring a direct exchange of information.',
        'grammar': 'Can use some simple structures correctly but still makes basic mistakes.',
        'vocabulary': 'Has sufficient vocabulary for basic communication needs.'
    },
    'B1': {
        'general': 'Independent User - Intermediate',
        'reading': 'Can understand texts that consist mainly of high frequency everyday language.',
        'listening': 'Can understand main points of clear standard speech on familiar matters.',
        'writing': 'Can write simple connected text on familiar topics.',
        'speaking': 'Can deal with most situations likely to arise while travelling.',
        'grammar': 'Can use reasonably accurately a repertoire of frequently used structures.',
        'vocabulary': 'Has enough vocabulary to express most thoughts, sometimes with circumlocutions.'
    },
    'B2': {
        'general': 'Independent User - Upper Intermediate',
        'reading': 'Can read articles and reports concerned with contemporary problems.',
        'listening': 'Can understand extended speech and lectures on complex topics if reasonably familiar.',
        'writing': 'Can write clear, detailed text on a wide range of subjects related to interests.',
        'speaking': 'Can interact with fluency and spontaneity making regular interaction possible.',
        'grammar': 'Shows good grammatical control; occasional slips do not lead to misunderstanding.',
        'vocabulary': 'Has good range of vocabulary for matters connected to field and most general topics.'
    },
    'C1': {
        'general': 'Proficient User - Advanced',
        'reading': 'Can understand long and complex factual and literary texts, appreciating distinctions of style.',
        'listening': 'Can understand extended speech even when not clearly structured.',
        'writing': 'Can express ideas fluently and spontaneously with clear, well-structured text.',
        'speaking': 'Can use language flexibly and effectively for social, academic and professional purposes.',
        'grammar': 'Consistently maintains high degree of grammatical accuracy; errors are rare.',
        'vocabulary': 'Has good command of a broad lexical repertoire including idiomatic expressions.'
    },
    'C2': {
        'general': 'Proficient User - Mastery',
        'reading': 'Can read with ease virtually all forms of written language including abstract texts.',
        'listening': 'Has no difficulty understanding any kind of spoken language, live or broadcast.',
        'writing': 'Can write smooth, fluent text in appropriate style with logical structure.',
        'speaking': 'Can express finely-shaded meanings precisely, using colloquial expressions naturally.',
        'grammar': 'Maintains consistent grammatical control of complex language.',
        'vocabulary': 'Has a very broad lexical repertoire including colloquial and idiomatic usage.'
    }
}

# ══════════════════════════════════════════════════════════════
# IELTS BAND SCORE MAPPING
# ══════════════════════════════════════════════════════════════

IELTS_BAND_MAP = {
    'A1': 2.5,
    'A2': 3.5,
    'B1': 5.0,
    'B2': 6.5,
    'C1': 7.5,
    'C2': 9.0
}

# Score to band conversion (0-100 to 0-9)
def score_to_ielts_band(score):
    """Convert percentage score to IELTS band score"""
    if score < 10:
        return 1.0
    elif score < 20:
        return 2.0
    elif score < 30:
        return 3.0
    elif score < 40:
        return 3.5
    elif score < 50:
        return 4.5
    elif score < 60:
        return 5.0
    elif score < 70:
        return 5.5
    elif score < 75:
        return 6.0
    elif score < 80:
        return 6.5
    elif score < 85:
        return 7.0
    elif score < 90:
        return 7.5
    elif score < 95:
        return 8.0
    elif score < 98:
        return 8.5
    else:
        return 9.0

# ══════════════════════════════════════════════════════════════
# CEFR MAPPING FUNCTIONS
# ══════════════════════════════════════════════════════════════

def score_to_cefr(score):
    """
    Convert percentage score to CEFR level
    
    Args:
        score: Percentage score (0-100)
        
    Returns:
        CEFR level string (A1-C2)
    """
    for level, (min_score, max_score) in CEFR_THRESHOLDS.items():
        if min_score <= score <= max_score:
            return level
    return 'A1' if score < 0 else 'C2'

def get_can_do_statement(cefr_level, skill=None):
    """
    Get can-do statement for a CEFR level
    
    Args:
        cefr_level: CEFR level string (A1-C2)
        skill: Optional skill name (reading, listening, writing, speaking, grammar, vocabulary)
        
    Returns:
        Can-do statement string or dict of all statements
    """
    if cefr_level not in CAN_DO_STATEMENTS:
        cefr_level = 'B1'  # Default
        
    if skill:
        return CAN_DO_STATEMENTS[cefr_level].get(skill, '')
    return CAN_DO_STATEMENTS[cefr_level]

def calculate_skill_levels(scores_dict):
    """
    Calculate CEFR level for each skill
    
    Args:
        scores_dict: Dict with skill names as keys and percentage scores as values
        Example: {'reading': 75, 'listening': 60, 'writing': 55, 'speaking': 80}
        
    Returns:
        Dict with skill CEFR levels and overall level
    """
    result = {}
    total_score = 0
    skill_count = 0
    
    skills = ['reading', 'listening', 'writing', 'speaking', 'grammar', 'vocabulary']
    
    for skill in skills:
        if skill in scores_dict and scores_dict[skill] is not None:
            score = scores_dict[skill]
            cefr = score_to_cefr(score)
            result[skill] = {
                'score': score,
                'cefr': cefr,
                'band': IELTS_BAND_MAP.get(cefr, 5.0),
                'can_do': get_can_do_statement(cefr, skill)
            }
            total_score += score
            skill_count += 1
    
    # Calculate overall
    if skill_count > 0:
        avg_score = total_score / skill_count
        overall_cefr = score_to_cefr(avg_score)
        result['overall'] = {
            'score': round(avg_score, 1),
            'cefr': overall_cefr,
            'band': IELTS_BAND_MAP.get(overall_cefr, 5.0),
            'description': CAN_DO_STATEMENTS.get(overall_cefr, {}).get('general', '')
        }
    
    return result

def get_radar_chart_data(skill_results):
    """
    Format skill results for Chart.js radar chart
    
    Args:
        skill_results: Dict from calculate_skill_levels()
        
    Returns:
        Dict with labels and datasets for Chart.js
    """
    labels = []
    scores = []
    
    skills_order = ['reading', 'listening', 'writing', 'speaking', 'grammar', 'vocabulary']
    skill_labels = {
        'reading': 'Reading',
        'listening': 'Listening',
        'writing': 'Writing',
        'speaking': 'Speaking',
        'grammar': 'Grammar',
        'vocabulary': 'Vocabulary'
    }
    
    for skill in skills_order:
        if skill in skill_results:
            labels.append(skill_labels[skill])
            scores.append(skill_results[skill]['score'])
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Your Score',
            'data': scores,
            'backgroundColor': 'rgba(54, 162, 235, 0.2)',
            'borderColor': 'rgb(54, 162, 235)',
            'pointBackgroundColor': 'rgb(54, 162, 235)',
            'pointBorderColor': '#fff',
            'pointHoverBackgroundColor': '#fff',
            'pointHoverBorderColor': 'rgb(54, 162, 235)'
        }]
    }

def get_cefr_color(level):
    """Get color code for CEFR level"""
    colors = {
        'A1': '#e74c3c',  # Red
        'A2': '#e67e22',  # Orange
        'B1': '#f1c40f',  # Yellow
        'B2': '#2ecc71',  # Green
        'C1': '#3498db',  # Blue
        'C2': '#9b59b6'   # Purple
    }
    return colors.get(level, '#95a5a6')

def generate_cefr_certificate_text(skill_results):
    """
    Generate certificate text based on skill results
    
    Args:
        skill_results: Dict from calculate_skill_levels()
        
    Returns:
        Formatted certificate text
    """
    if 'overall' not in skill_results:
        return "Assessment incomplete."
        
    overall = skill_results['overall']
    
    text = f"""ENGLISH PROFICIENCY CERTIFICATE

Overall CEFR Level: {overall['cefr']}
IELTS Band Equivalent: {overall['band']}
Score: {overall['score']}%

{overall['description']}

Skill Breakdown:
"""
    
    for skill in ['reading', 'listening', 'writing', 'speaking']:
        if skill in skill_results:
            data = skill_results[skill]
            text += f"\n{skill.capitalize()}: {data['cefr']} ({data['score']}%)"
            text += f"\n  • {data['can_do']}"
    
    return text

# ══════════════════════════════════════════════════════════════
# TOEFL SCORE MAPPING (for reference)
# ══════════════════════════════════════════════════════════════

TOEFL_MAP = {
    'A1': (0, 9),
    'A2': (10, 18),
    'B1': (19, 56),
    'B2': (57, 86),
    'C1': (87, 109),
    'C2': (110, 120)
}

def score_to_toefl(percentage):
    """Convert percentage score to approximate TOEFL iBT score"""
    return int(percentage * 1.2)  # Scale 0-100 to 0-120

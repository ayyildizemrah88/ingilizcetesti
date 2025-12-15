# -*- coding: utf-8 -*-
"""
Trend Analysis Utilities
Weekly/monthly performance trend calculations
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from sqlalchemy import func, extract
from app.extensions import db


class TrendAnalyzer:
    """Analyze performance trends over time."""
    
    def __init__(self):
        pass
    
    def get_exam_trends(self, company_id: int = None, days: int = 30) -> Dict:
        """
        Get exam completion trends.
        
        Args:
            company_id: Optional filter by company
            days: Number of days to analyze
        
        Returns:
            dict: Trend data with daily counts and changes
        """
        from app.models.candidate import Candidate
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        previous_start = start_date - timedelta(days=days)
        
        # Current period query
        query = db.session.query(
            func.date(Candidate.sinav_bitis).label('date'),
            func.count(Candidate.id).label('count'),
            func.avg(Candidate.toplam_puan).label('avg_score')
        ).filter(
            Candidate.durum == 'tamamlandi',
            Candidate.sinav_bitis >= start_date,
            Candidate.sinav_bitis <= end_date
        )
        
        if company_id:
            query = query.filter(Candidate.firma_id == company_id)
        
        current_data = query.group_by(func.date(Candidate.sinav_bitis)).all()
        
        # Previous period for comparison
        prev_query = db.session.query(
            func.count(Candidate.id)
        ).filter(
            Candidate.durum == 'tamamlandi',
            Candidate.sinav_bitis >= previous_start,
            Candidate.sinav_bitis < start_date
        )
        
        if company_id:
            prev_query = prev_query.filter(Candidate.firma_id == company_id)
        
        previous_count = prev_query.scalar() or 0
        current_count = sum(d.count for d in current_data)
        
        # Calculate change
        if previous_count > 0:
            change_pct = round((current_count - previous_count) / previous_count * 100, 1)
        else:
            change_pct = 100 if current_count > 0 else 0
        
        # Build daily data
        daily_data = {}
        for d in current_data:
            date_str = d.date.strftime('%Y-%m-%d') if hasattr(d.date, 'strftime') else str(d.date)
            daily_data[date_str] = {
                'count': d.count,
                'avg_score': round(d.avg_score, 1) if d.avg_score else 0
            }
        
        # Fill missing dates
        date_range = []
        current = start_date
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            if date_str not in daily_data:
                daily_data[date_str] = {'count': 0, 'avg_score': 0}
            date_range.append(date_str)
            current += timedelta(days=1)
        
        return {
            'period_days': days,
            'total_exams': current_count,
            'previous_period_exams': previous_count,
            'change_percent': change_pct,
            'trend': 'up' if change_pct > 0 else ('down' if change_pct < 0 else 'stable'),
            'daily_data': {k: daily_data[k] for k in sorted(daily_data.keys())},
            'date_range': sorted(date_range)
        }
    
    def get_score_trends(self, company_id: int = None, weeks: int = 8) -> Dict:
        """
        Get weekly score trends by skill.
        
        Args:
            company_id: Optional filter by company
            weeks: Number of weeks to analyze
        
        Returns:
            dict: Weekly score averages by skill
        """
        from app.models.candidate import Candidate
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(weeks=weeks)
        
        query = db.session.query(
            extract('year', Candidate.sinav_bitis).label('year'),
            extract('week', Candidate.sinav_bitis).label('week'),
            func.avg(Candidate.grammar_puan).label('grammar'),
            func.avg(Candidate.vocabulary_puan).label('vocabulary'),
            func.avg(Candidate.reading_puan).label('reading'),
            func.avg(Candidate.listening_puan).label('listening'),
            func.avg(Candidate.writing_puan).label('writing'),
            func.avg(Candidate.speaking_puan).label('speaking'),
            func.avg(Candidate.toplam_puan).label('overall')
        ).filter(
            Candidate.durum == 'tamamlandi',
            Candidate.sinav_bitis >= start_date
        )
        
        if company_id:
            query = query.filter(Candidate.firma_id == company_id)
        
        weekly_data = query.group_by(
            extract('year', Candidate.sinav_bitis),
            extract('week', Candidate.sinav_bitis)
        ).order_by('year', 'week').all()
        
        skills = ['grammar', 'vocabulary', 'reading', 'listening', 'writing', 'speaking', 'overall']
        
        result = {
            'weeks': [],
            'skills': {skill: [] for skill in skills}
        }
        
        for w in weekly_data:
            week_label = f"{int(w.year)}-W{int(w.week):02d}"
            result['weeks'].append(week_label)
            
            for skill in skills:
                value = getattr(w, skill)
                result['skills'][skill].append(round(value, 1) if value else 0)
        
        return result
    
    def get_cefr_distribution_trends(self, company_id: int = None, months: int = 6) -> Dict:
        """
        Get monthly CEFR level distribution trends.
        
        Args:
            company_id: Optional filter by company
            months: Number of months to analyze
        
        Returns:
            dict: Monthly CEFR distribution
        """
        from app.models.candidate import Candidate
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)
        
        query = db.session.query(
            extract('year', Candidate.sinav_bitis).label('year'),
            extract('month', Candidate.sinav_bitis).label('month'),
            Candidate.cefr_seviye,
            func.count(Candidate.id).label('count')
        ).filter(
            Candidate.durum == 'tamamlandi',
            Candidate.sinav_bitis >= start_date,
            Candidate.cefr_seviye.isnot(None)
        )
        
        if company_id:
            query = query.filter(Candidate.firma_id == company_id)
        
        monthly_data = query.group_by(
            extract('year', Candidate.sinav_bitis),
            extract('month', Candidate.sinav_bitis),
            Candidate.cefr_seviye
        ).all()
        
        # Organize data
        result = defaultdict(lambda: {'A1': 0, 'A2': 0, 'B1': 0, 'B2': 0, 'C1': 0, 'C2': 0})
        
        for m in monthly_data:
            month_label = f"{int(m.year)}-{int(m.month):02d}"
            if m.cefr_seviye in result[month_label]:
                result[month_label][m.cefr_seviye] = m.count
        
        # Sort by month
        sorted_months = sorted(result.keys())
        
        return {
            'months': sorted_months,
            'data': {month: result[month] for month in sorted_months}
        }
    
    def get_company_comparison(self, company_ids: List[int] = None, days: int = 30) -> Dict:
        """
        Compare performance across companies.
        
        Args:
            company_ids: List of company IDs to compare
            days: Number of days to analyze
        
        Returns:
            dict: Comparison metrics
        """
        from app.models.candidate import Candidate
        from app.models.company import Company
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.session.query(
            Company.id,
            Company.ad.label('name'),
            func.count(Candidate.id).label('exam_count'),
            func.avg(Candidate.toplam_puan).label('avg_score'),
            func.avg(Candidate.grammar_puan).label('grammar'),
            func.avg(Candidate.vocabulary_puan).label('vocabulary'),
            func.avg(Candidate.reading_puan).label('reading'),
            func.avg(Candidate.listening_puan).label('listening'),
            func.avg(Candidate.writing_puan).label('writing'),
            func.avg(Candidate.speaking_puan).label('speaking')
        ).join(
            Candidate, Company.id == Candidate.firma_id
        ).filter(
            Candidate.durum == 'tamamlandi',
            Candidate.sinav_bitis >= start_date
        )
        
        if company_ids:
            query = query.filter(Company.id.in_(company_ids))
        
        companies = query.group_by(Company.id, Company.ad).all()
        
        result = []
        for c in companies:
            result.append({
                'id': c.id,
                'name': c.name,
                'exam_count': c.exam_count,
                'avg_score': round(c.avg_score, 1) if c.avg_score else 0,
                'skills': {
                    'grammar': round(c.grammar, 1) if c.grammar else 0,
                    'vocabulary': round(c.vocabulary, 1) if c.vocabulary else 0,
                    'reading': round(c.reading, 1) if c.reading else 0,
                    'listening': round(c.listening, 1) if c.listening else 0,
                    'writing': round(c.writing, 1) if c.writing else 0,
                    'speaking': round(c.speaking, 1) if c.speaking else 0
                }
            })
        
        # Sort by avg score
        result.sort(key=lambda x: x['avg_score'], reverse=True)
        
        return {
            'period_days': days,
            'companies': result
        }
    
    def get_peak_hours(self, company_id: int = None, days: int = 30) -> Dict:
        """
        Analyze peak exam hours.
        
        Args:
            company_id: Optional filter by company
            days: Number of days to analyze
        
        Returns:
            dict: Hourly distribution of exams
        """
        from app.models.candidate import Candidate
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.session.query(
            extract('hour', Candidate.sinav_baslama).label('hour'),
            func.count(Candidate.id).label('count')
        ).filter(
            Candidate.sinav_baslama >= start_date,
            Candidate.sinav_baslama.isnot(None)
        )
        
        if company_id:
            query = query.filter(Candidate.firma_id == company_id)
        
        hourly = query.group_by(extract('hour', Candidate.sinav_baslama)).all()
        
        # Fill all hours
        hours = {i: 0 for i in range(24)}
        for h in hourly:
            hours[int(h.hour)] = h.count
        
        # Find peak hour
        peak_hour = max(hours, key=hours.get) if hours else 9
        
        return {
            'hourly_data': hours,
            'peak_hour': peak_hour,
            'peak_hour_label': f"{peak_hour:02d}:00 - {(peak_hour+1) % 24:02d}:00"
        }


# Global instance
trend_analyzer = TrendAnalyzer()


def get_dashboard_trends(company_id: int = None) -> Dict:
    """
    Get all trend data for dashboard.
    
    Args:
        company_id: Optional filter by company
    
    Returns:
        dict: All trend data
    """
    return {
        'exam_trends': trend_analyzer.get_exam_trends(company_id, days=30),
        'score_trends': trend_analyzer.get_score_trends(company_id, weeks=8),
        'cefr_trends': trend_analyzer.get_cefr_distribution_trends(company_id, months=6),
        'peak_hours': trend_analyzer.get_peak_hours(company_id, days=30)
    }

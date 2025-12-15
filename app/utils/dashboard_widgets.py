# -*- coding: utf-8 -*-
"""
Dashboard Widgets
Customizable dashboard widget system
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from app.extensions import db


class DashboardWidget:
    """Represents a single dashboard widget."""
    
    WIDGET_TYPES = {
        'stats_card': {
            'name': 'İstatistik Kartı',
            'description': 'Tek bir metriği gösteren kart',
            'min_width': 1,
            'max_width': 3
        },
        'line_chart': {
            'name': 'Çizgi Grafik',
            'description': 'Zaman bazlı trend grafiği',
            'min_width': 2,
            'max_width': 4
        },
        'bar_chart': {
            'name': 'Çubuk Grafik',
            'description': 'Karşılaştırmalı çubuk grafik',
            'min_width': 2,
            'max_width': 4
        },
        'pie_chart': {
            'name': 'Pasta Grafik',
            'description': 'Dağılım pasta grafiği',
            'min_width': 2,
            'max_width': 3
        },
        'table': {
            'name': 'Tablo',
            'description': 'Veri tablosu',
            'min_width': 2,
            'max_width': 4
        },
        'recent_activity': {
            'name': 'Son Aktiviteler',
            'description': 'Son işlemler listesi',
            'min_width': 2,
            'max_width': 4
        },
        'leaderboard': {
            'name': 'Sıralama',
            'description': 'En iyi performans sıralaması',
            'min_width': 2,
            'max_width': 3
        }
    }
    
    DATA_SOURCES = {
        'exam_count': 'Toplam Sınav Sayısı',
        'completion_rate': 'Tamamlanma Oranı',
        'average_score': 'Ortalama Puan',
        'cefr_distribution': 'CEFR Dağılımı',
        'skill_averages': 'Beceri Ortalamaları',
        'daily_exams': 'Günlük Sınav Sayısı',
        'weekly_scores': 'Haftalık Puan Trendi',
        'top_performers': 'En İyi Performanslar',
        'recent_exams': 'Son Sınavlar',
        'company_credits': 'Şirket Kredileri',
        'monthly_revenue': 'Aylık Gelir'
    }
    
    def __init__(self, widget_id: str, widget_type: str, data_source: str,
                 title: str = None, width: int = 2, position: int = 0,
                 config: Dict = None):
        self.id = widget_id
        self.type = widget_type
        self.data_source = data_source
        self.title = title or self.DATA_SOURCES.get(data_source, 'Widget')
        self.width = width
        self.position = position
        self.config = config or {}
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'type': self.type,
            'data_source': self.data_source,
            'title': self.title,
            'width': self.width,
            'position': self.position,
            'config': self.config
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DashboardWidget':
        return cls(
            widget_id=data.get('id'),
            widget_type=data.get('type'),
            data_source=data.get('data_source'),
            title=data.get('title'),
            width=data.get('width', 2),
            position=data.get('position', 0),
            config=data.get('config', {})
        )


class DashboardConfig(db.Model):
    """Store dashboard configurations per user/role."""
    
    __tablename__ = 'dashboard_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    role = db.Column(db.String(50), nullable=True)  # superadmin, customer
    
    name = db.Column(db.String(100), default='Varsayılan Dashboard')
    widgets = db.Column(db.Text, default='[]')  # JSON array of widgets
    is_default = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_widgets(self) -> List[DashboardWidget]:
        """Get widgets as objects."""
        try:
            data = json.loads(self.widgets or '[]')
            return [DashboardWidget.from_dict(w) for w in data]
        except:
            return []
    
    def set_widgets(self, widgets: List[DashboardWidget]):
        """Set widgets from objects."""
        self.widgets = json.dumps([w.to_dict() for w in widgets])
    
    @classmethod
    def get_default_for_role(cls, role: str) -> 'DashboardConfig':
        """Get or create default dashboard for a role."""
        config = cls.query.filter_by(role=role, is_default=True).first()
        
        if not config:
            config = cls.create_default(role)
        
        return config
    
    @classmethod
    def create_default(cls, role: str) -> 'DashboardConfig':
        """Create default dashboard configuration for a role."""
        if role == 'superadmin':
            widgets = [
                DashboardWidget('w1', 'stats_card', 'exam_count', 'Toplam Sınav', 1, 0),
                DashboardWidget('w2', 'stats_card', 'completion_rate', 'Tamamlanma Oranı', 1, 1),
                DashboardWidget('w3', 'stats_card', 'average_score', 'Ortalama Puan', 1, 2),
                DashboardWidget('w4', 'stats_card', 'company_credits', 'Aktif Şirketler', 1, 3),
                DashboardWidget('w5', 'line_chart', 'daily_exams', 'Günlük Sınav Trendi', 2, 4),
                DashboardWidget('w6', 'pie_chart', 'cefr_distribution', 'CEFR Dağılımı', 2, 5),
                DashboardWidget('w7', 'bar_chart', 'skill_averages', 'Beceri Ortalamaları', 2, 6),
                DashboardWidget('w8', 'table', 'recent_exams', 'Son Sınavlar', 2, 7),
                DashboardWidget('w9', 'leaderboard', 'top_performers', 'En İyi Performanslar', 2, 8),
                DashboardWidget('w10', 'line_chart', 'monthly_revenue', 'Aylık Gelir Trendi', 2, 9),
            ]
        else:  # customer
            widgets = [
                DashboardWidget('w1', 'stats_card', 'exam_count', 'Sınav Sayısı', 1, 0),
                DashboardWidget('w2', 'stats_card', 'completion_rate', 'Tamamlanma', 1, 1),
                DashboardWidget('w3', 'stats_card', 'average_score', 'Ortalama', 1, 2),
                DashboardWidget('w4', 'stats_card', 'company_credits', 'Kalan Kredi', 1, 3),
                DashboardWidget('w5', 'line_chart', 'weekly_scores', 'Haftalık Trend', 2, 4),
                DashboardWidget('w6', 'pie_chart', 'cefr_distribution', 'CEFR Dağılımı', 2, 5),
                DashboardWidget('w7', 'table', 'recent_exams', 'Son Sınavlar', 4, 6),
            ]
        
        config = cls(
            role=role,
            name=f"{role.title()} Varsayılan Dashboard",
            is_default=True
        )
        config.set_widgets(widgets)
        
        db.session.add(config)
        db.session.commit()
        
        return config


class DashboardDataProvider:
    """Provide data for dashboard widgets."""
    
    def __init__(self, company_id: int = None):
        self.company_id = company_id
    
    def get_widget_data(self, data_source: str, config: Dict = None) -> Any:
        """
        Get data for a specific widget.
        
        Args:
            data_source: Data source identifier
            config: Optional widget configuration
        
        Returns:
            Widget data
        """
        method_map = {
            'exam_count': self._get_exam_count,
            'completion_rate': self._get_completion_rate,
            'average_score': self._get_average_score,
            'cefr_distribution': self._get_cefr_distribution,
            'skill_averages': self._get_skill_averages,
            'daily_exams': self._get_daily_exams,
            'weekly_scores': self._get_weekly_scores,
            'top_performers': self._get_top_performers,
            'recent_exams': self._get_recent_exams,
            'company_credits': self._get_company_credits,
            'monthly_revenue': self._get_monthly_revenue
        }
        
        method = method_map.get(data_source)
        if method:
            return method(config or {})
        
        return None
    
    def _get_exam_count(self, config: Dict) -> Dict:
        from app.models.candidate import Candidate
        
        query = Candidate.query.filter(Candidate.durum == 'tamamlandi')
        if self.company_id:
            query = query.filter(Candidate.firma_id == self.company_id)
        
        total = query.count()
        
        # Compare with last month
        last_month = datetime.utcnow() - timedelta(days=30)
        this_month_count = query.filter(Candidate.sinav_bitis >= last_month).count()
        
        return {
            'value': total,
            'change': this_month_count,
            'change_label': 'bu ay',
            'icon': '📊'
        }
    
    def _get_completion_rate(self, config: Dict) -> Dict:
        from app.models.candidate import Candidate
        
        query = Candidate.query
        if self.company_id:
            query = query.filter(Candidate.firma_id == self.company_id)
        
        total = query.count()
        completed = query.filter(Candidate.durum == 'tamamlandi').count()
        
        rate = round(completed / total * 100, 1) if total > 0 else 0
        
        return {
            'value': f'{rate}%',
            'completed': completed,
            'total': total,
            'icon': '✅'
        }
    
    def _get_average_score(self, config: Dict) -> Dict:
        from app.models.candidate import Candidate
        from sqlalchemy import func
        
        query = db.session.query(func.avg(Candidate.toplam_puan)).filter(
            Candidate.durum == 'tamamlandi',
            Candidate.toplam_puan.isnot(None)
        )
        
        if self.company_id:
            query = query.filter(Candidate.firma_id == self.company_id)
        
        avg = query.scalar() or 0
        
        return {
            'value': round(avg, 1),
            'suffix': '%',
            'icon': '📈'
        }
    
    def _get_cefr_distribution(self, config: Dict) -> Dict:
        from app.models.candidate import Candidate
        from sqlalchemy import func
        
        query = db.session.query(
            Candidate.cefr_seviye,
            func.count(Candidate.id)
        ).filter(
            Candidate.durum == 'tamamlandi',
            Candidate.cefr_seviye.isnot(None)
        )
        
        if self.company_id:
            query = query.filter(Candidate.firma_id == self.company_id)
        
        distribution = query.group_by(Candidate.cefr_seviye).all()
        
        levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        data = {level: 0 for level in levels}
        
        for level, count in distribution:
            if level in data:
                data[level] = count
        
        return {
            'labels': levels,
            'values': [data[level] for level in levels],
            'colors': ['#dc3545', '#fd7e14', '#ffc107', '#28a745', '#20c997', '#6f42c1']
        }
    
    def _get_skill_averages(self, config: Dict) -> Dict:
        from app.models.candidate import Candidate
        from sqlalchemy import func
        
        query = db.session.query(
            func.avg(Candidate.grammar_puan),
            func.avg(Candidate.vocabulary_puan),
            func.avg(Candidate.reading_puan),
            func.avg(Candidate.listening_puan),
            func.avg(Candidate.writing_puan),
            func.avg(Candidate.speaking_puan)
        ).filter(Candidate.durum == 'tamamlandi')
        
        if self.company_id:
            query = query.filter(Candidate.firma_id == self.company_id)
        
        result = query.first()
        
        skills = ['Grammar', 'Vocabulary', 'Reading', 'Listening', 'Writing', 'Speaking']
        values = [round(v or 0, 1) for v in result]
        
        return {
            'labels': skills,
            'values': values
        }
    
    def _get_daily_exams(self, config: Dict) -> Dict:
        from app.utils.trend_analysis import trend_analyzer
        
        trends = trend_analyzer.get_exam_trends(self.company_id, days=30)
        
        return {
            'labels': trends['date_range'][-14:],  # Last 14 days
            'values': [trends['daily_data'].get(d, {}).get('count', 0) for d in trends['date_range'][-14:]]
        }
    
    def _get_weekly_scores(self, config: Dict) -> Dict:
        from app.utils.trend_analysis import trend_analyzer
        
        trends = trend_analyzer.get_score_trends(self.company_id, weeks=8)
        
        return {
            'labels': trends['weeks'],
            'datasets': [
                {'label': 'Genel', 'values': trends['skills']['overall']},
                {'label': 'Grammar', 'values': trends['skills']['grammar']},
                {'label': 'Reading', 'values': trends['skills']['reading']}
            ]
        }
    
    def _get_top_performers(self, config: Dict) -> List[Dict]:
        from app.models.candidate import Candidate
        
        query = Candidate.query.filter(
            Candidate.durum == 'tamamlandi',
            Candidate.toplam_puan.isnot(None)
        ).order_by(Candidate.toplam_puan.desc()).limit(10)
        
        if self.company_id:
            query = query.filter(Candidate.firma_id == self.company_id)
        
        performers = query.all()
        
        return [
            {
                'name': c.ad_soyad,
                'score': c.toplam_puan,
                'level': c.cefr_seviye,
                'date': c.sinav_bitis.strftime('%d.%m.%Y') if c.sinav_bitis else ''
            }
            for c in performers
        ]
    
    def _get_recent_exams(self, config: Dict) -> List[Dict]:
        from app.models.candidate import Candidate
        
        query = Candidate.query.filter(
            Candidate.durum == 'tamamlandi'
        ).order_by(Candidate.sinav_bitis.desc()).limit(10)
        
        if self.company_id:
            query = query.filter(Candidate.firma_id == self.company_id)
        
        exams = query.all()
        
        return [
            {
                'name': c.ad_soyad,
                'email': c.email,
                'score': c.toplam_puan,
                'level': c.cefr_seviye,
                'date': c.sinav_bitis.strftime('%d.%m.%Y %H:%M') if c.sinav_bitis else ''
            }
            for c in exams
        ]
    
    def _get_company_credits(self, config: Dict) -> Dict:
        if self.company_id:
            from app.models.company import Company
            company = Company.query.get(self.company_id)
            return {
                'value': company.kredi if company else 0,
                'icon': '💳'
            }
        else:
            from app.models.company import Company
            total = db.session.query(db.func.sum(Company.kredi)).scalar() or 0
            active = Company.query.filter(Company.aktif == True).count()
            return {
                'value': active,
                'label': 'Aktif Şirket',
                'total_credits': total,
                'icon': '🏢'
            }
    
    def _get_monthly_revenue(self, config: Dict) -> Dict:
        # Placeholder - implement based on your billing model
        months = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz']
        values = [12500, 15200, 18100, 22300, 19800, 25400]
        
        return {
            'labels': months,
            'values': values,
            'currency': '₺'
        }


def get_dashboard_data(user_id: int = None, role: str = None, company_id: int = None) -> Dict:
    """
    Get complete dashboard data.
    
    Args:
        user_id: Optional user ID for personalized dashboard
        role: User role (superadmin, customer)
        company_id: Optional company filter
    
    Returns:
        dict: Complete dashboard data
    """
    # Get dashboard config
    config = DashboardConfig.get_default_for_role(role or 'customer')
    widgets = config.get_widgets()
    
    # Get data for each widget
    provider = DashboardDataProvider(company_id)
    
    widget_data = {}
    for widget in widgets:
        widget_data[widget.id] = {
            **widget.to_dict(),
            'data': provider.get_widget_data(widget.data_source, widget.config)
        }
    
    return {
        'config': {
            'id': config.id,
            'name': config.name
        },
        'widgets': widget_data,
        'widget_types': DashboardWidget.WIDGET_TYPES,
        'data_sources': DashboardWidget.DATA_SOURCES
    }

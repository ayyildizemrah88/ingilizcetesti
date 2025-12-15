# -*- coding: utf-8 -*-
"""
Audit Log Model
Tracks all admin and sensitive operations for compliance
"""
from datetime import datetime
from app.extensions import db
import json


class AuditLog(db.Model):
    """
    Immutable audit log for tracking admin actions.
    
    Logs:
    - Who did what
    - When it happened
    - What data changed (before/after)
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Who
    user_id = db.Column(db.Integer, index=True)
    user_email = db.Column(db.String(255))
    user_role = db.Column(db.String(50))  # admin, superadmin, etc.
    
    # What
    action = db.Column(db.String(50))  # create, update, delete, login, etc.
    table_name = db.Column(db.String(100))
    record_id = db.Column(db.Integer)
    
    # Details
    old_values = db.Column(db.Text)  # JSON of previous values
    new_values = db.Column(db.Text)  # JSON of new values
    description = db.Column(db.String(500))
    
    # Context
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    endpoint = db.Column(db.String(200))
    
    # When
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.action} {self.table_name}:{self.record_id}>'
    
    @property
    def old_data(self):
        """Parse old values from JSON."""
        if self.old_values:
            return json.loads(self.old_values)
        return {}
    
    @property
    def new_data(self):
        """Parse new values from JSON."""
        if self.new_values:
            return json.loads(self.new_values)
        return {}
    
    @classmethod
    def log(cls, user_id: int, user_email: str, action: str,
            table_name: str = None, record_id: int = None,
            old_values: dict = None, new_values: dict = None,
            description: str = None, ip_address: str = None,
            user_agent: str = None, endpoint: str = None,
            user_role: str = None):
        """
        Create an audit log entry.
        
        Args:
            user_id: ID of user performing action
            user_email: Email of user
            action: Action type (create, update, delete, login, etc.)
            table_name: Database table affected
            record_id: ID of affected record
            old_values: Previous values (for updates)
            new_values: New values
            description: Human-readable description
            ip_address: Client IP
            user_agent: Client browser info
            endpoint: API endpoint called
            user_role: User's role
            
        Returns:
            AuditLog instance
        """
        log = cls(
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint
        )
        db.session.add(log)
        return log
    
    @classmethod
    def log_login(cls, user_id: int, user_email: str, success: bool,
                  ip_address: str = None, user_agent: str = None):
        """Log login attempt."""
        return cls.log(
            user_id=user_id,
            user_email=user_email,
            action='login_success' if success else 'login_failed',
            description=f"Login {'successful' if success else 'failed'} for {user_email}",
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @classmethod
    def log_data_export(cls, user_id: int, user_email: str,
                       exported_table: str, record_count: int,
                       ip_address: str = None):
        """Log data export (KVKK requirement)."""
        return cls.log(
            user_id=user_id,
            user_email=user_email,
            action='data_export',
            table_name=exported_table,
            description=f"Exported {record_count} records from {exported_table}",
            ip_address=ip_address
        )
    
    @classmethod
    def log_data_deletion(cls, user_id: int, user_email: str,
                         table_name: str, record_id: int,
                         description: str = None, ip_address: str = None):
        """Log data deletion (KVKK requirement)."""
        return cls.log(
            user_id=user_id,
            user_email=user_email,
            action='delete',
            table_name=table_name,
            record_id=record_id,
            description=description or f"Deleted record from {table_name}",
            ip_address=ip_address
        )


def audit_action(action: str, table_name: str = None, get_record_id=None):
    """
    Decorator to automatically log admin actions.
    
    Usage:
        @audit_action('update', 'candidates')
        def update_candidate(candidate_id):
            ...
    """
    from functools import wraps
    from flask import request, g
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get user info from session/g
            user_id = getattr(g, 'user_id', None)
            user_email = getattr(g, 'user_email', None)
            user_role = getattr(g, 'user_role', None)
            
            # Get record ID if provided
            record_id = None
            if get_record_id:
                record_id = get_record_id(*args, **kwargs)
            elif 'id' in kwargs:
                record_id = kwargs['id']
            elif args:
                record_id = args[0] if isinstance(args[0], int) else None
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Log the action
            try:
                AuditLog.log(
                    user_id=user_id,
                    user_email=user_email,
                    user_role=user_role,
                    action=action,
                    table_name=table_name,
                    record_id=record_id,
                    ip_address=request.remote_addr if request else None,
                    user_agent=request.user_agent.string if request else None,
                    endpoint=request.endpoint if request else None
                )
                db.session.commit()
            except Exception:
                pass  # Don't fail the main operation
            
            return result
        return wrapper
    return decorator

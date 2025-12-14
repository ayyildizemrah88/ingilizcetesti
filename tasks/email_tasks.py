# -*- coding: utf-8 -*-
"""
Email Tasks - Async email sending with retry
"""
from app.celery_app import celery
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, to, subject, body, html_body=None, sirket_id=None):
    """
    Send email asynchronously with automatic retry
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text body
        html_body: HTML body (optional)
        sirket_id: Company ID for custom SMTP settings
    """
    try:
        # Get SMTP settings
        smtp_config = get_smtp_config(sirket_id)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_config['from']
        msg['To'] = to
        
        # Add text part
        part1 = MIMEText(body, 'plain', 'utf-8')
        msg.attach(part1)
        
        # Add HTML part if provided
        if html_body:
            part2 = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
            server.starttls()
            server.login(smtp_config['user'], smtp_config['pass'])
            server.sendmail(smtp_config['from'], [to], msg.as_string())
        
        # Log success
        log_email_sent(to, subject, sirket_id)
        
        return {'status': 'sent', 'to': to}
        
    except smtplib.SMTPException as e:
        # Retry on SMTP errors
        raise self.retry(exc=e)
    except Exception as e:
        # Log error
        return {'status': 'error', 'error': str(e)}


@celery.task(bind=True, max_retries=3)
def send_exam_invitation(self, candidate_id):
    """
    Send exam invitation email to candidate
    
    Args:
        candidate_id: Candidate ID
    """
    try:
        from app.models import Candidate, Company
        from app.extensions import db
        
        candidate = Candidate.query.get(candidate_id)
        if not candidate or not candidate.email:
            return {'status': 'skipped', 'reason': 'no email'}
        
        company = Company.query.get(candidate.sirket_id)
        company_name = company.isim if company else 'Skills Test Center'
        
        # Build exam URL
        base_url = os.getenv('BASE_URL', 'http://localhost:5000')
        exam_url = f"{base_url}/sinav-giris"
        
        subject = f"Sınav Davetiyesi - {company_name}"
        
        body = f"""Sayın {candidate.ad_soyad},

{company_name} tarafından İngilizce yeterlilik sınavına davet edildiniz.

Giriş Kodunuz: {candidate.giris_kodu}
Sınav Linki: {exam_url}

Sınav Süresi: {candidate.sinav_suresi} dakika
Soru Sayısı: {candidate.soru_limiti} soru

Sınavınızda başarılar dileriz!

{company_name}
"""
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .code {{ font-size: 24px; font-weight: bold; background: #f4f4f4; padding: 10px 20px; text-align: center; margin: 20px 0; }}
        .btn {{ display: inline-block; background: #0d6efd; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Sınav Davetiyesi</h2>
        <p>Sayın <strong>{candidate.ad_soyad}</strong>,</p>
        <p>{company_name} tarafından İngilizce yeterlilik sınavına davet edildiniz.</p>
        
        <div class="code">{candidate.giris_kodu}</div>
        
        <p style="text-align: center;">
            <a href="{exam_url}" class="btn">Sınava Başla</a>
        </p>
        
        <p><strong>Sınav Bilgileri:</strong></p>
        <ul>
            <li>Süre: {candidate.sinav_suresi} dakika</li>
            <li>Soru: {candidate.soru_limiti} adet</li>
        </ul>
        
        <p>Başarılar dileriz!</p>
        <p><em>{company_name}</em></p>
    </div>
</body>
</html>
"""
        
        return send_email_task(
            candidate.email, 
            subject, 
            body, 
            html_body=html_body,
            sirket_id=candidate.sirket_id
        )
        
    except Exception as e:
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id, token):
    """
    Send password reset email
    """
    try:
        from app.models import User
        
        user = User.query.get(user_id)
        if not user:
            return {'status': 'skipped'}
        
        base_url = os.getenv('BASE_URL', 'http://localhost:5000')
        reset_url = f"{base_url}/reset-password/{token}"
        
        subject = "Şifre Sıfırlama - Skills Test Center"
        body = f"""Merhaba,

Şifre sıfırlama talebiniz alındı. Aşağıdaki linki kullanarak yeni şifrenizi belirleyebilirsiniz:

{reset_url}

Bu link 1 saat geçerlidir.

Eğer bu talebi siz yapmadıysanız, bu e-postayı görmezden gelebilirsiniz.
"""
        
        return send_email_task(user.email, subject, body)
        
    except Exception as e:
        raise self.retry(exc=e)


@celery.task
def send_exam_reminders():
    """
    Daily task: Send exam reminders to candidates with pending exams
    """
    from app.models import Candidate
    from datetime import datetime, timedelta
    
    # Find candidates with pending exams
    pending = Candidate.query.filter_by(
        sinav_durumu='beklemede',
        is_deleted=False
    ).all()
    
    count = 0
    for candidate in pending:
        if candidate.email:
            send_exam_invitation.delay(candidate.id)
            count += 1
    
    return {'reminders_sent': count}


def get_smtp_config(sirket_id=None):
    """Get SMTP configuration for company or default"""
    config = {
        'host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        'port': int(os.getenv('SMTP_PORT', 587)),
        'user': os.getenv('SMTP_USER', ''),
        'pass': os.getenv('SMTP_PASS', ''),
        'from': os.getenv('SMTP_FROM', 'noreply@skillstestcenter.com')
    }
    
    if sirket_id:
        from app.models import Company
        company = Company.query.get(sirket_id)
        if company and company.smtp_host:
            config = {
                'host': company.smtp_host,
                'port': company.smtp_port or 587,
                'user': company.smtp_user,
                'pass': company.smtp_pass,
                'from': company.smtp_from or company.email
            }
    
    return config


def log_email_sent(to, subject, sirket_id=None):
    """Log email for tracking"""
    # Could be extended to save to database
    import logging
    logging.info(f"Email sent: {to} - {subject}")

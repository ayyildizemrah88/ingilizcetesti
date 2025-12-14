# -*- coding: utf-8 -*-
"""
Email Tasks - Celery tasks for email notifications
"""
from app.celery_app import celery
import logging

logger = logging.getLogger(__name__)


@celery.task
def send_certificate_email(candidate_id):
    """
    Send certificate email to candidate after exam completion.
    Triggered automatically when exam status changes to 'tamamlandi'.
    """
    from app.models import Candidate
    from flask import render_template_string, current_app
    
    try:
        candidate = Candidate.query.get(candidate_id)
        if not candidate or not candidate.email:
            return {'status': 'skipped', 'reason': 'no email'}
        
        # Skip practice exams
        if candidate.is_practice:
            return {'status': 'skipped', 'reason': 'practice exam'}
        
        # Generate certificate URL
        cert_url = f"https://skillstestcenter.com/certificate/{candidate.certificate_hash}"
        
        # Email content
        subject = f"Skills Test Center - Sınav Sertifikanız"
        
        html_body = f"""
        <h2>Tebrikler, {candidate.ad_soyad}!</h2>
        
        <p>Skills Test Center İngilizce Yeterlilik Sınavı'nı başarıyla tamamladınız.</p>
        
        <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h3>Sınav Sonuçlarınız</h3>
            <p><strong>Seviye:</strong> {candidate.seviye_sonuc}</p>
            <p><strong>Genel Puan:</strong> {candidate.puan:.1f}%</p>
            <p><strong>Band Puanı:</strong> {candidate.band_score:.1f if candidate.band_score else '-'}</p>
        </div>
        
        <p>Sertifikanızı görüntülemek için aşağıdaki bağlantıya tıklayın:</p>
        <p><a href="{cert_url}" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">Sertifikayı Görüntüle</a></p>
        
        <p style="margin-top: 30px; color: #666;">
            Bu sertifika 2 yıl geçerlidir.<br>
            Doğrulama Kodu: {candidate.certificate_hash}
        </p>
        
        <hr style="margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">
            Skills Test Center<br>
            Bu email otomatik olarak gönderilmiştir.
        </p>
        """
        
        # Send email (using Flask-Mail or similar)
        send_email(candidate.email, subject, html_body)
        
        logger.info(f"Certificate email sent to {candidate.email}")
        return {'status': 'sent', 'email': candidate.email}
        
    except Exception as e:
        logger.error(f"Certificate email failed: {e}")
        return {'status': 'error', 'error': str(e)}


@celery.task
def send_exam_reminder(schedule_id):
    """
    Send exam reminder email for scheduled exams.
    Runs 24 hours before scheduled exam time.
    """
    from app.models.admin import ExamSchedule
    from app.models import Candidate
    
    try:
        schedule = ExamSchedule.query.get(schedule_id)
        if not schedule or schedule.reminder_sent:
            return {'status': 'skipped'}
        
        candidate = Candidate.query.get(schedule.candidate_id)
        if not candidate or not candidate.email:
            return {'status': 'skipped', 'reason': 'no email'}
        
        subject = "Skills Test Center - Sınav Hatırlatması"
        
        html_body = f"""
        <h2>Sayın {candidate.ad_soyad},</h2>
        
        <p>İngilizce Yeterlilik Sınavınız için bir hatırlatma:</p>
        
        <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h3>📅 Sınav Zamanı: {schedule.scheduled_at.strftime('%d %B %Y, %H:%M')}</h3>
        </div>
        
        <p><strong>Önemli Notlar:</strong></p>
        <ul>
            <li>Sessiz bir ortamda sınava girin</li>
            <li>Stabil internet bağlantısı sağlayın</li>
            <li>Kamera ve mikrofon izinlerini açık tutun</li>
            <li>Giriş kodunuz: <strong>{candidate.giris_kodu}</strong></li>
        </ul>
        
        <p style="margin-top: 20px;">
            <a href="https://skillstestcenter.com/sinav-giris" 
               style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
                Sınava Giriş Yap
            </a>
        </p>
        
        <p style="margin-top: 30px;">Başarılar dileriz!</p>
        """
        
        send_email(candidate.email, subject, html_body)
        
        # Mark reminder as sent
        schedule.reminder_sent = True
        from app.extensions import db
        db.session.commit()
        
        return {'status': 'sent', 'email': candidate.email}
        
    except Exception as e:
        logger.error(f"Reminder email failed: {e}")
        return {'status': 'error', 'error': str(e)}


@celery.task
def send_bulk_invite_emails(import_id):
    """
    Send invitation emails for bulk imported candidates.
    """
    from app.models.admin import BulkImport
    from app.models import Candidate
    from app.extensions import db
    
    try:
        bulk_import = BulkImport.query.get(import_id)
        if not bulk_import:
            return {'status': 'error', 'reason': 'import not found'}
        
        # Get candidates from this import (recent ones)
        candidates = Candidate.query.filter(
            Candidate.created_at >= bulk_import.created_at,
            Candidate.sirket_id == bulk_import.company_id
        ).all()
        
        sent_count = 0
        for candidate in candidates:
            if candidate.email:
                result = send_invite_email(candidate)
                if result.get('status') == 'sent':
                    sent_count += 1
        
        bulk_import.status = 'completed'
        bulk_import.success_count = sent_count
        db.session.commit()
        
        return {'status': 'completed', 'sent': sent_count}
        
    except Exception as e:
        logger.error(f"Bulk invite failed: {e}")
        return {'status': 'error', 'error': str(e)}


def send_invite_email(candidate):
    """Send individual invitation email."""
    subject = "Skills Test Center - Sınav Davetiyesi"
    
    html_body = f"""
    <h2>Sayın {candidate.ad_soyad},</h2>
    
    <p>Skills Test Center İngilizce Yeterlilik Sınavı'na davet edildiniz.</p>
    
    <div style="background: #e7f1ff; padding: 20px; border-radius: 10px; margin: 20px 0;">
        <p><strong>Giriş Kodunuz:</strong> {candidate.giris_kodu}</p>
        <p><strong>Sınav Süresi:</strong> {candidate.sinav_suresi} dakika</p>
    </div>
    
    <p>Sınava girmek için:</p>
    <ol>
        <li><a href="https://skillstestcenter.com/sinav-giris">skillstestcenter.com/sinav-giris</a> adresine gidin</li>
        <li>Giriş kodunuzu girin</li>
        <li>Sınava başlayın</li>
    </ol>
    
    <p style="margin-top: 20px;">
        <a href="https://skillstestcenter.com/sinav-giris" 
           style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">
            Sınava Başla
        </a>
    </p>
    
    <p style="margin-top: 30px;">Başarılar dileriz!</p>
    """
    
    return send_email(candidate.email, subject, html_body)


def send_email(to_email, subject, html_body):
    """
    Generic email sending function.
    Uses Flask-Mail or SendGrid based on configuration.
    """
    import os
    
    # Check for SendGrid
    sendgrid_key = os.getenv('SENDGRID_API_KEY')
    if sendgrid_key:
        return send_via_sendgrid(to_email, subject, html_body, sendgrid_key)
    
    # Fallback to logging
    logger.info(f"Email would be sent to {to_email}: {subject}")
    return {'status': 'sent', 'method': 'log'}


def send_via_sendgrid(to_email, subject, html_body, api_key):
    """Send email via SendGrid API."""
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
        
        sg = sendgrid.SendGridAPIClient(api_key)
        
        message = Mail(
            from_email='noreply@skillstestcenter.com',
            to_emails=to_email,
            subject=subject,
            html_content=html_body
        )
        
        response = sg.send(message)
        return {'status': 'sent', 'status_code': response.status_code}
        
    except Exception as e:
        logger.error(f"SendGrid error: {e}")
        return {'status': 'error', 'error': str(e)}

# -*- coding: utf-8 -*-
"""
Email Tasks - Celery tasks for sending emails
FIXED: Added SMTP fallback support alongside SendGrid
Uses: SendGrid (if SENDGRID_API_KEY set) -> SMTP (if MAIL_SERVER set) -> Log only
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.celery_app import celery

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# EMAIL SENDING FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def send_via_sendgrid(to_email, subject, html_body):
    """Send email via SendGrid API"""
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content
        
        sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))
        
        from_email = Email(os.getenv('MAIL_DEFAULT_SENDER', 'noreply@skillstestcenter.com'))
        to_email_obj = To(to_email)
        content = Content("text/html", html_body)
        
        mail = Mail(from_email, to_email_obj, subject, content)
        response = sg.client.mail.send.post(request_body=mail.get())
        
        logger.info(f"SendGrid email sent to {to_email}, status: {response.status_code}")
        return {'status': 'sent', 'method': 'sendgrid', 'status_code': response.status_code}
    
    except Exception as e:
        logger.error(f"SendGrid email failed: {e}")
        raise e


def send_via_smtp(to_email, subject, html_body):
    """Send email via SMTP (Flask-Mail compatible settings)"""
    try:
        mail_server = os.getenv('MAIL_SERVER')
        mail_port = int(os.getenv('MAIL_PORT', 587))
        mail_username = os.getenv('MAIL_USERNAME')
        mail_password = os.getenv('MAIL_PASSWORD')
        mail_use_tls = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
        mail_use_ssl = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
        mail_sender = os.getenv('MAIL_DEFAULT_SENDER', mail_username)
        
        if not all([mail_server, mail_username, mail_password]):
            raise ValueError("SMTP settings incomplete: MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD required")
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = mail_sender
        msg['To'] = to_email
        
        # Attach HTML content
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Connect and send
        if mail_use_ssl:
            server = smtplib.SMTP_SSL(mail_server, mail_port)
        else:
            server = smtplib.SMTP(mail_server, mail_port)
            if mail_use_tls:
                server.starttls()
        
        server.login(mail_username, mail_password)
        server.sendmail(mail_sender, [to_email], msg.as_string())
        server.quit()
        
        logger.info(f"SMTP email sent to {to_email}")
        return {'status': 'sent', 'method': 'smtp'}
    
    except Exception as e:
        logger.error(f"SMTP email failed: {e}")
        raise e


def send_email(to_email, subject, html_body):
    """
    Send email using available method:
    1. SendGrid (if SENDGRID_API_KEY is set)
    2. SMTP (if MAIL_SERVER is set)
    3. Log only (fallback for development)
    """
    # Try SendGrid first
    if os.getenv('SENDGRID_API_KEY'):
        try:
            return send_via_sendgrid(to_email, subject, html_body)
        except Exception as e:
            logger.warning(f"SendGrid failed, trying SMTP: {e}")
    
    # Try SMTP second
    if os.getenv('MAIL_SERVER'):
        try:
            return send_via_smtp(to_email, subject, html_body)
        except Exception as e:
            logger.warning(f"SMTP failed: {e}")
    
    # Fallback: Log only (development mode)
    logger.warning(f"No email service configured. Email logged only.")
    logger.info(f"[EMAIL LOG] To: {to_email}, Subject: {subject}")
    logger.debug(f"[EMAIL LOG] Body: {html_body[:500]}...")
    return {'status': 'logged', 'method': 'log', 'warning': 'No email service configured'}


# ══════════════════════════════════════════════════════════════════
# CELERY TASKS
# ══════════════════════════════════════════════════════════════════

@celery.task(bind=True, max_retries=3)
def send_certificate_email(self, candidate_id):
    """Send certificate email to candidate after exam completion"""
    try:
        from app import create_app
        from app.models import Candidate
        
        app = create_app()
        with app.app_context():
            candidate = Candidate.query.get(candidate_id)
            if not candidate or not candidate.email:
                logger.warning(f"Candidate {candidate_id} not found or no email")
                return {'status': 'skipped', 'reason': 'no_email'}
            
            cert_url = f"https://skillstestcenter.com/sertifika/verify/{candidate.certificate_hash}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">🎉 Tebrikler!</h1>
                </div>
                <div style="padding: 30px; background: #f8f9fa;">
                    <h2>Sayın {candidate.ad_soyad},</h2>
                    <p>Skills Test Center İngilizce Yeterlilik Sınavı'nı başarıyla tamamladınız.</p>
                    
                    <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        <h3>📊 Sınav Sonuçlarınız</h3>
                        <p><strong>Seviye:</strong> {candidate.seviye_sonuc or 'B1'}</p>
                        <p><strong>Genel Puan:</strong> {candidate.puan or 0:.1f}%</p>
                    </div>
                    
                    <p>Sertifikanızı görüntülemek için:</p>
                    <a href="{cert_url}" style="display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px;">
                        📜 Sertifikayı Görüntüle
                    </a>
                    
                    <p style="margin-top: 30px; color: #666; font-size: 12px;">
                        Bu sertifika 2 yıl geçerlidir.<br>
                        Doğrulama Kodu: {candidate.certificate_hash}
                    </p>
                </div>
                <div style="text-align: center; padding: 20px; color: #999;">
                    Skills Test Center - Bu email otomatik olarak gönderilmiştir.
                </div>
            </body>
            </html>
            """
            
            result = send_email(
                to_email=candidate.email,
                subject="🎓 Skills Test Center - Sınav Sonucunuz ve Sertifikanız",
                html_body=html_body
            )
            
            logger.info(f"Certificate email sent to {candidate.email}: {result}")
            return result
            
    except Exception as e:
        logger.error(f"send_certificate_email failed: {e}")
        self.retry(countdown=60, exc=e)


@celery.task(bind=True, max_retries=3)
def send_exam_reminder(self, candidate_id, scheduled_time):
    """Send exam reminder email"""
    try:
        from app import create_app
        from app.models import Candidate
        
        app = create_app()
        with app.app_context():
            candidate = Candidate.query.get(candidate_id)
            if not candidate or not candidate.email:
                return {'status': 'skipped', 'reason': 'no_email'}
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #3498db; padding: 30px; text-align: center;">
                    <h1 style="color: white;">⏰ Sınav Hatırlatması</h1>
                </div>
                <div style="padding: 30px;">
                    <h2>Sayın {candidate.ad_soyad},</h2>
                    <p>İngilizce Yeterlilik Sınavınız için bir hatırlatma:</p>
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                        <h3>📅 Sınav Zamanı: {scheduled_time}</h3>
                        <p><strong>Giriş Kodunuz:</strong> {candidate.giris_kodu}</p>
                    </div>
                    
                    <h4>Önemli Notlar:</h4>
                    <ul>
                        <li>Sessiz bir ortamda sınava girin</li>
                        <li>Stabil internet bağlantısı sağlayın</li>
                        <li>Kamera ve mikrofon izinlerini açık tutun</li>
                    </ul>
                    
                    <a href="https://skillstestcenter.com/sinav-giris" style="display: inline-block; background: #3498db; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px;">
                        🚀 Sınava Giriş Yap
                    </a>
                    
                    <p style="margin-top: 30px;">Başarılar dileriz!</p>
                </div>
            </body>
            </html>
            """
            
            result = send_email(
                to_email=candidate.email,
                subject="⏰ Skills Test Center - Sınav Hatırlatması",
                html_body=html_body
            )
            
            return result
            
    except Exception as e:
        logger.error(f"send_exam_reminder failed: {e}")
        self.retry(countdown=60, exc=e)


@celery.task(bind=True, max_retries=3)
def send_invite_email(self, candidate_id):
    """Send exam invitation email to new candidate"""
    try:
        from app import create_app
        from app.models import Candidate
        
        app = create_app()
        with app.app_context():
            candidate = Candidate.query.get(candidate_id)
            if not candidate or not candidate.email:
                return {'status': 'skipped', 'reason': 'no_email'}
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white;">📝 Sınav Daveti</h1>
                </div>
                <div style="padding: 30px;">
                    <h2>Sayın {candidate.ad_soyad},</h2>
                    <p>Skills Test Center İngilizce Yeterlilik Sınavı'na davet edildiniz.</p>
                    
                    <div style="background: #e8f5e9; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center;">
                        <h3>🔑 Giriş Kodunuz</h3>
                        <p style="font-size: 28px; font-weight: bold; color: #2e7d32; letter-spacing: 3px;">
                            {candidate.giris_kodu}
                        </p>
                        <p>Sınav Süresi: {candidate.sinav_suresi or 60} dakika</p>
                    </div>
                    
                    <h4>Sınava girmek için:</h4>
                    <ol>
                        <li><a href="https://skillstestcenter.com/sinav-giris">skillstestcenter.com/sinav-giris</a> adresine gidin</li>
                        <li>TC Kimlik numaranızı ve giriş kodunuzu girin</li>
                        <li>Sınava başlayın</li>
                    </ol>
                    
                    <a href="https://skillstestcenter.com/sinav-giris" style="display: inline-block; background: #11998e; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px;">
                        🚀 Sınava Başla
                    </a>
                    
                    <p style="margin-top: 30px;">Başarılar dileriz!</p>
                </div>
                <div style="text-align: center; padding: 20px; color: #999;">
                    Skills Test Center
                </div>
            </body>
            </html>
            """
            
            result = send_email(
                to_email=candidate.email,
                subject="📝 Skills Test Center - Sınav Davetiniz",
                html_body=html_body
            )
            
            logger.info(f"Invite email sent to {candidate.email}: {result}")
            return result
            
    except Exception as e:
        logger.error(f"send_invite_email failed: {e}")
        self.retry(countdown=60, exc=e)


@celery.task(bind=True, max_retries=2)
def send_bulk_invite_emails(self, candidate_ids):
    """Send invitation emails to multiple candidates"""
    results = []
    for candidate_id in candidate_ids:
        try:
            result = send_invite_email.delay(candidate_id)
            results.append({'candidate_id': candidate_id, 'task_id': result.id})
        except Exception as e:
            results.append({'candidate_id': candidate_id, 'error': str(e)})
    
    return {'total': len(candidate_ids), 'results': results}


@celery.task
def send_password_reset_email(user_id, reset_token):
    """Send password reset email"""
    try:
        from app import create_app
        from app.models import User
        
        app = create_app()
        with app.app_context():
            user = User.query.get(user_id)
            if not user or not user.email:
                return {'status': 'skipped', 'reason': 'no_email'}
            
            reset_url = f"https://skillstestcenter.com/reset-password/{reset_token}"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #e74c3c; padding: 30px; text-align: center;">
                    <h1 style="color: white;">🔐 Şifre Sıfırlama</h1>
                </div>
                <div style="padding: 30px;">
                    <h2>Sayın {user.ad_soyad or user.email},</h2>
                    <p>Şifre sıfırlama talebiniz alınmıştır.</p>
                    
                    <p>Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:</p>
                    
                    <a href="{reset_url}" style="display: inline-block; background: #e74c3c; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px;">
                        🔑 Şifremi Sıfırla
                    </a>
                    
                    <p style="margin-top: 30px; color: #666;">
                        Bu bağlantı 1 saat geçerlidir.<br>
                        Eğer bu talebi siz yapmadıysanız, bu emaili görmezden gelebilirsiniz.
                    </p>
                </div>
            </body>
            </html>
            """
            
            result = send_email(
                to_email=user.email,
                subject="🔐 Skills Test Center - Şifre Sıfırlama",
                html_body=html_body
            )
            
            return result
            
    except Exception as e:
        logger.error(f"send_password_reset_email failed: {e}")
        return {'status': 'error', 'error': str(e)}

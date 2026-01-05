# -*- coding: utf-8 -*-
"""
Email Tasks - Celery async email gönderimi
GitHub: app/tasks/email_tasks.py
Skills Test Center - Email System
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging

logger = logging.getLogger(__name__)

# SMTP Ayarları
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')


def send_email_sync(to_email, subject, html_content, text_content=None):
    """
    Senkron email gönderimi
    """
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP credentials not configured")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"Skills Test Center <{SMTP_USER}>"
        msg['To'] = to_email
        
        if text_content:
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(part1)
        
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part2)
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        
        logger.info(f"Email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


# ══════════════════════════════════════════════════════════════════
# CELERY TASKS
# ══════════════════════════════════════════════════════════════════

try:
    from celery import shared_task
    
    @shared_task(bind=True, max_retries=3)
    def send_exam_invitation(self, candidate_id):
        """
        Aday sınav davet emaili gönder (Async)
        """
        from app import create_app
        from app.models import Candidate, EmailLog
        from app.extensions import db
        
        app = create_app()
        with app.app_context():
            try:
                candidate = Candidate.query.get(candidate_id)
                if not candidate or not candidate.email:
                    return {'status': 'error', 'message': 'Candidate not found or no email'}
                
                sinav_url = "https://skillstestcenter.com/sinav-giris"
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                        .code-box {{ background: #2d3748; color: #38ef7d; padding: 20px; border-radius: 10px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 5px; margin: 20px 0; }}
                        .button {{ display: inline-block; background: #11998e; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                        .footer {{ text-align: center; color: #888; margin-top: 20px; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>📝 Sınav Davetiyesi</h1>
                        </div>
                        <div class="content">
                            <p>Sayın <strong>{candidate.ad_soyad}</strong>,</p>
                            <p>İngilizce yeterlilik sınavına davet edildiniz.</p>
                            
                            <h3>Giriş Kodunuz:</h3>
                            <div class="code-box">{candidate.giris_kodu}</div>
                            
                            <p><strong>⏱️ Sınav Süresi:</strong> {candidate.sinav_suresi or 30} dakika</p>
                            <p><strong>❓ Soru Sayısı:</strong> {candidate.soru_limiti or 25} soru</p>
                            
                            <p style="text-align: center;">
                                <a href="{sinav_url}" class="button">Sınava Başla</a>
                            </p>
                            
                            <p>Başarılar dileriz! 🍀</p>
                        </div>
                        <div class="footer">
                            <p>© 2026 Skills Test Center</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                success = send_email_sync(candidate.email, "Sınav Davetiyesi - Skills Test Center", html_content)
                
                # Email log kaydet
                try:
                    log = EmailLog(
                        recipient=candidate.email,
                        subject="Sınav Davetiyesi",
                        email_type='invitation',
                        status='sent' if success else 'failed',
                        candidate_id=candidate.id
                    )
                    db.session.add(log)
                    db.session.commit()
                except:
                    pass
                
                return {'status': 'success' if success else 'error', 'email': candidate.email}
                
            except Exception as e:
                logger.error(f"Invitation email task error: {e}")
                raise self.retry(exc=e, countdown=60)
    
    
    @shared_task(bind=True, max_retries=3)
    def send_exam_result(self, candidate_id):
        """
        Aday sınav sonuç emaili gönder (Async)
        """
        from app import create_app
        from app.models import Candidate, EmailLog
        from app.extensions import db
        
        app = create_app()
        with app.app_context():
            try:
                candidate = Candidate.query.get(candidate_id)
                if not candidate or not candidate.email:
                    return {'status': 'error', 'message': 'Candidate not found or no email'}
                
                level_colors = {
                    'A1': '#e74c3c', 'A2': '#e67e22', 'B1': '#f1c40f',
                    'B2': '#2ecc71', 'C1': '#3498db', 'C2': '#9b59b6'
                }
                level_color = level_colors.get(candidate.seviye_sonuc, '#667eea')
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                        .result-box {{ background: white; padding: 30px; border-radius: 15px; text-align: center; margin: 20px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
                        .level {{ font-size: 72px; font-weight: bold; color: {level_color}; }}
                        .score {{ font-size: 24px; color: #666; margin-top: 10px; }}
                        .footer {{ text-align: center; color: #888; margin-top: 20px; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🎓 Sınav Sonucunuz</h1>
                        </div>
                        <div class="content">
                            <p>Sayın <strong>{candidate.ad_soyad}</strong>,</p>
                            <p>İngilizce yeterlilik sınavınız başarıyla tamamlanmıştır.</p>
                            
                            <div class="result-box">
                                <div class="level">{candidate.seviye_sonuc or 'N/A'}</div>
                                <div class="score">Puan: {candidate.puan or 0}/100</div>
                            </div>
                            
                            <p>Tebrikler! 🎉</p>
                        </div>
                        <div class="footer">
                            <p>© 2026 Skills Test Center</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                success = send_email_sync(candidate.email, "Sınav Sonucunuz - Skills Test Center", html_content)
                
                # Email log kaydet
                try:
                    log = EmailLog(
                        recipient=candidate.email,
                        subject="Sınav Sonucu",
                        email_type='result',
                        status='sent' if success else 'failed',
                        candidate_id=candidate.id
                    )
                    db.session.add(log)
                    db.session.commit()
                except:
                    pass
                
                return {'status': 'success' if success else 'error', 'email': candidate.email}
                
            except Exception as e:
                logger.error(f"Result email task error: {e}")
                raise self.retry(exc=e, countdown=60)
    
    
    @shared_task(bind=True, max_retries=3)
    def send_password_reset_email_task(self, user_id, reset_token, reset_url):
        """
        Şifre sıfırlama emaili gönder (Async)
        """
        from app import create_app
        from app.models import User, EmailLog
        from app.extensions import db
        
        app = create_app()
        with app.app_context():
            try:
                user = User.query.get(user_id)
                if not user:
                    return {'status': 'error', 'message': 'User not found'}
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                        .button {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                        .footer {{ text-align: center; color: #888; margin-top: 20px; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🔐 Şifre Sıfırlama</h1>
                        </div>
                        <div class="content">
                            <p>Merhaba,</p>
                            <p>Şifre sıfırlama talebinde bulundunuz.</p>
                            <p style="text-align: center;">
                                <a href="{reset_url}" class="button">Şifremi Sıfırla</a>
                            </p>
                            <p><strong>Not:</strong> Bu bağlantı 1 saat içinde geçerliliğini yitirecektir.</p>
                        </div>
                        <div class="footer">
                            <p>© 2026 Skills Test Center</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                success = send_email_sync(user.email, "Şifre Sıfırlama - Skills Test Center", html_content)
                
                return {'status': 'success' if success else 'error', 'email': user.email}
                
            except Exception as e:
                logger.error(f"Password reset email task error: {e}")
                raise self.retry(exc=e, countdown=60)


except ImportError:
    # Celery yüklü değilse senkron versiyonları tanımla
    logger.warning("Celery not available, using synchronous email functions")
    
    def send_exam_invitation(candidate_id):
        """Senkron aday davet emaili"""
        from flask import current_app
        from app.models import Candidate
        
        try:
            candidate = Candidate.query.get(candidate_id)
            if candidate and candidate.email:
                from app.routes.auth import send_candidate_invitation_email
                return send_candidate_invitation_email(candidate)
        except Exception as e:
            logger.error(f"Sync invitation email error: {e}")
        return False
    
    def send_exam_result(candidate_id):
        """Senkron sınav sonuç emaili"""
        from flask import current_app
        from app.models import Candidate
        
        try:
            candidate = Candidate.query.get(candidate_id)
            if candidate and candidate.email:
                from app.routes.auth import send_exam_result_email
                return send_exam_result_email(candidate)
        except Exception as e:
            logger.error(f"Sync result email error: {e}")
        return False


# ══════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════════

def send_bulk_invitations(candidate_ids):
    """
    Toplu davet emaili gönder
    """
    results = {'success': 0, 'failed': 0}
    
    for cid in candidate_ids:
        try:
            # Celery varsa async, yoksa sync
            if 'shared_task' in dir():
                send_exam_invitation.delay(cid)
            else:
                send_exam_invitation(cid)
            results['success'] += 1
        except Exception as e:
            logger.error(f"Bulk invitation error for {cid}: {e}")
            results['failed'] += 1
    
    return results


def test_email_connection():
    """
    SMTP bağlantısını test et
    """
    if not SMTP_USER or not SMTP_PASS:
        return {'success': False, 'error': 'SMTP credentials not configured'}
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
        return {'success': True, 'message': 'SMTP connection successful'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

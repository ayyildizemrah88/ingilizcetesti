# -*- coding: utf-8 -*-
"""
Email Service - Brevo (Sendinblue) SMTP Integration
Handles all email sending for Skills Test Center
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

logger = logging.getLogger(__name__)

# Brevo SMTP Configuration (from image)
BREVO_SMTP_HOST = os.getenv('SMTP_HOST', 'smtp-relay.brevo.com')
BREVO_SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
BREVO_SMTP_USER = os.getenv('SMTP_USER', '9c6577001@smtp-brevo.com')
BREVO_SMTP_PASS = os.getenv('SMTP_PASS', 'bskDUx8qxMUwJum')
BREVO_FROM_EMAIL = os.getenv('SMTP_FROM', 'noreply@skillstestcenter.com')


class EmailService:
    """Email service using Brevo SMTP"""
    
    def __init__(self, company=None):
        """
        Initialize email service.
        If company is provided, uses company-specific SMTP settings.
        Otherwise uses global Brevo settings.
        """
        if company and company.smtp_host:
            self.host = company.smtp_host
            self.port = company.smtp_port or 587
            self.user = company.smtp_user
            self.password = company.smtp_pass
            self.from_email = company.smtp_from or company.email
        else:
            self.host = BREVO_SMTP_HOST
            self.port = BREVO_SMTP_PORT
            self.user = BREVO_SMTP_USER
            self.password = BREVO_SMTP_PASS
            self.from_email = BREVO_FROM_EMAIL
    
    def send_email(self, to_email, subject, html_content, text_content=None, attachments=None):
        """
        Send an email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text body (optional, auto-generated if not provided)
            attachments: List of file paths to attach (optional)
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"Skills Test Center <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text part
            if not text_content:
                import re
                text_content = re.sub('<[^>]+>', '', html_content)
            
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Add attachments
            if attachments:
                for filepath in attachments:
                    try:
                        with open(filepath, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{os.path.basename(filepath)}"'
                            )
                            msg.attach(part)
                    except Exception as e:
                        logger.warning(f"Could not attach file {filepath}: {e}")
            
            # Send via SMTP
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True, "Email gönderildi"
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP auth error: {e}")
            return False, "SMTP kimlik doğrulama hatası"
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False, f"SMTP hatası: {str(e)}"
        except Exception as e:
            logger.error(f"Email error: {e}")
            return False, f"E-posta hatası: {str(e)}"
    
    def send_exam_invitation(self, candidate):
        """Send exam invitation email to candidate"""
        subject = "Sınav Davetiyeniz - Skills Test Center"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .code-box {{ background: #fff; border: 2px dashed #667eea; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }}
                .code {{ font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 3px; }}
                .btn {{ display: inline-block; background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎓 Sınav Davetiyesi</h1>
                </div>
                <div class="content">
                    <p>Merhaba <strong>{candidate.ad_soyad}</strong>,</p>
                    
                    <p>İngilizce seviye tespit sınavına davet edildiniz. Sınava girmek için aşağıdaki giriş kodunu kullanın:</p>
                    
                    <div class="code-box">
                        <div class="code">{candidate.giris_kodu}</div>
                    </div>
                    
                    <p><strong>Sınav Bilgileri:</strong></p>
                    <ul>
                        <li>Süre: {candidate.sinav_suresi} dakika</li>
                        <li>Soru Sayısı: {candidate.soru_limiti} soru</li>
                    </ul>
                    
                    <p style="text-align: center;">
                        <a href="https://skillstestcenter.com/sinav-giris" class="btn">Sınava Başla →</a>
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                    
                    <p style="font-size: 13px; color: #666;">
                        💡 <strong>İpucu:</strong> Sınav başlamadan önce internet bağlantınızın stabil olduğundan emin olun.
                    </p>
                </div>
                <div class="footer">
                    <p>Bu e-posta Skills Test Center tarafından gönderilmiştir.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(candidate.email, subject, html_content)
    
    def send_password_reset(self, user, reset_url):
        """Send password reset email"""
        subject = "Şifre Sıfırlama - Skills Test Center"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ffc107; color: #333; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .btn {{ display: inline-block; background: #ffc107; color: #333; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔑 Şifre Sıfırlama</h1>
                </div>
                <div class="content">
                    <p>Merhaba,</p>
                    
                    <p>Şifrenizi sıfırlamak için bir istek aldık. Şifrenizi sıfırlamak için aşağıdaki butona tıklayın:</p>
                    
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="btn">Şifremi Sıfırla →</a>
                    </p>
                    
                    <p style="font-size: 13px; color: #666; margin-top: 30px;">
                        ⚠️ Bu link 1 saat geçerlidir. Eğer bu isteği siz yapmadıysanız, bu e-postayı görmezden gelebilirsiniz.
                    </p>
                </div>
                <div class="footer">
                    <p>Bu e-posta Skills Test Center tarafından gönderilmiştir.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user.email, subject, html_content)
    
    def send_exam_result(self, candidate, score, cefr_level):
        """Send exam result email"""
        subject = "Sınav Sonucunuz - Skills Test Center"
        
        # Color based on level
        level_colors = {
            'A1': '#dc3545', 'A2': '#fd7e14', 
            'B1': '#ffc107', 'B2': '#20c997',
            'C1': '#0d6efd', 'C2': '#6f42c1'
        }
        color = level_colors.get(cefr_level, '#667eea')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .result-box {{ background: white; border-radius: 10px; padding: 30px; text-align: center; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .score {{ font-size: 48px; font-weight: bold; color: {color}; }}
                .level {{ display: inline-block; background: {color}; color: white; padding: 10px 30px; border-radius: 30px; font-size: 24px; font-weight: bold; margin-top: 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Sınav Sonucunuz</h1>
                </div>
                <div class="content">
                    <p>Merhaba <strong>{candidate.ad_soyad}</strong>,</p>
                    
                    <p>Sınavınızı tamamladığınız için teşekkür ederiz. İşte sonuçlarınız:</p>
                    
                    <div class="result-box">
                        <div class="score">{score:.0f}%</div>
                        <div class="level">{cefr_level}</div>
                        <p style="margin-top: 20px; color: #666;">CEFR Seviyesi</p>
                    </div>
                    
                    <p>Sertifikanızı ve detaylı raporunuzu görüntülemek için Skills Test Center'a giriş yapabilirsiniz.</p>
                </div>
                <div class="footer">
                    <p>Bu e-posta Skills Test Center tarafından gönderilmiştir.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(candidate.email, subject, html_content)


# Convenience function
def send_email(to_email, subject, html_content, company=None):
    """Send email using default or company-specific settings"""
    service = EmailService(company)
    return service.send_email(to_email, subject, html_content)

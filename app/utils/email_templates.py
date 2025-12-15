# -*- coding: utf-8 -*-
"""
Professional HTML Email Templates
Branded email templates for Skills Test Center
"""
from datetime import datetime


class EmailTemplates:
    """Professional HTML email template generator."""
    
    # Brand colors
    PRIMARY_COLOR = "#667eea"
    SECONDARY_COLOR = "#764ba2"
    SUCCESS_COLOR = "#28a745"
    WARNING_COLOR = "#ffc107"
    DANGER_COLOR = "#dc3545"
    
    @classmethod
    def _base_template(cls, content, footer_text=""):
        """Base HTML template wrapper."""
        return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skills Test Center</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 40px 0;">
                <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {cls.PRIMARY_COLOR} 0%, {cls.SECONDARY_COLOR} 100%); padding: 30px; border-radius: 8px 8px 0 0; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: bold;">
                                📚 Skills Test Center
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            {content}
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 20px 30px; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="color: #6c757d; font-size: 12px; margin: 0;">
                                {footer_text if footer_text else "Bu e-posta Skills Test Center tarafından gönderilmiştir."}
                            </p>
                            <p style="color: #6c757d; font-size: 12px; margin: 10px 0 0 0;">
                                © {datetime.now().year} Skills Test Center. Tüm hakları saklıdır.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
'''
    
    @classmethod
    def exam_invitation(cls, candidate_name, exam_code, exam_url, company_name=None, expiry_date=None):
        """Exam invitation email template."""
        expiry_text = ""
        if expiry_date:
            expiry_text = f'''
            <p style="color: #6c757d; font-size: 14px; margin-top: 20px;">
                ⏰ Bu kod <strong>{expiry_date.strftime('%d.%m.%Y %H:%M')}</strong> tarihine kadar geçerlidir.
            </p>
            '''
        
        company_text = f" ({company_name})" if company_name else ""
        
        content = f'''
            <h2 style="color: #333; margin: 0 0 20px 0;">Merhaba {candidate_name},</h2>
            
            <p style="color: #555; font-size: 16px; line-height: 1.6;">
                İngilizce yeterlilik sınavına davet edildiniz{company_text}. Aşağıdaki bilgileri kullanarak sınava giriş yapabilirsiniz.
            </p>
            
            <div style="background: linear-gradient(135deg, {cls.PRIMARY_COLOR}15 0%, {cls.SECONDARY_COLOR}15 100%); border-radius: 8px; padding: 25px; margin: 25px 0; text-align: center;">
                <p style="color: #555; font-size: 14px; margin: 0 0 10px 0;">Sınav Kodunuz:</p>
                <p style="color: {cls.PRIMARY_COLOR}; font-size: 32px; font-weight: bold; margin: 0; letter-spacing: 3px;">
                    {exam_code}
                </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{exam_url}" style="display: inline-block; background: linear-gradient(135deg, {cls.PRIMARY_COLOR} 0%, {cls.SECONDARY_COLOR} 100%); color: #ffffff; text-decoration: none; padding: 15px 40px; border-radius: 30px; font-size: 16px; font-weight: bold;">
                    Sınava Başla
                </a>
            </div>
            
            {expiry_text}
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            
            <h3 style="color: #333; margin: 0 0 15px 0;">📋 Sınav Hakkında:</h3>
            <ul style="color: #555; font-size: 14px; line-height: 1.8; padding-left: 20px;">
                <li>Sınav süresi yaklaşık 60-90 dakikadır</li>
                <li>Dilbilgisi, kelime, okuma, dinleme, yazma ve konuşma bölümlerinden oluşur</li>
                <li>Sakin ve sessiz bir ortamda sınava girmeniz önerilir</li>
                <li>Stabil bir internet bağlantısı gereklidir</li>
            </ul>
            
            <p style="color: #555; font-size: 14px; margin-top: 25px;">
                Başarılar dileriz! 🍀
            </p>
        '''
        
        return cls._base_template(content)
    
    @classmethod
    def exam_completed(cls, candidate_name, score, cefr_level, certificate_url=None, skills=None):
        """Exam completion notification template."""
        
        level_colors = {
            'A1': '#dc3545', 'A2': '#fd7e14',
            'B1': '#ffc107', 'B2': '#28a745',
            'C1': '#20c997', 'C2': '#6f42c1'
        }
        level_color = level_colors.get(cefr_level, cls.PRIMARY_COLOR)
        
        skills_html = ""
        if skills:
            skills_html = '''
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            '''
            for skill, value in skills.items():
                skills_html += f'''
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; color: #555;">{skill.title()}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">
                        <div style="background-color: #e9ecef; border-radius: 10px; overflow: hidden; width: 150px; display: inline-block;">
                            <div style="background: linear-gradient(90deg, {cls.PRIMARY_COLOR}, {cls.SECONDARY_COLOR}); width: {value}%; height: 20px;"></div>
                        </div>
                        <span style="color: #333; font-weight: bold; margin-left: 10px;">{value}%</span>
                    </td>
                </tr>
                '''
            skills_html += '</table>'
        
        cert_button = ""
        if certificate_url:
            cert_button = f'''
            <div style="text-align: center; margin: 30px 0;">
                <a href="{certificate_url}" style="display: inline-block; background: linear-gradient(135deg, {cls.SUCCESS_COLOR} 0%, #218838 100%); color: #ffffff; text-decoration: none; padding: 15px 40px; border-radius: 30px; font-size: 16px; font-weight: bold;">
                    📜 Sertifikayı İndir
                </a>
            </div>
            '''
        
        content = f'''
            <h2 style="color: #333; margin: 0 0 20px 0;">Tebrikler {candidate_name}! 🎉</h2>
            
            <p style="color: #555; font-size: 16px; line-height: 1.6;">
                İngilizce yeterlilik sınavınızı başarıyla tamamladınız. İşte sonuçlarınız:
            </p>
            
            <div style="background: linear-gradient(135deg, {level_color}20 0%, {level_color}10 100%); border-radius: 8px; padding: 30px; margin: 25px 0; text-align: center; border: 2px solid {level_color};">
                <p style="color: #555; font-size: 14px; margin: 0 0 10px 0;">CEFR Seviyeniz:</p>
                <p style="color: {level_color}; font-size: 48px; font-weight: bold; margin: 0;">
                    {cefr_level}
                </p>
                <p style="color: #555; font-size: 18px; margin: 15px 0 0 0;">
                    Toplam Puan: <strong>{score}%</strong>
                </p>
            </div>
            
            {skills_html}
            
            {cert_button}
            
            <p style="color: #555; font-size: 14px; margin-top: 25px;">
                Sınavınızı değerlendirdiğiniz için teşekkür ederiz!
            </p>
        '''
        
        return cls._base_template(content)
    
    @classmethod
    def password_reset(cls, user_name, reset_url, expiry_minutes=60):
        """Password reset email template."""
        
        content = f'''
            <h2 style="color: #333; margin: 0 0 20px 0;">Merhaba {user_name},</h2>
            
            <p style="color: #555; font-size: 16px; line-height: 1.6;">
                Hesabınız için şifre sıfırlama talebinde bulundunuz. Şifrenizi sıfırlamak için aşağıdaki butona tıklayın.
            </p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="display: inline-block; background: linear-gradient(135deg, {cls.WARNING_COLOR} 0%, #e0a800 100%); color: #333; text-decoration: none; padding: 15px 40px; border-radius: 30px; font-size: 16px; font-weight: bold;">
                    🔑 Şifremi Sıfırla
                </a>
            </div>
            
            <div style="background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin: 25px 0;">
                <p style="color: #856404; font-size: 14px; margin: 0;">
                    ⚠️ Bu bağlantı <strong>{expiry_minutes} dakika</strong> içinde geçerliliğini yitirecektir.
                </p>
            </div>
            
            <p style="color: #555; font-size: 14px; line-height: 1.6;">
                Eğer bu talebi siz yapmadıysanız, bu e-postayı görmezden gelebilirsiniz. Hesabınız güvende.
            </p>
        '''
        
        return cls._base_template(content, "Bu otomatik bir e-postadır, lütfen yanıtlamayın.")
    
    @classmethod
    def two_factor_enabled(cls, user_name):
        """2FA enabled notification template."""
        
        content = f'''
            <h2 style="color: #333; margin: 0 0 20px 0;">Merhaba {user_name},</h2>
            
            <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                <p style="color: #155724; font-size: 18px; margin: 0;">
                    ✅ İki faktörlü doğrulama başarıyla etkinleştirildi!
                </p>
            </div>
            
            <p style="color: #555; font-size: 16px; line-height: 1.6;">
                Hesabınız artık ekstra güvenlik katmanıyla korunuyor. Bundan sonraki girişlerinizde doğrulama uygulamanızdan kod girmeniz gerekecektir.
            </p>
            
            <h3 style="color: #333; margin: 25px 0 15px 0;">🔐 Önemli Hatırlatmalar:</h3>
            <ul style="color: #555; font-size: 14px; line-height: 1.8; padding-left: 20px;">
                <li>Yedek kodlarınızı güvenli bir yere kaydedin</li>
                <li>Telefonunuzu kaybederseniz yedek kodlarla giriş yapabilirsiniz</li>
                <li>2FA'yı kapatmak için yöneticinizle iletişime geçin</li>
            </ul>
        '''
        
        return cls._base_template(content)
    
    @classmethod
    def credit_added(cls, company_name, credit_amount, total_credits, invoice_url=None):
        """Credit purchase confirmation template."""
        
        invoice_button = ""
        if invoice_url:
            invoice_button = f'''
            <div style="text-align: center; margin: 30px 0;">
                <a href="{invoice_url}" style="display: inline-block; background: linear-gradient(135deg, {cls.PRIMARY_COLOR} 0%, {cls.SECONDARY_COLOR} 100%); color: #ffffff; text-decoration: none; padding: 15px 40px; border-radius: 30px; font-size: 16px; font-weight: bold;">
                    📄 Faturayı Görüntüle
                </a>
            </div>
            '''
        
        content = f'''
            <h2 style="color: #333; margin: 0 0 20px 0;">Kredi Yükleme Başarılı! 💳</h2>
            
            <p style="color: #555; font-size: 16px; line-height: 1.6;">
                <strong>{company_name}</strong> hesabınıza kredi yüklemesi yapılmıştır.
            </p>
            
            <div style="background: linear-gradient(135deg, {cls.SUCCESS_COLOR}20 0%, {cls.SUCCESS_COLOR}10 100%); border-radius: 8px; padding: 25px; margin: 25px 0; text-align: center; border: 2px solid {cls.SUCCESS_COLOR};">
                <p style="color: #555; font-size: 14px; margin: 0 0 5px 0;">Eklenen Kredi:</p>
                <p style="color: {cls.SUCCESS_COLOR}; font-size: 36px; font-weight: bold; margin: 0;">
                    +{credit_amount}
                </p>
                <hr style="border: none; border-top: 1px solid #c3e6cb; margin: 20px 0;">
                <p style="color: #555; font-size: 14px; margin: 0;">
                    Toplam Kredi: <strong style="color: {cls.PRIMARY_COLOR}; font-size: 20px;">{total_credits}</strong>
                </p>
            </div>
            
            {invoice_button}
            
            <p style="color: #555; font-size: 14px;">
                Teşekkür ederiz! 🙏
            </p>
        '''
        
        return cls._base_template(content)
    
    @classmethod
    def low_credit_warning(cls, company_name, remaining_credits, purchase_url):
        """Low credit warning template."""
        
        content = f'''
            <h2 style="color: #333; margin: 0 0 20px 0;">⚠️ Kredi Uyarısı</h2>
            
            <p style="color: #555; font-size: 16px; line-height: 1.6;">
                <strong>{company_name}</strong> hesabınızdaki sınav kredisi azalmaktadır.
            </p>
            
            <div style="background-color: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 25px; margin: 25px 0; text-align: center;">
                <p style="color: #856404; font-size: 14px; margin: 0 0 5px 0;">Kalan Kredi:</p>
                <p style="color: #856404; font-size: 48px; font-weight: bold; margin: 0;">
                    {remaining_credits}
                </p>
            </div>
            
            <p style="color: #555; font-size: 16px; line-height: 1.6;">
                Sınav kredinizi tamamlamak için aşağıdaki butona tıklayın ve kesintisiz hizmet almaya devam edin.
            </p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{purchase_url}" style="display: inline-block; background: linear-gradient(135deg, {cls.PRIMARY_COLOR} 0%, {cls.SECONDARY_COLOR} 100%); color: #ffffff; text-decoration: none; padding: 15px 40px; border-radius: 30px; font-size: 16px; font-weight: bold;">
                    💳 Kredi Satın Al
                </a>
            </div>
        '''
        
        return cls._base_template(content)

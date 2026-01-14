# -*- coding: utf-8 -*-
"""
PDF Certificate Generator
Generates professional certificates for exam completion
"""
import os
import hashlib
import qrcode
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class CertificateGenerator:
    """Generate professional PDF certificates for exam completion."""
    
    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.getenv('CERTIFICATE_DIR', '/tmp/certificates')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Certificate styling
        self.page_size = landscape(A4)
        self.width, self.height = self.page_size
        
        # Colors
        self.primary_color = colors.HexColor('#667eea')
        self.secondary_color = colors.HexColor('#764ba2')
        self.gold_color = colors.HexColor('#FFD700')
        self.dark_color = colors.HexColor('#2c3e50')
    
    def generate_certificate_hash(self, candidate_id, exam_date):
        """Generate unique verification hash for certificate."""
        data = f"{candidate_id}-{exam_date.isoformat()}-skillstestcenter"
        return hashlib.sha256(data.encode()).hexdigest()[:16].upper()
    
    def generate_qr_code(self, verification_url):
        """Generate QR code for certificate verification."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=3,
            border=2,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    
    def get_cefr_description(self, level):
        """Get CEFR level description."""
        descriptions = {
            'A1': 'Beginner - Can understand and use familiar everyday expressions',
            'A2': 'Elementary - Can communicate in simple and routine tasks',
            'B1': 'Intermediate - Can deal with most situations likely to arise',
            'B2': 'Upper-Intermediate - Can interact with a degree of fluency',
            'C1': 'Advanced - Can express ideas fluently and spontaneously',
            'C2': 'Proficient - Can understand with ease virtually everything'
        }
        return descriptions.get(level, 'English Proficiency')
    
    def create_certificate(self, candidate_data, base_url='https://skillstestcenter.com'):
        """
        Generate a PDF certificate for a candidate.
        
        Args:
            candidate_data: dict with keys:
                - id: candidate ID
                - ad_soyad: full name
                - puan: total score (0-100)
                - cefr_seviye: CEFR level (A1-C2)
                - sinav_bitis: exam completion datetime
                - skills: dict of skill scores
            base_url: base URL for verification
        
        Returns:
            tuple: (file_path, certificate_hash)
        """
        # Generate verification hash
        cert_hash = self.generate_certificate_hash(
            candidate_data['id'],
            candidate_data.get('sinav_bitis', datetime.utcnow())
        )
        
        # Verification URL
        verification_url = f"{base_url}/verify/{cert_hash}"
        
        # Output file path
        filename = f"certificate_{candidate_data['id']}_{cert_hash}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        # Create PDF
        c = canvas.Canvas(filepath, pagesize=self.page_size)
        
        # Draw certificate
        self._draw_background(c)
        self._draw_border(c)
        self._draw_header(c)
        self._draw_recipient_name(c, candidate_data['ad_soyad'])
        self._draw_achievement(c, candidate_data)
        self._draw_scores(c, candidate_data)
        self._draw_footer(c, cert_hash, verification_url)
        self._draw_qr_code(c, verification_url)
        
        c.save()
        
        return filepath, cert_hash
    
    def _draw_background(self, c):
        """Draw certificate background gradient."""
        c.setFillColor(colors.HexColor('#f8f9fa'))
        c.rect(0, 0, self.width, self.height, fill=True, stroke=False)
        
        c.setFillColor(self.primary_color)
        c.rect(0, self.height - 3*cm, self.width, 3*cm, fill=True, stroke=False)
        
        c.setFillColor(self.secondary_color)
        c.rect(0, 0, self.width, 2*cm, fill=True, stroke=False)
    
    def _draw_border(self, c):
        """Draw decorative border - disabled per user request."""
        # Yellow/gold border removed
        pass
    
    def _draw_header(self, c):
        """Draw certificate header."""
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 28)
        c.drawCentredString(self.width/2, self.height - 2.2*cm, "SKILLS TEST CENTER")
        
        c.setFillColor(self.primary_color)
        c.setFont('Helvetica-Bold', 36)
        c.drawCentredString(self.width/2, self.height - 5.5*cm, "Certificate of Achievement")
        
        c.setFillColor(self.dark_color)
        c.setFont('Helvetica', 14)
        c.drawCentredString(self.width/2, self.height - 6.5*cm, "English Language Proficiency Assessment")
    
    def _draw_recipient_name(self, c, name):
        """Draw recipient name."""
        c.setFillColor(self.dark_color)
        c.setFont('Helvetica', 14)
        c.drawCentredString(self.width/2, self.height - 8.5*cm, "This is to certify that")
        
        c.setFont('Helvetica-Bold', 32)
        c.setFillColor(self.secondary_color)
        c.drawCentredString(self.width/2, self.height - 10*cm, name.upper())
        
        name_width = c.stringWidth(name.upper(), 'Helvetica-Bold', 32)
        c.setStrokeColor(self.gold_color)
        c.setLineWidth(2)
        c.line(
            self.width/2 - name_width/2 - 20,
            self.height - 10.5*cm,
            self.width/2 + name_width/2 + 20,
            self.height - 10.5*cm
        )
    
    def _draw_achievement(self, c, data):
        """Draw achievement details."""
        cefr_level = data.get('cefr_seviye', 'B1')
        score = data.get('puan', 0)
        
        c.setFillColor(self.dark_color)
        c.setFont('Helvetica', 14)
        c.drawCentredString(self.width/2, self.height - 11.8*cm, 
            "has successfully completed the English Proficiency Assessment")
        
        c.setFillColor(self.primary_color)
        c.setFont('Helvetica-Bold', 48)
        c.drawCentredString(self.width/2, self.height - 13.8*cm, cefr_level)
        
        c.setFillColor(self.dark_color)
        c.setFont('Helvetica-Oblique', 12)
        description = self.get_cefr_description(cefr_level)
        c.drawCentredString(self.width/2, self.height - 14.8*cm, description)
        
        c.setFont('Helvetica-Bold', 16)
        c.drawCentredString(self.width/2, self.height - 16*cm, f"Overall Score: {score}%")
    
    def _draw_scores(self, c, data):
        """Draw skill scores."""
        skills = data.get('skills', {})
        
        x_start = 3.5*cm
        y_pos = 4*cm
        bar_width = 3*cm
        spacing = 4.2*cm
        
        skill_names = ['Grammar', 'Vocabulary', 'Reading', 'Listening', 'Writing', 'Speaking']
        skill_keys = ['grammar', 'vocabulary', 'reading', 'listening', 'writing', 'speaking']
        
        c.setFont('Helvetica', 9)
        
        for i, (name, key) in enumerate(zip(skill_names, skill_keys)):
            x = x_start + (i * spacing)
            score = skills.get(key, 0) or 0
            
            c.setFillColor(self.dark_color)
            c.drawCentredString(x + bar_width/2, y_pos + 0.8*cm, name)
            
            c.setFillColor(colors.HexColor('#e0e0e0'))
            c.rect(x, y_pos, bar_width, 0.5*cm, fill=True, stroke=False)
            
            fill_width = (score / 100) * bar_width
            c.setFillColor(self.primary_color)
            c.rect(x, y_pos, fill_width, 0.5*cm, fill=True, stroke=False)
            
            c.setFillColor(self.dark_color)
            c.drawCentredString(x + bar_width/2, y_pos - 0.4*cm, f"{score}%")
    
    def _draw_footer(self, c, cert_hash, verification_url):
        """Draw certificate footer."""
        c.setFillColor(self.dark_color)
        c.setFont('Helvetica', 10)
        date_str = datetime.utcnow().strftime('%B %d, %Y')
        c.drawString(3*cm, 2.8*cm, f"Issue Date: {date_str}")
        c.drawString(3*cm, 2.3*cm, f"Certificate ID: {cert_hash}")
        
        c.setFont('Helvetica', 8)
        c.setFillColor(colors.white)
        c.drawCentredString(self.width/2, 0.8*cm, f"Verify this certificate at: {verification_url}")
        
        c.setStrokeColor(self.dark_color)
        c.setLineWidth(1)
        sig_y = 3.5*cm
        c.line(self.width - 8*cm, sig_y, self.width - 3*cm, sig_y)
        c.setFillColor(self.dark_color)
        c.setFont('Helvetica', 10)
        c.drawCentredString(self.width - 5.5*cm, 2.8*cm, "Authorized Signature")
    
    def _draw_qr_code(self, c, verification_url):
        """Draw QR code for verification."""
        try:
            qr_buffer = self.generate_qr_code(verification_url)
            qr_x = self.width - 6*cm
            qr_y = 4.5*cm
            
            c.drawImage(
                qr_buffer, qr_x, qr_y,
                width=2.5*cm, height=2.5*cm,
                preserveAspectRatio=True
            )
        except Exception as e:
            print(f"QR code generation failed: {e}")


def generate_certificate(candidate_data, base_url='https://skillstestcenter.com'):
    """Convenience function to generate a certificate."""
    generator = CertificateGenerator()
    return generator.create_certificate(candidate_data, base_url)

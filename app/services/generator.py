"""Certificate generation service."""

import io
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import settings
from app.models import CertificateRequest, CertificateType


class CertificateGenerator:
    """Certificate PDF generator using ReportLab."""
    
    def __init__(self):
        """Initialize certificate generator."""
        self.page_size = letter if settings.certificate_page_size == "Letter" else A4
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        self._load_logo()
    
    def _load_logo(self):
        """Load the MicroLearn logo image."""
        # Try multiple possible logo locations
        logo_paths = [
            Path("app/static/assets/microlearn-logo.png"),
            Path("../mlsk/static/images/logo.png"),
            Path("static/assets/microlearn-logo.png"),
        ]
        
        self.logo = None
        for logo_path in logo_paths:
            if logo_path.exists():
                try:
                    self.logo = ImageReader(str(logo_path))
                    break
                except Exception as e:
                    print(f"Warning: Could not load logo from {logo_path}: {e}")
        
        if not self.logo:
            print("Warning: Logo not found in any expected location")
    
    def _setup_styles(self):
        """Setup custom styles for certificate."""
        # Title style
        self.styles.add(ParagraphStyle(
            name="CertificateTitle",
            parent=self.styles["Heading1"],
            fontSize=28,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name="CertificateSubtitle",
            parent=self.styles["Heading2"],
            fontSize=20,
            textColor=colors.HexColor("#4a4a4a"),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName="Helvetica",
        ))
        
        # Recipient name style
        self.styles.add(ParagraphStyle(
            name="RecipientName",
            parent=self.styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#2c5282"),
            spaceAfter=20,
            spaceBefore=20,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        ))
        
        # Body text style
        self.styles.add(ParagraphStyle(
            name="CertificateBody",
            parent=self.styles["Normal"],
            fontSize=14,
            textColor=colors.HexColor("#4a4a4a"),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName="Helvetica",
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name="CertificateFooter",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#6a6a6a"),
            alignment=TA_CENTER,
            fontName="Helvetica",
        ))
    
    async def generate_certificate(self, request: CertificateRequest) -> bytes:
        """Generate certificate PDF.
        
        Args:
            request: Certificate request data
            
        Returns:
            PDF data as bytes
        """
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create canvas
        pdf = canvas.Canvas(buffer, pagesize=self.page_size)
        width, height = self.page_size
        
        # Draw certificate border
        self._draw_border(pdf, width, height)
        
        # Add certificate content based on type
        if request.certificate_type == CertificateType.COLLECTION:
            self._draw_collection_certificate(pdf, request, width, height)
        elif request.certificate_type == CertificateType.COURSE:
            self._draw_course_certificate(pdf, request, width, height)
        elif request.certificate_type == CertificateType.ACHIEVEMENT:
            self._draw_achievement_certificate(pdf, request, width, height)
        
        # Add footer
        self._draw_footer(pdf, request, width, height)
        
        # Save PDF
        pdf.save()
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data
    
    def _draw_border(self, pdf: canvas.Canvas, width: float, height: float):
        """Draw decorative border on certificate."""
        # Outer border
        pdf.setStrokeColor(colors.HexColor("#2c5282"))
        pdf.setLineWidth(3)
        pdf.rect(0.5 * inch, 0.5 * inch, width - inch, height - inch)
        
        # Inner border
        pdf.setLineWidth(1)
        pdf.rect(0.6 * inch, 0.6 * inch, width - 1.2 * inch, height - 1.2 * inch)
    
    def _draw_header_with_logo(self, pdf: canvas.Canvas, width: float, height: float):
        """Draw the MicroLearn logo at the top of the certificate."""
        if self.logo:
            # Position for logo - centered at top
            # Use a larger size since the logo includes text
            logo_width = 120  # Wider to accommodate text in logo
            logo_height = 60  # Proportional height
            logo_x = (width - logo_width) / 2
            logo_y = height - 1.5 * inch
            
            # Draw logo image with embedded text
            pdf.drawImage(self.logo, logo_x, logo_y, width=logo_width, height=logo_height, mask='auto', preserveAspectRatio=True)
        
        # Reset color to black for subsequent text
        pdf.setFillColor(colors.black)
    
    def _draw_collection_certificate(
        self,
        pdf: canvas.Canvas,
        request: CertificateRequest,
        width: float,
        height: float
    ):
        """Draw collection certificate content."""
        # Draw logo header
        self._draw_header_with_logo(pdf, width, height)
        
        # Certificate title (adjusted position to account for logo)
        pdf.setFont("Helvetica-Bold", 32)
        pdf.drawCentredString(width / 2, height - 2.5 * inch, "Certificate of Completion")
        
        # Collection name
        pdf.setFont("Helvetica", 20)
        pdf.drawCentredString(width / 2, height - 3.2 * inch, request.title)
        
        # Presented to
        pdf.setFont("Helvetica", 16)
        pdf.drawCentredString(width / 2, height - 4.2 * inch, "This certifies that")
        
        # Recipient name
        pdf.setFont("Helvetica-Bold", 24)
        pdf.setFillColor(colors.HexColor("#2c5282"))
        pdf.drawCentredString(width / 2, height - 4.8 * inch, request.user_name)
        pdf.setFillColor(colors.black)
        
        # Completion text
        pdf.setFont("Helvetica", 14)
        pdf.drawCentredString(
            width / 2,
            height - 5.6 * inch,
            "has successfully completed all courses in this collection"
        )
        
        # Completed items
        if request.items_completed:
            pdf.setFont("Helvetica", 12)
            y_position = height - 6.4 * inch
            
            pdf.drawCentredString(width / 2, y_position, "Courses Completed:")
            y_position -= 0.3 * inch
            
            pdf.setFont("Helvetica", 11)
            for item in request.items_completed[:5]:  # Show max 5 items
                pdf.drawCentredString(width / 2, y_position, f"• {item}")
                y_position -= 0.25 * inch
            
            if len(request.items_completed) > 5:
                pdf.drawCentredString(
                    width / 2,
                    y_position,
                    f"... and {len(request.items_completed) - 5} more"
                )
    
    def _draw_course_certificate(
        self,
        pdf: canvas.Canvas,
        request: CertificateRequest,
        width: float,
        height: float
    ):
        """Draw course certificate content."""
        # Draw logo header
        self._draw_header_with_logo(pdf, width, height)
        
        # Certificate title (adjusted position to account for logo)
        pdf.setFont("Helvetica-Bold", 32)
        pdf.drawCentredString(width / 2, height - 2.5 * inch, "Certificate of Achievement")
        
        # Course name
        pdf.setFont("Helvetica", 20)
        pdf.drawCentredString(width / 2, height - 3.2 * inch, request.title)
        
        # Presented to
        pdf.setFont("Helvetica", 16)
        pdf.drawCentredString(width / 2, height - 4.2 * inch, "This certifies that")
        
        # Recipient name
        pdf.setFont("Helvetica-Bold", 24)
        pdf.setFillColor(colors.HexColor("#2c5282"))
        pdf.drawCentredString(width / 2, height - 4.8 * inch, request.user_name)
        pdf.setFillColor(colors.black)
        
        # Completion text
        pdf.setFont("Helvetica", 14)
        pdf.drawCentredString(
            width / 2,
            height - 5.6 * inch,
            "has successfully completed this course"
        )
        
        # Description if provided
        if request.description:
            pdf.setFont("Helvetica", 12)
            # Word wrap description
            lines = self._wrap_text(request.description, 60)
            y_position = height - 6.4 * inch
            for line in lines[:3]:  # Show max 3 lines
                pdf.drawCentredString(width / 2, y_position, line)
                y_position -= 0.25 * inch
    
    def _draw_achievement_certificate(
        self,
        pdf: canvas.Canvas,
        request: CertificateRequest,
        width: float,
        height: float
    ):
        """Draw achievement certificate content."""
        # Draw logo header
        self._draw_header_with_logo(pdf, width, height)
        
        # Certificate title (adjusted position to account for logo)
        pdf.setFont("Helvetica-Bold", 32)
        pdf.drawCentredString(width / 2, height - 2.5 * inch, "Certificate of Achievement")
        
        # Achievement name
        pdf.setFont("Helvetica", 20)
        pdf.drawCentredString(width / 2, height - 3.2 * inch, request.title)
        
        # Presented to
        pdf.setFont("Helvetica", 16)
        pdf.drawCentredString(width / 2, height - 4.2 * inch, "Awarded to")
        
        # Recipient name
        pdf.setFont("Helvetica-Bold", 24)
        pdf.setFillColor(colors.HexColor("#2c5282"))
        pdf.drawCentredString(width / 2, height - 4.8 * inch, request.user_name)
        pdf.setFillColor(colors.black)
        
        # Achievement text
        pdf.setFont("Helvetica", 14)
        pdf.drawCentredString(
            width / 2,
            height - 5.6 * inch,
            "in recognition of outstanding achievement"
        )
        
        # Description if provided
        if request.description:
            pdf.setFont("Helvetica", 12)
            lines = self._wrap_text(request.description, 60)
            y_position = height - 6.4 * inch
            for line in lines[:3]:
                pdf.drawCentredString(width / 2, y_position, line)
                y_position -= 0.25 * inch
    
    def _draw_footer(
        self,
        pdf: canvas.Canvas,
        request: CertificateRequest,
        width: float,
        height: float
    ):
        """Draw certificate footer with date and ID."""
        # Issue date
        issue_date = request.issued_date or datetime.utcnow()
        date_str = issue_date.strftime("%B %d, %Y")
        
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(width / 2, 2 * inch, f"Issued on {date_str}")
        
        # Certificate ID
        cert_id = request.certificate_id or str(uuid.uuid4())
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#6a6a6a"))
        pdf.drawCentredString(width / 2, 1.5 * inch, f"Certificate ID: {cert_id}")
        
        # Verification URL (placeholder)
        pdf.drawCentredString(
            width / 2,
            1.2 * inch,
            "Verify at: certificates.microlearn.com/verify"
        )
    
    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        """Simple text wrapping.
        
        Args:
            text: Text to wrap
            max_chars: Maximum characters per line
            
        Returns:
            List of wrapped lines
        """
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines
    
    async def generate_batch_certificates(
        self,
        requests: List[CertificateRequest]
    ) -> List[bytes]:
        """Generate multiple certificates.
        
        Args:
            requests: List of certificate requests
            
        Returns:
            List of PDF data as bytes
        """
        certificates = []
        for request in requests:
            pdf_data = await self.generate_certificate(request)
            certificates.append(pdf_data)
        
        return certificates


# Global certificate generator instance
certificate_generator = CertificateGenerator()

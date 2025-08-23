"""Certificate verification service."""

from datetime import datetime
from typing import Optional, Dict, Any
import os

from app.config import settings
from app.models import CertificateVerification, CertificateRequest
from app.services.storage import storage_service


class VerificationService:
    """Service for verifying certificates."""
    
    def __init__(self, redis_client=None):
        """Initialize verification service.
        
        Args:
            redis_client: Optional Redis client for caching
        """
        self.redis_client = redis_client
        
        # Use environment variable with fallback for verification URL
        # In production: https://tracks.microlearn.university/verify
        # In development: http://localhost:8001/verify
        self.verify_base_url = os.getenv(
            "CERTIFICATE_VERIFY_URL",
            "http://localhost:8001/verify" if settings.environment == "development"
            else "https://tracks.microlearn.university/verify"
        )
    
    async def verify_certificate(self, certificate_id: str) -> Optional[CertificateVerification]:
        """Verify a certificate.
        
        Args:
            certificate_id: Certificate ID to verify
            
        Returns:
            CertificateVerification if certificate exists and is valid, None otherwise
        """
        # Try to get certificate data from Redis first
        certificate_data = None
        s3_key = None
        
        if self.redis_client:
            cached_key = self.redis_client.get(f"cert:{certificate_id}")
            if cached_key:
                s3_key = cached_key
                metadata = await self.get_metadata(s3_key)
                if metadata:
                    certificate_data = metadata
        
        # If not in cache, try to find the certificate
        if not s3_key:
            now = datetime.utcnow()
            s3_key = f"certificates/{now.year}/{now.month:02d}/{certificate_id}.pdf"
            
            # Check if certificate exists in storage
            exists = await storage_service.certificate_exists(s3_key)
            if not exists:
                # Try previous month (in case certificate was generated near month boundary)
                if now.day < 5:  # Only try previous month for first few days
                    prev_month = 12 if now.month == 1 else now.month - 1
                    prev_year = now.year - 1 if now.month == 1 else now.year
                    s3_key = f"certificates/{prev_year}/{prev_month:02d}/{certificate_id}.pdf"
                    exists = await storage_service.certificate_exists(s3_key)
                    if not exists:
                        return None
                else:
                    return None
            
            # Get metadata from storage
            metadata = await self.get_metadata(s3_key)
            if not metadata:
                return None
            
            certificate_data = metadata
        
        # Get fresh download URL
        download_url = storage_service.get_presigned_url(s3_key)
        
        # Construct verification URL - the user-facing URL, not the API URL
        verification_url = f"{self.verify_base_url}/{certificate_id}"
        
        # Parse metadata and return verification response
        items_value = certificate_data.get("items_completed", "")
        if isinstance(items_value, list):
            items_completed = items_value
        else:
            items_completed = items_value.split(",") if items_value else []
        
        # Parse issued date
        issued_date_str = certificate_data.get("issued_date")
        if issued_date_str:
            issued_date = datetime.fromisoformat(issued_date_str)
        else:
            issued_date = datetime.utcnow()
        
        return CertificateVerification(
            certificate_id=certificate_id,
            user_name=certificate_data.get("user_name", ""),
            user_email=certificate_data.get("user_email", ""),
            certificate_type=certificate_data.get("certificate_type", "track"),
            title=certificate_data.get("title", ""),
            description=certificate_data.get("description") or None,
            items_completed=items_completed,
            issued_date=issued_date,
            verification_url=verification_url,
            download_url=download_url
        )
    
    async def get_metadata(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """Get certificate metadata from storage.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Certificate metadata or None if not found
        """
        try:
            metadata = await storage_service.get_metadata(s3_key)
            if metadata:
                return metadata
        except Exception:
            return None
        
        return None


# Global verification service instance
verification_service = VerificationService()

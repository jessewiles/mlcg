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
        
        Note: Since we no longer store metadata, this method only verifies
        that the certificate file exists in storage. The actual certificate
        details should be retrieved from MLAPI's database.
        
        Args:
            certificate_id: Certificate ID to verify
            
        Returns:
            CertificateVerification if certificate exists, None otherwise
        """
        s3_key = None
        
        # Check Redis cache for S3 key
        if self.redis_client:
            cached_key = self.redis_client.get(f"cert:{certificate_id}")
            if cached_key:
                s3_key = cached_key
        
        # If not in cache, construct expected key
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
                        # Try a few more months back (up to 3 months)
                        for months_back in range(2, 4):
                            test_date = datetime.utcnow()
                            for _ in range(months_back):
                                if test_date.month == 1:
                                    test_date = test_date.replace(year=test_date.year - 1, month=12)
                                else:
                                    test_date = test_date.replace(month=test_date.month - 1)
                            s3_key = f"certificates/{test_date.year}/{test_date.month:02d}/{certificate_id}.pdf"
                            exists = await storage_service.certificate_exists(s3_key)
                            if exists:
                                break
                        if not exists:
                            return None
                else:
                    return None
        else:
            # Verify the cached key still exists
            exists = await storage_service.certificate_exists(s3_key)
            if not exists:
                # Clear invalid cache entry
                if self.redis_client:
                    self.redis_client.delete(f"cert:{certificate_id}")
                return None
        
        # Certificate exists - generate download URL
        download_url = storage_service.get_presigned_url(s3_key)
        
        # Construct verification URL
        verification_url = f"{self.verify_base_url}/{certificate_id}"
        
        # Return basic verification info with placeholder data
        # Note: The actual certificate details (user name, course/track info, etc.)
        # should be fetched from MLAPI's database when the verification endpoint
        # is called from MLAPI
        return CertificateVerification(
            certificate_id=certificate_id,
            user_name="Certificate Holder",  # Placeholder - should be fetched from MLAPI
            user_email="certificate@microlearn.university",  # Placeholder - should be fetched from MLAPI
            certificate_type="track",  # Placeholder - should be determined from MLAPI
            title="Certificate",  # Placeholder - should be fetched from MLAPI
            description=None,
            items_completed=[],  # Should be fetched from MLAPI
            issued_date=datetime.utcnow(),  # Should be fetched from MLAPI
            verification_url=verification_url,
            download_url=download_url
        )


# Global verification service instance
verification_service = VerificationService()

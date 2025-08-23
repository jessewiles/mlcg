"""Tests for certificate verification."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.models import CertificateVerification, CertificateType
from app.services.verification import VerificationService


@pytest.fixture
def verification_service():
    """Create a verification service for testing."""
    return VerificationService()


@pytest.fixture
def sample_metadata():
    """Sample certificate metadata."""
    return {
        "user_name": "Test User",
        "user_email": "test@example.com",
        "certificate_type": "track",
        "title": "Python Mastery Track",
        "description": "Successfully completed all courses in this track",
        "items_completed": ["Python Basics", "Advanced Python"],
        "issued_date": datetime.utcnow().isoformat(),
    }


@pytest.mark.asyncio
async def test_verify_certificate_success(
    verification_service, sample_metadata, client
):
    """Test successful certificate verification."""
    certificate_id = "TRACK-TEST-123"
    s3_key = f"certificates/2025/08/{certificate_id}.pdf"
    
    # Mock storage service (patch where it's used)
    with patch("app.services.verification.storage_service") as mock_storage:
        # Mock certificate existence check
        mock_storage.certificate_exists = AsyncMock(return_value=True)
        
        # Mock presigned URL generation
        mock_storage.get_presigned_url.return_value = "https://example.com/cert.pdf"
        
        # Verify certificate
        verification = await verification_service.verify_certificate(certificate_id)
        
        # Check result - now we only verify that the certificate exists
        # and return placeholder data (actual data should come from MLAPI)
        assert verification is not None
        assert verification.certificate_id == certificate_id
        assert verification.user_name == "Certificate Holder"  # Placeholder
        assert verification.user_email == "certificate@microlearn.university"  # Placeholder
        assert verification.certificate_type == CertificateType.TRACK  # Default placeholder
        assert verification.title == "Certificate"  # Placeholder
        assert verification.items_completed == []  # Empty placeholder
        # In development this may be localhost; in prod it will be tracks.microlearn.*
        assert verification.verification_url.endswith(f"/verify/{certificate_id}")
        assert verification.download_url == "https://example.com/cert.pdf"


@pytest.mark.asyncio
async def test_verify_certificate_not_found(verification_service):
    """Test verification of non-existent certificate."""
    # Mock storage service (patch where it's used)
    with patch("app.services.verification.storage_service") as mock_storage:
        # Mock certificate existence check
        mock_storage.certificate_exists = AsyncMock(return_value=False)
        
        # Verify non-existent certificate
        verification = await verification_service.verify_certificate("INVALID-123")
        
        # Check result
        assert verification is None


@pytest.mark.asyncio
async def test_verify_certificate_api(client, sample_metadata):
    """Test certificate verification API endpoint."""
    certificate_id = "TRACK-TEST-123"
    
    # Mock verification service (patch the instance used by the endpoint)
    with patch("app.api.endpoints.verification_service") as mock_service:
        # Mock successful verification
        mock_service.verify_certificate = AsyncMock(
            return_value=CertificateVerification(
                certificate_id=certificate_id,
                user_name=sample_metadata["user_name"],
                user_email=sample_metadata["user_email"],
                certificate_type=CertificateType.TRACK,
                title=sample_metadata["title"],
                description=sample_metadata["description"],
                items_completed=sample_metadata["items_completed"],
                issued_date=datetime.fromisoformat(sample_metadata["issued_date"]),
                verification_url=f"https://tracks.microlearn.university/verify/{certificate_id}",
                download_url="https://example.com/cert.pdf"
            )
        )
        
        # Test successful verification
        response = client.get(f"/api/v1/certificates/{certificate_id}/verify", headers={"Accept": "application/json"})
        assert response.status_code == 200
        data = response.json()
        assert data["certificate_id"] == certificate_id
        assert data["user_name"] == sample_metadata["user_name"]
        assert data["certificate_type"] == "track"
        assert "verification_url" in data
        assert "download_url" in data
        
        # Test non-existent certificate
        mock_service.verify_certificate = AsyncMock(return_value=None)
        response = client.get("/api/v1/certificates/INVALID-123/verify", headers={"Accept": "application/json"})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

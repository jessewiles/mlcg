"""Tests for API endpoints."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "certificate-generation-service"
    assert "dependencies" in data


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["service"] == "certificate-generation-service"


@patch("app.api.endpoints.redis_client")
@patch("app.services.storage.storage_service.get_presigned_url")
@patch(
    "app.services.storage.storage_service.upload_certificate", new_callable=AsyncMock
)
@patch(
    "app.services.generator.certificate_generator.generate_certificate",
    new_callable=AsyncMock,
)
def test_generate_certificate(
    mock_generate,
    mock_upload,
    mock_presigned_url,
    mock_redis,
    client,
    sample_certificate_request,
):
    """Test certificate generation endpoint."""
    # Mock Redis to return None (no cache)
    mock_redis.get.return_value = None

    # Mock the certificate generation
    mock_generate.return_value = b"PDF content"
    mock_upload.return_value = "certificates/2024/01/TEST-CERT-001.pdf"
    mock_presigned_url.return_value = (
        "https://example.com/certificates/TEST-CERT-001.pdf"
    )

    response = client.post(
        "/api/v1/certificates/generate", json=sample_certificate_request
    )

    assert response.status_code == 200
    data = response.json()
    assert data["certificate_id"] == "TEST-CERT-001"
    assert "s3_key" in data
    assert "public_url" in data
    assert data["status"] == "completed"


@patch("app.services.storage.storage_service.get_presigned_url")
@patch(
    "app.services.storage.storage_service.upload_certificate", new_callable=AsyncMock
)
@patch(
    "app.services.generator.certificate_generator.generate_certificate",
    new_callable=AsyncMock,
)
def test_batch_certificate_generation_sync(
    mock_generate, mock_upload, mock_presigned_url, client, sample_batch_request
):
    """Test batch certificate generation (synchronous)."""
    # Mock the certificate generation
    mock_generate.return_value = b"PDF content"
    mock_upload.return_value = "certificates/2024/01/cert.pdf"
    mock_presigned_url.return_value = "https://example.com/certificates/cert.pdf"

    response = client.post("/api/v1/certificates/batch", json=sample_batch_request)

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["total_certificates"] == 2
    assert data["status"] == "completed"
    assert len(data["certificates"]) == 2


@patch("app.api.endpoints.redis_client")
def test_batch_certificate_generation_async(mock_redis, client):
    """Test batch certificate generation (asynchronous)."""
    # Mock Redis client
    mock_redis.hset.return_value = True

    request = {
        "certificates": [
            {
                "user_name": "Test User",
                "user_email": "test@example.com",
                "certificate_type": "course",
                "title": "Test Course",
            }
        ],
        "async_processing": True,
    }

    response = client.post("/api/v1/certificates/batch", json=request)

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "queued"
    assert data["certificates"] is None


@pytest.mark.skip(reason="Pending implementation of certificate status endpoint")
@patch("app.services.storage.storage_service.get_presigned_url")
@patch(
    "app.services.storage.storage_service.certificate_exists", new_callable=AsyncMock
)
def test_get_certificate_status_found(mock_exists, mock_presigned_url, client):
    """Test getting certificate status when certificate exists."""
    # Mock async method properly
    mock_exists.return_value = True
    mock_presigned_url.return_value = "https://example.com/certificates/CERT-123.pdf"

    response = client.get("/api/v1/certificates/CERT-123")

    assert response.status_code == 200
    data = response.json()
    assert data["certificate_id"] == "CERT-123"
    assert data["status"] == "completed"


@pytest.mark.skip(reason="Pending implementation of certificate status endpoint")
@patch(
    "app.services.storage.storage_service.certificate_exists", new_callable=AsyncMock
)
def test_get_certificate_status_not_found(mock_exists, client):
    """Test getting certificate status when certificate doesn't exist."""
    # Mock async method properly
    mock_exists.return_value = False

    response = client.get("/api/v1/certificates/CERT-NOTFOUND")

    assert response.status_code == 200
    data = response.json()
    assert data["certificate_id"] == "CERT-NOTFOUND"
    assert data["status"] == "not_found"
    assert data["error_message"] == "Certificate not found"


def test_invalid_certificate_request(client):
    """Test certificate generation with invalid data."""
    invalid_request = {
        "user_name": "",  # Empty name
        "certificate_type": "invalid",  # Invalid type
    }

    response = client.post("/api/v1/certificates/generate", json=invalid_request)

    assert response.status_code == 422  # Validation error

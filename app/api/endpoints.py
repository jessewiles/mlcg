"""API endpoints for certificate generation."""

import uuid
from datetime import datetime
from typing import Any

import redis
from fastapi import APIRouter, HTTPException, status
from prometheus_client import Counter, Histogram

from app.config import settings
from app.models import (
    BatchCertificateRequest,
    BatchCertificateResponse,
    CertificateRequest,
    CertificateResponse,
    CertificateStatus,
    CertificateVerification,
    HealthResponse,
)
from app.services.generator import certificate_generator
from app.services.storage import storage_service
from app.services.verification import verification_service

# Create router
router = APIRouter(prefix=settings.api_prefix, tags=["certificates"])

# Metrics
certificates_generated = Counter(
    "certificates_generated_total",
    "Total number of certificates generated",
    ["certificate_type"],
)

generation_duration = Histogram(
    "certificate_generation_duration_seconds", "Time spent generating certificates"
)

# Redis client for caching (optional)
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
except Exception:
    redis_client = None


@router.post("/certificates/generate", response_model=CertificateResponse)
async def generate_certificate(request: CertificateRequest) -> CertificateResponse:
    """Generate a new certificate.

    Args:
        request: Certificate generation request

    Returns:
        Certificate response with download URL
    """
    try:
        # Generate certificate ID if not provided
        if not request.certificate_id:
            request.certificate_id = f"CERT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        # Check cache first
        if redis_client:
            cached_url = redis_client.get(f"cert:{request.certificate_id}")
            if cached_url:
                return CertificateResponse(
                    certificate_id=request.certificate_id,
                    s3_key=f"certificates/{request.certificate_id}.pdf",
                    public_url=cached_url,
                    generated_at=datetime.utcnow(),
                    status="cached",
                )

        # Generate certificate PDF
        with generation_duration.time():
            pdf_data = await certificate_generator.generate_certificate(request)

        # Upload to storage with metadata
        metadata = {
            "user_name": request.user_name,
            "user_email": request.user_email,
            "certificate_type": request.certificate_type.value,
            "title": request.title,
            "description": request.description or "",
            "items_completed": ",".join(request.items_completed) if request.items_completed else "",
            "issued_date": request.issued_date.isoformat() if request.issued_date else datetime.utcnow().isoformat(),
        }
        s3_key = await storage_service.upload_certificate(
            pdf_data, request.certificate_id, request.user_email, metadata
        )

        # Cache the S3 key
        if redis_client:
            redis_client.setex(
                f"cert:{request.certificate_id}", settings.redis_ttl, s3_key
            )

        # Update metrics
        certificates_generated.labels(
            certificate_type=request.certificate_type.value
        ).inc()

        # Generate presigned URL for immediate download
        presigned_url = storage_service.get_presigned_url(s3_key)

        return CertificateResponse(
            certificate_id=request.certificate_id,
            s3_key=s3_key,
            public_url=presigned_url,
            generated_at=datetime.utcnow(),
            status="completed",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate certificate: {str(e)}",
        )


@router.post("/certificates/batch", response_model=BatchCertificateResponse)
async def generate_batch_certificates(
    request: BatchCertificateRequest,
) -> BatchCertificateResponse:
    """Generate multiple certificates.

    Args:
        request: Batch certificate generation request

    Returns:
        Batch response with job ID or certificates
    """
    try:
        job_id = f"BATCH-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        if request.async_processing:
            # Queue for async processing (would use Celery in production)
            # For now, we'll just return the job ID
            if redis_client:
                # Store job info in Redis
                redis_client.hset(
                    f"batch:{job_id}",
                    mapping={
                        "total": len(request.certificates),
                        "status": "queued",
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )

            return BatchCertificateResponse(
                job_id=job_id,
                total_certificates=len(request.certificates),
                status="queued",
                created_at=datetime.utcnow(),
            )
        else:
            # Process synchronously
            generated_certificates = []

            for cert_request in request.certificates:
                # Generate each certificate
                if not cert_request.certificate_id:
                    cert_request.certificate_id = f"CERT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

                pdf_data = await certificate_generator.generate_certificate(
                    cert_request
                )

                # Upload to storage
                s3_key = await storage_service.upload_certificate(
                    pdf_data, cert_request.certificate_id, cert_request.user_email
                )

                # Generate presigned URL
                presigned_url = storage_service.get_presigned_url(s3_key)

                generated_certificates.append(
                    CertificateResponse(
                        certificate_id=cert_request.certificate_id,
                        s3_key=s3_key,
                        public_url=presigned_url,
                        generated_at=datetime.utcnow(),
                        status="completed",
                    )
                )

                # Update metrics
                certificates_generated.labels(
                    certificate_type=cert_request.certificate_type.value
                ).inc()

            return BatchCertificateResponse(
                job_id=job_id,
                total_certificates=len(request.certificates),
                status="completed",
                created_at=datetime.utcnow(),
                certificates=generated_certificates,
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate batch certificates: {str(e)}",
        )


# Moved API endpoint to better reflect resource hierarchy
@router.get("/certificates/{certificate_id}/verify", response_model=CertificateVerification)
async def verify_certificate(certificate_id: str) -> CertificateVerification:
    """Verify the authenticity of a certificate.

    Args:
        certificate_id: Certificate ID to verify

    Returns:
        Certificate verification details
    """
    verification = await verification_service.verify_certificate(certificate_id)
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found or invalid."
        )
    return verification


@router.get("/certificates/{certificate_id}/download-url")
async def get_certificate_download_url(certificate_id: str) -> dict[str, Any]:
    """Get a fresh presigned URL for downloading a certificate.

    Args:
        certificate_id: Certificate ID

    Returns:
        Dictionary with presigned download URL
    """
    try:
        # Check cache for S3 key
        s3_key = None
        if redis_client:
            s3_key = redis_client.get(f"cert:{certificate_id}")

        # If not in cache, construct the expected key
        if not s3_key:
            now = datetime.utcnow()
            s3_key = f"certificates/{now.year}/{now.month:02d}/{certificate_id}.pdf"

        # Check if certificate exists in storage
        exists = await storage_service.certificate_exists(s3_key)

        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found"
            )

        # Generate fresh presigned URL (valid for 1 hour)
        presigned_url = storage_service.get_presigned_url(s3_key, expiration=3600)

        return {
            "certificate_id": certificate_id,
            "download_url": presigned_url,
            "expires_in": 3600,  # seconds
            "generated_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}",
        )


@router.get("/certificates/{certificate_id}", response_model=CertificateStatus)
async def get_certificate_status(certificate_id: str) -> CertificateStatus:
    """Get certificate status and download URL.

    Args:
        certificate_id: Certificate ID

    Returns:
        Certificate status information
    """
    try:
        # Check cache for S3 key
        s3_key = None
        if redis_client:
            s3_key = redis_client.get(f"cert:{certificate_id}")

        # If not in cache, construct the expected key
        if not s3_key:
            now = datetime.utcnow()
            s3_key = f"certificates/{now.year}/{now.month:02d}/{certificate_id}.pdf"

        # Check if certificate exists in storage
        exists = await storage_service.certificate_exists(s3_key)

        if exists:
            # Generate fresh presigned URL
            presigned_url = storage_service.get_presigned_url(s3_key)

            return CertificateStatus(
                certificate_id=certificate_id,
                status="completed",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                download_url=presigned_url,
            )
        else:
            return CertificateStatus(
                certificate_id=certificate_id,
                status="not_found",
                error_message="Certificate not found",
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get certificate status: {str(e)}",
        )


@router.get("/batch/{job_id}", response_model=dict)
async def get_batch_status(job_id: str) -> dict:
    """Get batch job status.

    Args:
        job_id: Batch job ID

    Returns:
        Batch job status
    """
    try:
        if not redis_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis not available",
            )

        job_info = redis_client.hgetall(f"batch:{job_id}")

        if not job_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Batch job not found"
            )

        return job_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get batch status: {str(e)}",
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Service health status
    """
    dependencies = {}

    # Check Redis
    if redis_client:
        try:
            redis_client.ping()
            dependencies["redis"] = "healthy"
        except Exception:
            dependencies["redis"] = "unhealthy"
    else:
        dependencies["redis"] = "not_configured"

    # Check S3
    try:
        # This would normally check S3 connectivity
        # For now, we'll just check if credentials are configured
        if settings.aws_access_key_id:
            dependencies["s3"] = "configured"
        else:
            dependencies["s3"] = "not_configured"
    except Exception:
        dependencies["s3"] = "error"

    return HealthResponse(
        status="healthy",
        service=settings.service_name,
        version="0.1.0",
        timestamp=datetime.utcnow(),
        dependencies=dependencies,
    )

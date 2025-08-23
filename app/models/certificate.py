"""Pydantic models for certificate API."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class CertificateType(str, Enum):
    """Certificate type enumeration."""
    TRACK = "track"
    COURSE = "course"
    ACHIEVEMENT = "achievement"


class CertificateRequest(BaseModel):
    """Request model for certificate generation."""
    
    user_name: str = Field(..., min_length=1, max_length=200, description="Name of the certificate recipient")
    user_email: EmailStr = Field(..., description="Email of the certificate recipient")
    certificate_type: CertificateType = Field(..., description="Type of certificate to generate")
    title: str = Field(..., min_length=1, max_length=500, description="Certificate title")
    description: Optional[str] = Field(None, max_length=2000, description="Certificate description")
    items_completed: List[str] = Field(default_factory=list, description="List of completed items")
    issued_date: Optional[datetime] = Field(None, description="Date of issuance")
    certificate_id: Optional[str] = Field(None, description="Unique certificate identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "user_name": "John Doe",
                "user_email": "john.doe@example.com",
                "certificate_type": "track",
                "title": "Python Mastery Track",
                "description": "Successfully completed all courses in the Python Mastery track",
                "items_completed": ["Python Basics", "Advanced Python", "Python Web Development"],
                "issued_date": "2024-01-15T10:00:00Z",
                "certificate_id": "CERT-2024-001",
                "metadata": {
                    "instructor": "Jane Smith",
                    "duration_hours": 40
                }
            }
        }


class CertificateResponse(BaseModel):
    """Response model for certificate generation."""
    
    certificate_id: str = Field(..., description="Unique certificate identifier")
    s3_key: str = Field(..., description="S3 object key")
    public_url: str = Field(..., description="Public URL for certificate download")
    generated_at: datetime = Field(..., description="Timestamp of generation")
    status: str = Field(default="completed", description="Generation status")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "certificate_id": "CERT-2024-001",
                "s3_key": "certificates/2024/01/CERT-2024-001.pdf",
                "public_url": "https://certificates.example.com/certificates/2024/01/CERT-2024-001.pdf",
                "generated_at": "2024-01-15T10:00:30Z",
                "status": "completed"
            }
        }


class BatchCertificateRequest(BaseModel):
    """Request model for batch certificate generation."""
    
    certificates: List[CertificateRequest] = Field(..., min_items=1, max_items=100, description="List of certificates to generate")
    async_processing: bool = Field(default=True, description="Process certificates asynchronously")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "certificates": [
                    {
                        "user_name": "John Doe",
                        "user_email": "john.doe@example.com",
                        "certificate_type": "course",
                        "title": "Python Basics",
                        "certificate_id": "CERT-2024-001"
                    },
                    {
                        "user_name": "Jane Smith",
                        "user_email": "jane.smith@example.com",
                        "certificate_type": "course",
                        "title": "Python Basics",
                        "certificate_id": "CERT-2024-002"
                    }
                ],
                "async_processing": True
            }
        }


class BatchCertificateResponse(BaseModel):
    """Response model for batch certificate generation."""
    
    job_id: str = Field(..., description="Batch job identifier")
    total_certificates: int = Field(..., description="Total number of certificates to generate")
    status: str = Field(..., description="Batch job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    certificates: Optional[List[CertificateResponse]] = Field(None, description="Generated certificates (if sync processing)")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "job_id": "BATCH-2024-001",
                "total_certificates": 2,
                "status": "processing",
                "created_at": "2024-01-15T10:00:00Z",
                "certificates": None
            }
        }


class CertificateStatus(BaseModel):
    """Model for certificate status information."""
    
    certificate_id: str = Field(..., description="Certificate identifier")
    status: str = Field(..., description="Current status")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    download_url: Optional[str] = Field(None, description="Download URL if completed")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "certificate_id": "CERT-2024-001",
                "status": "completed",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:30Z",
                "error_message": None,
                "download_url": "https://certificates.example.com/certificates/2024/01/CERT-2024-001.pdf"
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Current timestamp")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependency status")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "certificate-generation-service",
                "version": "0.1.0",
                "timestamp": "2024-01-15T10:00:00Z",
                "dependencies": {
                    "redis": "connected",
                    "s3": "connected"
                }
            }
        }


class CertificateVerification(BaseModel):
    """Model for certificate verification."""
    
    certificate_id: str = Field(..., description="Certificate identifier")
    user_name: str = Field(..., description="Name of the certificate recipient")
    user_email: EmailStr = Field(..., description="Email of the certificate recipient")
    certificate_type: CertificateType = Field(..., description="Type of certificate")
    title: str = Field(..., description="Certificate title")
    description: Optional[str] = Field(None, description="Certificate description")
    items_completed: List[str] = Field(default_factory=list, description="List of completed items")
    issued_date: datetime = Field(..., description="Date of issuance")
    verification_url: str = Field(..., description="URL where certificate can be verified")
    download_url: Optional[str] = Field(None, description="URL to download the certificate")
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "certificate_id": "TRACK-2024-001",
                "user_name": "John Doe",
                "user_email": "john.doe@example.com",
                "certificate_type": "track",
                "title": "Python Mastery Track",
                "description": "Successfully completed all courses in the Python Mastery track",
                "items_completed": ["Python Basics", "Advanced Python", "Python Web Development"],
                "issued_date": "2024-01-15T10:00:00Z",
                "verification_url": "https://tracks.microlearn.university/verify/TRACK-2024-001",
                "download_url": "https://certificates.example.com/certificates/2024/01/TRACK-2024-001.pdf"
            }
        }

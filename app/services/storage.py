"""Storage service for certificate files."""

import io
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.config import settings


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def upload(self, file_data: bytes, key: str, content_type: str = "application/pdf") -> str:
        """Upload file to storage.
        
        Args:
            file_data: File data as bytes
            key: Storage key/path
            content_type: MIME type of the file
            
        Returns:
            Storage key
        """
        pass
    
    @abstractmethod
    async def download(self, key: str) -> bytes | None:
        """Download file from storage.
        
        Args:
            key: Storage key/path
            
        Returns:
            File data as bytes or None if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete file from storage.
        
        Args:
            key: Storage key/path
            
        Returns:
            True if deleted successfully
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if file exists in storage.
        
        Args:
            key: Storage key/path
            
        Returns:
            True if file exists
        """
        pass
    
    @abstractmethod
    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """Get metadata from storage.
        
        Args:
            key: Storage key/path
            
        Returns:
            Metadata dictionary or None if not found
        """
        pass


class S3Storage(StorageBackend):
    """AWS S3 storage backend."""
    
    def __init__(self):
        """Initialize S3 client."""
        self.bucket_name = settings.s3_bucket_name
        
        # Create S3 client
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            endpoint_url=settings.s3_endpoint_url,  # For LocalStack testing
        )
        
        # Create S3 resource for presigned URLs
        self.s3_resource = boto3.resource(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
            endpoint_url=settings.s3_endpoint_url,
        )
    
    async def upload(self, file_data: bytes, key: str, content_type: str = "application/pdf") -> str:
        """Upload file to S3.
        
        Returns:
            S3 object key
        """
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type,
                Metadata={
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "service": settings.service_name,
                }
            )
            
            return key
            
        except NoCredentialsError:
            raise ValueError("AWS credentials not configured")
        except ClientError as e:
            raise ValueError(f"Failed to upload to S3: {e}")
    
    async def download(self, key: str) -> bytes | None:
        """Download file from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response["Body"].read()
            
        except self.s3_client.exceptions.NoSuchKey:
            return None
        except ClientError as e:
            raise ValueError(f"Failed to download from S3: {e}")
    
    async def delete(self, key: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
            
        except ClientError:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
            
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except ClientError:
            return False
    
    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """Get metadata from S3 object."""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response.get('Metadata', {})
        except (self.s3_client.exceptions.NoSuchKey, ClientError):
            return None
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for downloading.
        
        Args:
            key: S3 object key
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise ValueError(f"Failed to generate presigned URL: {e}")


class LocalStorage(StorageBackend):
    """Local file system storage backend."""
    
    def __init__(self):
        """Initialize local storage."""
        self.base_path = Path(settings.local_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def upload(self, file_data: bytes, key: str, content_type: str = "application/pdf") -> str:
        """Save file to local storage."""
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(file_data)
        
        return str(key)
    
    async def download(self, key: str) -> bytes | None:
        """Read file from local storage."""
        file_path = self.base_path / key
        
        if not file_path.exists():
            return None
        
        with open(file_path, "rb") as f:
            return f.read()
    
    async def delete(self, key: str) -> bool:
        """Delete file from local storage."""
        file_path = self.base_path / key
        
        if file_path.exists():
            file_path.unlink()
            return True
        
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if file exists in local storage."""
        file_path = self.base_path / key
        return file_path.exists()
    
    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """Get metadata from local file."""
        # For local storage, we'll store metadata in a parallel .meta file
        file_path = self.base_path / f"{key}.meta"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                import json
                return json.load(f)
        except Exception:
            return None


class StorageService:
    """Storage service with backend abstraction."""
    
    def __init__(self):
        """Initialize storage service with configured backend."""
        if settings.storage_backend == "s3":
            self.backend = S3Storage()
        elif settings.storage_backend == "local":
            self.backend = LocalStorage()
        else:
            raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")
    
    async def upload_certificate(
        self,
        pdf_data: bytes,
        certificate_id: str,
        user_email: str,
        metadata: dict[str, Any] | None = None
    ) -> str:
        """Upload certificate to storage.
        
        Args:
            pdf_data: Certificate PDF data
            certificate_id: Unique certificate ID
            user_email: User email for organization
            
        Returns:
            Storage key
        """
        # Generate storage key with date-based organization
        now = datetime.utcnow()
        key = f"certificates/{now.year}/{now.month:02d}/{certificate_id}.pdf"
        
        # If we're using S3 and have metadata, upload with metadata
        if isinstance(self.backend, S3Storage) and metadata:
            try:
                self.backend.s3_client.put_object(
                    Bucket=self.backend.bucket_name,
                    Key=key,
                    Body=pdf_data,
                    ContentType="application/pdf",
                    Metadata={
                        "uploaded_at": now.isoformat(),
                        "service": settings.service_name,
                        **{k: str(v) if v is not None else "" for k, v in metadata.items()}
                    }
                )
                return key
            except Exception as e:
                raise ValueError(f"Failed to upload with metadata: {e}")
        
        return await self.backend.upload(pdf_data, key)
    
    async def get_certificate(self, key: str) -> bytes | None:
        """Get certificate from storage.
        
        Args:
            key: Storage key
            
        Returns:
            Certificate PDF data or None
        """
        return await self.backend.download(key)
    
    async def delete_certificate(self, key: str) -> bool:
        """Delete certificate from storage.
        
        Args:
            key: Storage key
            
        Returns:
            True if deleted successfully
        """
        return await self.backend.delete(key)
    
    async def certificate_exists(self, key: str) -> bool:
        """Check if certificate exists.
        
        Args:
            key: Storage key
            
        Returns:
            True if certificate exists
        """
        return await self.backend.exists(key)
    
    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """Get certificate metadata.
        
        Args:
            key: Storage key
            
        Returns:
            Metadata dictionary or None if not found
        """
        return await self.backend.get_metadata(key)
    
    def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Get a presigned URL for downloading a certificate.
        
        Args:
            key: Storage key
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL for downloading
        """
        if isinstance(self.backend, S3Storage):
            return self.backend.generate_presigned_url(key, expiration)
        elif isinstance(self.backend, LocalStorage):
            # For local storage, return a file:// URL
            file_path = self.backend.base_path / key
            return f"file://{file_path.absolute()}"
        else:
            raise ValueError(f"Presigned URLs not supported for backend: {type(self.backend)}")


# Global storage service instance
storage_service = StorageService()

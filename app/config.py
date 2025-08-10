"""Configuration management for the Certificate Generation Microservice."""

import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get secret from file or environment variable.

    First checks for {key}_FILE environment variable pointing to a file,
    then checks for direct {key} environment variable.
    """
    # Check for file-based secret
    secret_file = os.getenv(f"{key}_FILE")
    if secret_file and os.path.exists(secret_file):
        with open(secret_file, "r") as f:
            return f.read().strip()

    # Fall back to environment variable
    return os.getenv(key, default)


class Settings(BaseSettings):
    """Application settings."""

    # Service Configuration
    service_name: str = "certificate-generation-service"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API Configuration
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8001

    # AWS Configuration
    @property
    def aws_access_key_id(self) -> Optional[str]:
        return get_secret("AWS_ACCESS_KEY_ID")

    @property
    def aws_secret_access_key(self) -> Optional[str]:
        return get_secret("AWS_SECRET_ACCESS_KEY")

    aws_region: str = "us-east-1"
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "microlearn-certificates-dev")
    s3_endpoint_url: Optional[str] = None  # For testing with LocalStack

    # Storage Configuration
    storage_backend: str = "s3"  # Options: s3, local, gcs
    local_storage_path: str = "/tmp/certificates"

    # Redis Configuration (for caching and Celery)
    redis_url: str = "redis://localhost:6379"
    redis_ttl: int = 3600  # Cache TTL in seconds

    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False  # Set True for testing

    # Service URLs
    mlapi_url: str = "http://localhost:8000"

    # Certificate Generation Settings
    certificate_dpi: int = 300
    certificate_page_size: str = "Letter"  # Letter or A4
    default_font: str = "Helvetica"
    default_font_size: int = 12

    # Security
    api_key: Optional[str] = None
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # In seconds

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Create a global settings instance
settings = get_settings()

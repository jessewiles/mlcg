# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is the Certificate Generation Microservice (MLCG) for the MicroLearn platform. It's a FastAPI-based service that generates PDF certificates using ReportLab, with support for S3/local storage, Redis caching, and async processing via Celery.

## Development Commands

### Initial Setup
```bash
# Install dependencies with Poetry
poetry install

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration
```

### Running the Service

**IMPORTANT**: The service is typically run as part of the MicroLearn platform via Docker Compose from the `../mldev` directory.

```bash
# PRIMARY METHOD: Run via Docker Compose from mldev directory
cd ../mldev
docker-compose up -d
cd ../mlcg  # ALWAYS return to mlcg directory after Docker commands

# View logs for the certificate service
docker-compose -f ../mldev/docker-compose.yml logs -f certificate-service

# Restart just the certificate service
cd ../mldev && docker-compose restart certificate-service && cd ../mlcg

# Alternative: Development mode with auto-reload (standalone)
poetry run uvicorn app.main:app --reload --port 8001

# Alternative: Run standalone Docker container
docker build -t mlcg .
docker run -p 8001:8001 --env-file .env mlcg
```

**Note**: When running Docker commands from mldev, ALWAYS return to the mlcg directory (`cd ../mlcg`) to maintain the correct working directory for development.

### Testing
```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/test_endpoints.py

# Run specific test
poetry run pytest tests/test_endpoints.py::test_generate_certificate

# Run tests with verbose output
poetry run pytest -v

# Run tests and stop on first failure
poetry run pytest --maxfail=1 --disable-warnings --tb=short
```

### Code Quality
```bash
# Format code with Black
poetry run black app tests

# Lint with Ruff
poetry run ruff app tests

# Type checking with MyPy
poetry run mypy app

# Run all quality checks
poetry run black app tests && poetry run ruff app tests && poetry run mypy app
```

### Dependency Management
```bash
# Add a production dependency
poetry add <package>

# Add a development dependency
poetry add --group dev <package>

# Update dependencies
poetry update

# Show dependency tree
poetry show --tree
```

## Architecture

### Service Ports
- **8001**: Default service port (configurable via PORT env)
- **8002**: Docker container exposed port
- **6379**: Redis port
- **9090**: Prometheus metrics port

### Core Components

1. **app/main.py**: FastAPI application entry point with middleware, lifespan management, and global exception handling
2. **app/config.py**: Pydantic settings management with support for file-based secrets and environment variables
3. **app/api/endpoints.py**: REST API endpoints for certificate generation and management
4. **app/services/generator.py**: PDF generation logic using ReportLab
5. **app/services/storage.py**: Storage abstraction layer supporting S3 and local filesystem
6. **app/models/certificate.py**: Pydantic models for request/response validation

### Storage Strategy
- Supports both S3 and local filesystem storage (configured via `STORAGE_BACKEND`)
- S3 configuration supports custom endpoints for LocalStack testing
- File-based secrets supported for AWS credentials (checks `AWS_ACCESS_KEY_ID_FILE` before `AWS_ACCESS_KEY_ID`)

### API Endpoints
- `POST /api/v1/certificates/generate`: Generate single certificate
- `POST /api/v1/certificates/batch`: Batch certificate generation
- `GET /api/v1/certificates/{certificate_id}`: Get certificate status
- `GET /api/v1/health`: Health check endpoint
- `GET /metrics`: Prometheus metrics (if enabled)
- `GET /docs`: Swagger UI documentation
- `GET /redoc`: ReDoc documentation

## Environment Configuration

### Critical Environment Variables
```bash
# Required for S3 storage
AWS_ACCESS_KEY_ID=<your_key>
AWS_SECRET_ACCESS_KEY=<your_secret>
S3_BUCKET_NAME=microlearn-certificates

# Storage backend selection
STORAGE_BACKEND=s3  # or "local"

# Redis configuration (required for caching)
REDIS_URL=redis://localhost:6379

# Service configuration
ENVIRONMENT=development  # or "production"
DEBUG=true  # false for production
```

### LocalStack Testing
```bash
# Use LocalStack for S3 testing
S3_ENDPOINT_URL=http://localhost:4566
```

## CI/CD Workflows

### GitHub Actions
- **tests.yml**: Runs on push/PR - executes test suite and Docker build verification
- **docker-build.yml**: Runs on main branch push - builds multi-platform Docker image and pushes to Docker Hub

### Required GitHub Secrets
- `DOCKERHUB_USERNAME`: Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token

## Integration with Other Services

### MLAPI Integration
The service is designed to be called from the main MLAPI service. Example integration:
```python
import httpx

async def generate_certificate_via_microservice(data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://certificate-service:8001/api/v1/certificates/generate",
            json=data,
            timeout=30.0
        )
        return response.json()
```

### Service Discovery
When running in Docker Compose or Kubernetes, use service names:
- From MLAPI: `http://certificate-service:8001`
- Redis: `redis://redis:6379`

## Common Development Tasks

### Adding New Certificate Types
1. Update models in `app/models/certificate.py`
2. Add generation logic in `app/services/generator.py`
3. Update API endpoints in `app/api/endpoints.py`
4. Add tests in `tests/test_endpoints.py`

### Testing with Local Files
```bash
# Set storage to local
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=/tmp/certificates

# Generated certificates will be saved to /tmp/certificates/
```

### Debugging Failed Certificate Generation
1. Check logs for detailed error messages
2. Verify storage backend configuration (S3 credentials, bucket permissions)
3. Test with local storage first to isolate storage issues
4. Use `LOG_LEVEL=DEBUG` for verbose logging

### Performance Monitoring
- Prometheus metrics available at `/metrics`
- Key metrics:
  - `certificates_generated_total`: Total certificates generated
  - `certificate_generation_duration_seconds`: Generation time histogram

## Production Deployment

### Docker Production Build
```bash
# Build with specific tag
docker build -t mlcg:v1.0.0 .

# Run with production config
docker run -d \
  --name mlcg \
  -p 8001:8001 \
  --env-file .env.production \
  mlcg:v1.0.0
```

### Required Production Settings
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
STORAGE_BACKEND=s3
RATE_LIMIT_ENABLED=true
ENABLE_METRICS=true
```

## Troubleshooting

### Redis Connection Issues
```bash
# Test Redis connection
redis-cli ping

# Check Redis is running
docker ps | grep redis

# View Redis logs
docker logs mlcg-redis
```

### S3 Upload Failures
```bash
# Test S3 credentials
aws s3 ls s3://microlearn-certificates/ --profile your-profile

# Test with LocalStack
aws --endpoint-url=http://localhost:4566 s3 ls
```

### Certificate Generation Failures
- Check ReportLab is installed: `poetry show reportlab`
- Verify font settings in config
- Test with simple certificate first
- Check disk space for local storage

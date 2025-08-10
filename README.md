# Certificate Generation Microservice (MLCG)

A FastAPI-based microservice for generating PDF certificates for the MicroLearn platform.

## Features

- **PDF Certificate Generation**: Generate professional PDF certificates using ReportLab
- **Multiple Certificate Types**: Support for collection, course, and achievement certificates
- **Batch Processing**: Generate multiple certificates in a single request
- **Storage Abstraction**: Support for S3 and local file storage
- **Caching**: Redis-based caching for improved performance
- **Monitoring**: Prometheus metrics and health checks
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## Tech Stack

- **Framework**: FastAPI
- **PDF Generation**: ReportLab
- **Storage**: AWS S3 / Local filesystem
- **Caching**: Redis
- **Container**: Docker
- **Package Management**: Poetry

## Installation

### Using Poetry (Development)

```bash
# Install dependencies
poetry install

# Run the application
poetry run uvicorn app.main:app --reload --port 8001
```

### Using Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run manually
docker build -t mlcg .
docker run -p 8001:8001 mlcg
```

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Storage
STORAGE_BACKEND=local  # or "s3"
LOCAL_STORAGE_PATH=/tmp/certificates

# AWS (if using S3)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=microlearn-certificates

# Redis
REDIS_URL=redis://localhost:6379
REDIS_TTL=3600

# API
API_PREFIX=/api/v1
HOST=0.0.0.0
PORT=8001
```

## API Endpoints

### Generate Certificate
```http
POST /api/v1/certificates/generate
Content-Type: application/json

{
  "user_name": "John Doe",
  "user_email": "john.doe@example.com",
  "certificate_type": "collection",
  "title": "Python Mastery Collection",
  "description": "Successfully completed all courses",
  "items_completed": ["Python Basics", "Advanced Python"],
  "certificate_id": "CERT-2024-001"
}
```

### Batch Generate Certificates
```http
POST /api/v1/certificates/batch
Content-Type: application/json

{
  "certificates": [
    {
      "user_name": "John Doe",
      "user_email": "john@example.com",
      "certificate_type": "course",
      "title": "Python Basics"
    }
  ],
  "async_processing": false
}
```

### Get Certificate Status
```http
GET /api/v1/certificates/{certificate_id}
```

### Health Check
```http
GET /api/v1/health
```

## API Documentation

Once the service is running, you can access:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc
- OpenAPI JSON: http://localhost:8001/openapi.json

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/test_generator.py
```

### Code Quality

```bash
# Format code
poetry run black app tests

# Lint code
poetry run ruff app tests

# Type checking
poetry run mypy app
```

## Project Structure

```
mlcg/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py                # Configuration management
│   ├── models/
│   │   ├── __init__.py
│   │   └── certificate.py      # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── generator.py        # Certificate generation
│   │   └── storage.py          # Storage abstraction
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py        # API endpoints
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_*.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── .env.example
```

## Monitoring

### Prometheus Metrics

The service exposes Prometheus metrics at `/metrics`:

- `certificates_generated_total`: Total number of certificates generated
- `certificate_generation_duration_seconds`: Time spent generating certificates

### Health Check

The `/api/v1/health` endpoint provides:
- Service status
- Dependency health (Redis, S3)
- Version information

## Deployment

### Environment Variables for Production

```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
STORAGE_BACKEND=s3
RATE_LIMIT_ENABLED=true
ENABLE_METRICS=true
```

### Docker Production Build

```dockerfile
docker build -t mlcg:latest .
docker run -d \
  --name mlcg \
  -p 8001:8001 \
  --env-file .env.production \
  mlcg:latest
```

## Integration with MLAPI

To integrate with the main MLAPI service:

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

## License

Copyright (c) 2024 MicroLearn

## Support

For issues and questions, please create an issue in the repository.

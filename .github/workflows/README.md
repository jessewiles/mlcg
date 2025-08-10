# GitHub Actions Workflows

This directory contains GitHub Actions workflows for the mlcg service.

## Workflows

### 1. Testing (`tests.yml`)
- **Trigger**: On push to main and on pull requests
- **Purpose**: Runs the test suite and verifies Docker build
- **Actions**:
  - Sets up Python 3.11
  - Installs Poetry and dependencies
  - Runs pytest test suite
  - Verifies Docker image builds successfully

### 2. Docker Build and Push (`docker-build.yml`)
- **Trigger**: On push to main branch
- **Purpose**: Builds and pushes Docker images to Docker Hub
- **Actions**:
  - Builds multi-platform Docker image
  - Tags with:
    - `latest`
    - Full commit SHA
    - Versioned release tag (format: `v-YYYY.MM.DD.N-SHA`)
  - Pushes to Docker Hub
  - Creates GitHub release with generated tag

## Required Secrets

These secrets must be configured in the GitHub repository settings under Settings → Secrets and variables → Actions:

- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token (not password)

## Required Environment

The Docker build workflow requires a GitHub environment named `microlearn` to be configured in the repository settings.

## Docker Hub Setup

1. Create a Docker Hub account if you don't have one
2. Generate an access token:
   - Go to Docker Hub → Account Settings → Security
   - Click "New Access Token"
   - Give it a descriptive name (e.g., "GitHub Actions - mlcg")
   - Copy the token and save it as `DOCKERHUB_TOKEN` in GitHub secrets

## Local Testing

To test the workflows locally:

```bash
# Run tests
poetry run pytest tests/ --maxfail=1 --disable-warnings --tb=short

# Build Docker image
docker build -t mlcg:local .

# Run Docker container
docker run -p 8002:8002 mlcg:local
```

"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_certificate_request():
    """Sample certificate request for testing."""
    return {
        "user_name": "Test User",
        "user_email": "test@example.com",
        "certificate_type": "track",
        "title": "Python Mastery Track",
        "description": "Successfully completed all courses in the Python Mastery track",
        "items_completed": ["Python Basics", "Advanced Python", "Python Web Development"],
        "certificate_id": "TEST-CERT-001"
    }


@pytest.fixture
def sample_batch_request():
    """Sample batch certificate request for testing."""
    return {
        "certificates": [
            {
                "user_name": "User One",
                "user_email": "user1@example.com",
                "certificate_type": "course",
                "title": "Python Basics",
                "certificate_id": "TEST-CERT-002"
            },
            {
                "user_name": "User Two",
                "user_email": "user2@example.com",
                "certificate_type": "course",
                "title": "Advanced Python",
                "certificate_id": "TEST-CERT-003"
            }
        ],
        "async_processing": False
    }

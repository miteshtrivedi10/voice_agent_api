"""Tests for the main application endpoints."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_voice_session_creation():
    """Test voice session creation endpoint."""
    response = client.post("/voice?user_id=test_user&name=Test&email=test@example.com")
    assert response.status_code == 200
    data = response.json()
    assert "room_name" in data
    assert "token" in data
    assert "ws_url" in data
    assert "participant_name" in data


def test_file_upload_invalid_type():
    """Test file upload with invalid file type."""
    # Create a mock text file
    files = {"file": ("test.txt", b"test content", "text/plain")}
    response = client.post("/upload-files", files=files, data={"user_id": "test_user", "subject_name": "Math"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "Only PDF files are allowed" in data["message"]
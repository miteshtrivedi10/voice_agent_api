"""Additional tests for the authentication system."""
import pytest
from fastapi.testclient import TestClient
from main import app
from logic.auth import SupabaseJWTValidator
from unittest.mock import patch, MagicMock

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_voice_session_creation_unauthorized():
    """Test voice session creation endpoint without authentication."""
    response = client.post("/voice?name=Test&email=test@example.com")
    # Should return 403 Forbidden because no authentication token is provided
    assert response.status_code == 403


def test_file_upload_invalid_type_unauthorized():
    """Test file upload with invalid file type without authentication."""
    # Create a mock text file
    files = {"file": ("test.txt", b"test content", "text/plain")}
    response = client.post("/upload-files", files=files, data={"subject_name": "Math"})
    # Should return 403 Forbidden because no authentication token is provided
    assert response.status_code == 403


# Example of how to test with a mock token (for documentation purposes)
# This would require a valid JWT token to test properly
def test_voice_session_creation_with_mock_token():
    """Example test showing how to use authentication (mocked)."""
    # This is just an example of how you would test with a token
    # In a real test, you would need a valid JWT token
    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/voice?name=Test&email=test@example.com", headers=headers)
    # This will fail because the token is not valid, but it shows the pattern
    assert response.status_code == 401
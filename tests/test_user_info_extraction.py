"""Tests for user information extraction from JWT tokens."""
import pytest
from fastapi.testclient import TestClient
from main import app
from logic.auth import get_user_info_from_token
from fastapi import HTTPException

client = TestClient(app)


def test_get_user_info_from_token_valid():
    """Test extracting user information from a valid token payload."""
    token_payload = {
        "aal": "aal1",
        "aud": "authenticated",
        "email": "mtrivedi@zacks.com",
        "exp": 1756394616,
        "full_name": "Mits T",
        "iat": 1756391016,
        "is_anonymous": False,
        "name": "Mits T",
        "phone": "",
        "role": "authenticated",
        "session_id": "b10b7b1a-c375-493b-a26c-3823e8210ce1",
        "sub": "8c6f4719-ad2f-4330-9f53-1a059c27d44f",
        "uid": "8c6f4719-ad2f-4330-9f53-1a059c27d44f"
    }
    
    user_info = get_user_info_from_token(token_payload)
    
    assert user_info["user_id"] == "8c6f4719-ad2f-4330-9f53-1a059c27d44f"
    assert user_info["full_name"] == "Mits T"
    assert user_info["email"] == "mtrivedi@zacks.com"


def test_get_user_info_from_token_missing_user_id():
    """Test extracting user information from a token payload missing user ID."""
    token_payload = {
        "email": "mtrivedi@zacks.com",
        "full_name": "Mits T"
    }
    
    with pytest.raises(HTTPException) as exc_info:
        get_user_info_from_token(token_payload)
    
    assert exc_info.value.status_code == 401
    assert "missing user ID" in exc_info.value.detail


def test_get_user_info_from_token_missing_full_name():
    """Test extracting user information from a token payload missing full name."""
    token_payload = {
        "email": "mtrivedi@zacks.com",
        "sub": "8c6f4719-ad2f-4330-9f53-1a059c27d44f"
    }
    
    with pytest.raises(HTTPException) as exc_info:
        get_user_info_from_token(token_payload)
    
    assert exc_info.value.status_code == 401
    assert "missing full name" in exc_info.value.detail


def test_get_user_info_from_token_missing_email():
    """Test extracting user information from a token payload missing email."""
    token_payload = {
        "full_name": "Mits T",
        "sub": "8c6f4719-ad2f-4330-9f53-1a059c27d44f"
    }
    
    with pytest.raises(HTTPException) as exc_info:
        get_user_info_from_token(token_payload)
    
    assert exc_info.value.status_code == 401
    assert "missing email" in exc_info.value.detail


def test_get_user_info_from_token_using_uid():
    """Test extracting user information using 'uid' field when 'sub' is missing."""
    token_payload = {
        "email": "mtrivedi@zacks.com",
        "full_name": "Mits T",
        "uid": "8c6f4719-ad2f-4330-9f53-1a059c27d44f"
    }
    
    user_info = get_user_info_from_token(token_payload)
    
    assert user_info["user_id"] == "8c6f4719-ad2f-4330-9f53-1a059c27d44f"
    assert user_info["full_name"] == "Mits T"
    assert user_info["email"] == "mtrivedi@zacks.com"


def test_get_user_info_from_token_using_name():
    """Test extracting user information using 'name' field when 'full_name' is missing."""
    token_payload = {
        "email": "mtrivedi@zacks.com",
        "name": "Mits T",
        "sub": "8c6f4719-ad2f-4330-9f53-1a059c27d44f"
    }
    
    user_info = get_user_info_from_token(token_payload)
    
    assert user_info["user_id"] == "8c6f4719-ad2f-4330-9f53-1a059c27d44f"
    assert user_info["full_name"] == "Mits T"
    assert user_info["email"] == "mtrivedi@zacks.com"
"""Tests for the data models."""
import pytest
from datetime import datetime
from model.dtos import FileDetails, VoiceSessionResponse


def test_voice_session_response_creation():
    """Test VoiceSessionResponse model creation."""
    session = VoiceSessionResponse(
        room_name="test_room",
        token="test_token",
        ws_url="ws://test.url",
        participant_name="test_participant"
    )
    
    assert session.room_name == "test_room"
    assert session.token == "test_token"
    assert session.ws_url == "ws://test.url"
    assert session.participant_name == "test_participant"


def test_file_details_creation():
    """Test FileDetails model creation."""
    file_details = FileDetails(
        user_id="test_user",
        file_id="test_file_id",
        file_name="test.pdf",
        subject="Math",
        file_size=1024,
        file_type="application/pdf",
        is_processed=False,
        total_generated_qna=0,
        upload_timestamp="2023-01-01 12:00:00",
        processed_timestamp="2023-01-01 12:00:00",
        user_name="test_username"  # Add the required user_name field
    )
    
    assert file_details.user_id == "test_user"
    assert file_details.file_id == "test_file_id"
    assert file_details.file_name == "test.pdf"
    assert file_details.subject == "Math"
    assert file_details.file_size == 1024
    assert file_details.file_type == "application/pdf"
    assert file_details.is_processed is False
    assert file_details.total_generated_qna == 0
    assert file_details.upload_timestamp == "2023-01-01 12:00:00"
    assert file_details.processed_timestamp == "2023-01-01 12:00:00"
    assert file_details.user_name == "test_username"  # Verify the user_name field
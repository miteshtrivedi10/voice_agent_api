"""Tests for the data models."""
import pytest
from datetime import datetime
from model.dtos import UserVoiceSessions, FileDetails


def test_user_voice_session_creation():
    """Test UserVoiceSessions model creation."""
    session = UserVoiceSessions(
        id="test_id",
        user_id="test_user",
        session_id="test_session",
        room_name="test_room",
        duration=100,
        start_time="2023-01-01 12:00:00",
        end_time="2023-01-01 12:01:00"
    )
    
    assert session.id == "test_id"
    assert session.user_id == "test_user"
    assert session.session_id == "test_session"
    assert session.room_name == "test_room"
    assert session.duration == 100
    assert session.start_time == "2023-01-01 12:00:00"
    assert session.end_time == "2023-01-01 12:01:00"


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
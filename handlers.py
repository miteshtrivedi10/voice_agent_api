"""Handler functions that connect API endpoints to service functions."""
from typing import Optional
from fastapi import UploadFile
from model.dtos import VoiceSessionResponse


async def handle_voice_session_creation(
    user_id: str, name: Optional[str] = "NA", email: Optional[str] = "NA"
) -> VoiceSessionResponse:
    """Handle voice session creation request."""
    from service import create_voice_session_service
    return await create_voice_session_service(user_id, name, email)


async def handle_file_upload(
    file: UploadFile, user_id: str, subject_name: str
):
    """Handle file upload request."""
    from service import upload_files_service
    return await upload_files_service(file, user_id, subject_name)
"""Handler functions that connect API endpoints to service functions."""
from typing import Optional
from fastapi import UploadFile
from fastapi import UploadFile
from model.dtos import VoiceSessionResponse, VoiceSessionParams, UploadFileParams
from logic.service import create_voice_session_service, upload_files_service


async def handle_voice_session_creation(params: VoiceSessionParams) -> VoiceSessionResponse:
    """Handle voice session creation request."""
    return await create_voice_session_service(params)


async def handle_file_upload(params: UploadFileParams):
    """Handle file upload request."""
    return await upload_files_service(params)
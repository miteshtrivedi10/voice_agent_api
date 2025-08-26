"""API endpoints for the voice agent service."""
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, Form
from model.dtos import FileDetails, VoiceSessionResponse, UserVoiceSessions
from service import create_voice_session_service, upload_files_service

# Create router for API endpoints
router = APIRouter()


@router.post("/voice")
async def create_voice_session(
    user_id: str, name: Optional[str] = "NA", email: Optional[str] = "NA"
) -> VoiceSessionResponse:
    """Create new voice session with WebRTC connection"""
    try:
        return await create_voice_session_service(user_id, name, email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-files")
async def upload_files(
    file: UploadFile, user_id: str = Form(...), subject_name: str = Form(...)
):
    """Upload PDF files with validation and subject name"""
    try:
        return await upload_files_service(file, user_id, subject_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""API endpoints for the voice agent service."""
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, Form, Depends
from model.dtos import FileDetails, VoiceSessionResponse, UserVoiceSessions
from logic.service import create_voice_session_service, upload_files_service
from logic.auth import get_current_user, get_user_id_from_token

# Create router for API endpoints
router = APIRouter()


@router.post("/voice")
async def create_voice_session(
    name: Optional[str] = "NA", 
    email: Optional[str] = "NA",
    token_payload: dict = Depends(get_current_user)
) -> VoiceSessionResponse:
    """Create new voice session with WebRTC connection"""
    try:
        # Extract user_id from token
        user_id = get_user_id_from_token(token_payload)
        return await create_voice_session_service(user_id, name, email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-files")
async def upload_files(
    file: UploadFile, 
    subject_name: str = Form(...),
    token_payload: dict = Depends(get_current_user)
):
    """Upload PDF files with validation and subject name"""
    try:
        # Extract user_id from token
        user_id = get_user_id_from_token(token_payload)
        return await upload_files_service(file, user_id, subject_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
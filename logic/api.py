"""API endpoints for the voice agent service."""

from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, Form, Depends
from model.dtos import VoiceSessionResponse
from logic.service import create_voice_session_service, upload_files_service
from logic.auth import get_current_user, get_user_info_from_token

# Create router for API endpoints
router = APIRouter()


@router.post("/voice")
async def create_voice_session(
    name: Optional[str] = "NA",
    email: Optional[str] = "NA",
    token_payload: dict = Depends(get_current_user),
) -> VoiceSessionResponse:
    """Create new voice session with WebRTC connection"""
    try:
        # Extract user information from token
        user_info = get_user_info_from_token(token_payload)
        user_id = user_info["user_id"]
        full_name = user_info["full_name"]
        user_email = user_info["email"]
        user_name = user_info["user_name"]  # Extract user_name from token

        # Extract session_id from token (if available)
        session_id = token_payload.get("session_id")

        # Create parameter object
        from model.dtos import VoiceSessionParams

        params = VoiceSessionParams(
            user_id=user_id,
            name=full_name,
            email=user_email,
            session_id=session_id,
            user_name=user_name,  # Include user_name in params
        )

        # Use the extracted information
        return await create_voice_session_service(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-files")
async def upload_files(
    file: UploadFile,
    subject_name: str = Form(...),
    token_payload: dict = Depends(get_current_user),
):
    """Upload PDF files with validation and subject name"""
    try:
        # Extract user information from token
        user_info = get_user_info_from_token(token_payload)
        user_id = user_info["user_id"]
        full_name = user_info["full_name"]
        user_email = user_info["email"]
        user_name = user_info["user_name"]  # Extract user_name from token

        # Create parameter object
        from model.dtos import UploadFileParams

        params = UploadFileParams(
            file=file, user_id=user_id, subject_name=subject_name, user_name=user_name
        )

        # Use the parameter object
        return await upload_files_service(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

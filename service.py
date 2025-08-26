"""Service layer for the voice agent API."""
import os
import uuid
from datetime import datetime
from typing import Optional
import asyncio
from fastapi import UploadFile
from livekit import api
from loguru import logger

from model.dtos import FileDetails, VoiceSessionResponse, UserVoiceSessions
from database.models import UserVoiceSessionsDB, FileDetailsDB
from database.repository import create_user_voice_session, create_file_details


# LiveKit configuration (imported from environment)
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "your-api-key")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "your-api-secret")


def get_today_timestamp() -> str:
    """Get today's date as a timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def insert_voice_session_async(session_data: UserVoiceSessions):
    """Asynchronously insert voice session data into database"""
    try:
        # Convert to database model
        db_session = UserVoiceSessionsDB(**session_data.model_dump())
        
        # Insert into database
        success = await create_user_voice_session(db_session)
        if success:
            logger.info(f"Successfully inserted voice session for user_id: {session_data.user_id}")
        else:
            logger.error(f"Failed to insert voice session for user_id: {session_data.user_id}")
    except Exception as e:
        logger.error(f"Error in async voice session insertion: {e}")


async def insert_file_details_async(file_data: FileDetails):
    """Asynchronously insert file details data into database"""
    try:
        # Convert to database model
        db_file = FileDetailsDB(**file_data.model_dump())
        
        # Insert into database
        success = await create_file_details(db_file)
        if success:
            logger.info(f"Successfully inserted file details for user_id: {file_data.user_id}")
        else:
            logger.error(f"Failed to insert file details for user_id: {file_data.user_id}")
    except Exception as e:
        logger.error(f"Error in async file details insertion: {e}")


async def create_voice_session_service(
    user_id: str, name: Optional[str] = "NA", email: Optional[str] = "NA"
) -> VoiceSessionResponse:
    """Service function to create new voice session with WebRTC connection"""
    logger.info(f"Creating voice session for user_id: {user_id}, name: {name}, email: {email}")

    # Generate unique room and participant
    room_name = f"voice_session_{uuid.uuid4().hex[:8]}"
    participant_name = user_id

    # Create room token
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(participant_name)
    token.with_name(participant_name)
    token.with_grants(
        api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        )
    )

    jwt_token = token.to_jwt()

    # Create UserVoiceSessions object with default values for missing fields
    session_data = UserVoiceSessions(
        id=str(uuid.uuid4()),
        user_id=user_id or "",
        session_id=room_name or "",
        room_name=room_name or "",
        duration=0,  # Default value
        start_time=get_today_timestamp(),
        end_time=""  # Default value
    )

    # Schedule async database insertion before returning response
    # This is non-blocking and won't delay the API response
    asyncio.create_task(insert_voice_session_async(session_data))

    logger.info(f"Voice session created successfully for user_id: {user_id}")
    
    return VoiceSessionResponse(
        room_name=room_name,
        token=jwt_token,
        ws_url=LIVEKIT_URL,
        participant_name=participant_name,
    )


async def upload_files_service(
    file: UploadFile, user_id: str, subject_name: str
):
    """Service function to upload PDF files with validation and subject name"""
    logger.info(f"Uploading file for user_id: {user_id}, subject: {subject_name}")
    
    # Check file type
    if file.content_type != "application/pdf":
        logger.warning(f"Invalid file type uploaded by user_id: {user_id}")
        return {"status": "error", "message": "Only PDF files are allowed"}

    file.filename = user_id + "_" + uuid.uuid4().hex[:8] + ".pdf"

    # Check file size (20MB limit)
    # Read file in chunks to check size without loading everything into memory
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    chunks = []

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_size += len(chunk)
        chunks.append(chunk)

        # Check size limit during reading
        if file_size > 20 * 1024 * 1024:  # 20MB in bytes
            logger.warning(f"File too large uploaded by user_id: {user_id}")
            return {"status": "error", "message": "File size must be 20MB or less"}

    # Reconstruct file content
    content = b"".join(chunks)

    # Save file to uploaded_files directory
    os.makedirs("uploaded_files", exist_ok=True)
    file_path = f"uploaded_files/{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # Create FileDetails object with default values for missing fields
    file_details = FileDetails(
        user_id=user_id or "",
        file_id=str(uuid.uuid4()) or "",
        file_name=file.filename or "",
        subject=subject_name or "",
        file_size=file_size,
        file_type=file.content_type or "",
        is_processed=False,  # Default value
        total_generated_qna=0,  # Default value
        upload_timestamp=get_today_timestamp(),
        processed_timestamp=get_today_timestamp(),  # Default value
    )

    # Schedule async database insertion before returning response
    # This is non-blocking and won't delay the API response
    asyncio.create_task(insert_file_details_async(file_details))

    logger.info(f"File uploaded successfully for user_id: {user_id}")
    
    return {
        "status": "success",
        "message": "File uploaded successfully",
        "file_name": file.filename,
        "user_id": user_id,
        "subject_name": subject_name,
    }
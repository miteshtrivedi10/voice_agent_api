"""Service layer for the voice agent API."""

import os
import uuid
import httpx
from datetime import datetime
from typing import Optional
import asyncio
from livekit import api
from loguru import logger

from model.dtos import (
    FileDetails,
    VoiceSessionResponse,
    UserVoiceSessions,
    VoiceSessionParams,
    GenerateEmbeddingRequest,
    GenerateEmbeddingResponse,
    QuestionAndAnswers,
    UploadFileParams,
)
from database.models import UserVoiceSessionsDB, FileDetailsDB, QuestionAndAnswersDB
from database.repository import (
    create_user_voice_session,
    create_file_details,
    create_question_and_answers,
    update_file_details,
)

# Import settings
from logic.config import settings


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
            logger.info(
                f"Successfully inserted voice session for user_id: {session_data.user_id}"
            )
        else:
            logger.error(
                f"Failed to insert voice session for user_id: {session_data.user_id}"
            )
    except Exception as e:
        logger.error(f"Error in async voice session insertion: {e}")


async def insert_file_details_async(
    file_data: FileDetails, user_name: str
):  # user_name parameter already exists
    """Asynchronously insert file details data into database and generate embeddings"""
    try:
        # Convert to database model
        db_file = FileDetailsDB(**file_data.model_dump())

        # Insert into database
        success = await create_file_details(db_file)
        if success:
            logger.info(
                f"Successfully inserted file details for user_id: {file_data.user_id}"
            )

            # Generate embeddings after successful insertion
            absolute_filepath = f"{settings.UPLOAD_DIRECTORY}/{file_data.file_name}"
            # Pass user_name to generate_embedding
            embedding_response = await generate_embedding(
                file_data, absolute_filepath, user_name
            )

            if embedding_response and embedding_response.status == "success":
                logger.info(
                    f"Embedding generation successful for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
                )

                # Process the embedding response and store Q&A pairs
                await process_embedding_response(
                    file_data, embedding_response, user_name
                )  # user_name already passed

                # Update the is_processed flag to True
                file_data.is_processed = True
                file_data.total_generated_qna = len(
                    embedding_response.question_and_answers
                )
                success = await update_file_details(
                    FileDetailsDB(**file_data.model_dump())
                )
                if success:
                    logger.info(
                        f"Successfully updated file details for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
                    )
                else:
                    logger.error(
                        f"Failed to update file details for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
                    )
            elif embedding_response:
                logger.warning(
                    f"Embedding generation failed with status: {embedding_response.status} for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
                )
            else:
                logger.error(
                    f"Embedding generation failed for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
                )
        else:
            logger.error(
                f"Failed to insert file details for user_id: {file_data.user_id}"
            )
    except Exception as e:
        logger.error(f"Error in async file details insertion: {e}")


async def generate_embedding(
    file_data: FileDetails,
    absolute_filepath: str,
    user_name: str,  # Add user_name parameter
) -> Optional[GenerateEmbeddingResponse]:
    """
    Generate embeddings for the uploaded file by calling the embedding API.

    Args:
        file_data: FileDetails object containing file information
        absolute_filepath: Absolute path to the uploaded file
        user_name: User name extracted from JWT token

    Returns:
        GenerateEmbeddingResponse: Response from the embedding API or None if failed
    """
    try:
        # Prepare the request data
        request_data = GenerateEmbeddingRequest(
            user_id=file_data.user_id,
            absolute_filepath=absolute_filepath,
            subject=file_data.subject,
            file_id=file_data.file_id,
            user_name=user_name,  # Include user_name in the request
        )

        logger.info(
            f"Calling embedding API for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
        )

        # Create HTTP client with timeout of 3 minutes (180 seconds)
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                settings.EMBEDDING_API_URL, json=request_data.model_dump()
            )

        # Check if the request was successful
        if response.status_code == 200:
            response_data = response.json()
            embedding_response = GenerateEmbeddingResponse(**response_data)

            logger.info(
                f"Embedding API successful for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
            )
            return embedding_response
        else:
            logger.error(
                f"Embedding API returned status code {response.status_code} for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
            )
            return None

    except asyncio.TimeoutError:
        logger.error(
            f"Embedding API timeout (3 minutes) for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
        )
        return None
    except Exception as e:
        logger.error(
            f"Error calling embedding API for user_id: {file_data.user_id}, file_id: {file_data.file_id}: {e}"
        )
        return None


async def process_embedding_response(
    file_data: FileDetails,
    embedding_response: GenerateEmbeddingResponse,
    user_name: str,  # Add user_name parameter
):
    """
    Process the embedding API response and store Q&A pairs in the database.

    Args:
        file_data: FileDetails object containing file information
        embedding_response: GenerateEmbeddingResponse from the embedding API
        user_name: User name extracted from JWT token
    """
    try:
        # Store Q&A pairs in the database
        for i, qna_pair in enumerate(embedding_response.question_and_answers):
            qna_data = QuestionAndAnswers(
                question_id=str(uuid.uuid4()),
                user_id=file_data.user_id,
                file_id=file_data.file_id,
                question=qna_pair.question,
                answer=qna_pair.answer,
                timestamp=get_today_timestamp(),
                user_name=user_name,  # Include user_name in the record
            )

            # Convert to database model
            db_qna = QuestionAndAnswersDB(**qna_data.model_dump())

            # Insert into database
            success = await create_question_and_answers(db_qna)
            if not success:
                logger.error(
                    f"Failed to insert Q&A pair {i} for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
                )

        logger.info(
            f"Successfully processed {len(embedding_response.question_and_answers)} Q&A pairs for user_id: {file_data.user_id}, file_id: {file_data.file_id}"
        )

    except Exception as e:
        logger.error(
            f"Error processing embedding response for user_id: {file_data.user_id}, file_id: {file_data.file_id}: {e}"
        )


async def create_voice_session_service(
    params: VoiceSessionParams,
) -> VoiceSessionResponse:
    """Service function to create new voice session with WebRTC connection"""
    logger.info(
        f"Creating voice session for user_id: {params.user_id}, name: {params.name}, email: {params.email}"
    )

    # Generate unique room and participant
    room_name = f"voice_session_{uuid.uuid4().hex[:8]}"
    # Use user_name as participant_name if available, otherwise fallback to user_id
    participant_name = params.user_name if params.user_name else params.user_id

    # Create room token
    token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    token.with_identity(participant_name)
    token.with_name(participant_name)
    token.with_metadata(f"USERID={participant_name}")
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

    # Use session_id from JWT token if available, otherwise use room_name
    session_id = params.session_id if params.session_id else room_name

    # Create UserVoiceSessions object with default values for missing fields
    session_data = UserVoiceSessions(
        id=str(uuid.uuid4()),
        user_id=params.user_id,
        session_id=session_id,
        room_name=room_name,
        duration=0,  # Default value
        start_time=get_today_timestamp(),
        end_time="",  # Default value
    )

    # Schedule async database insertion before returning response
    # This is non-blocking and won't delay the API response
    asyncio.create_task(insert_voice_session_async(session_data))

    logger.info(f"Voice session created successfully for user_id: {params.user_id}")

    return VoiceSessionResponse(
        room_name=room_name,
        token=jwt_token,
        ws_url=settings.LIVEKIT_URL,
        participant_name=participant_name,  # Use user_name as participant_name
    )


async def upload_files_service(params: UploadFileParams):
    """Service function to upload PDF files with validation and subject name"""
    logger.info(
        f"Uploading file for user_id: {params.user_id}, subject: {params.subject_name}"
    )

    # Check file type
    if params.file.content_type != "application/pdf":
        logger.warning(f"Invalid file type uploaded by user_id: {params.user_id}")
        return {"status": "error", "message": "Only PDF files are allowed"}

    params.file.filename = params.user_id + "_" + uuid.uuid4().hex[:8] + ".pdf"

    # Check file size (20MB limit)
    # Read file in chunks to check size without loading everything into memory
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    chunks = []

    while True:
        chunk = await params.file.read(chunk_size)
        if not chunk:
            break
        file_size += len(chunk)
        chunks.append(chunk)

        # Check size limit during reading
        if file_size > 20 * 1024 * 1024:  # 20MB in bytes
            logger.warning(f"File too large uploaded by user_id: {params.user_id}")
            return {"status": "error", "message": "File size must be 20MB or less"}

    # Reconstruct file content
    content = b"".join(chunks)

    # Save file to upload directory (from environment variable)
    os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
    file_path = f"{settings.UPLOAD_DIRECTORY}/{params.file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # Create FileDetails object with default values for missing fields
    file_details = FileDetails(
        user_id=params.user_id or "",
        file_id=str(uuid.uuid4()) or "",
        file_name=params.file.filename or "",
        subject=params.subject_name or "",
        file_size=file_size,
        file_type=params.file.content_type or "",
        is_processed=False,  # Default value
        total_generated_qna=0,  # Default value
        upload_timestamp=get_today_timestamp(),
        processed_timestamp=get_today_timestamp(),  # Default value
        user_name=params.user_name,  # Include user_name in the record
    )

    # Schedule async database insertion before returning response
    # This is non-blocking and won't delay the API response
    asyncio.create_task(insert_file_details_async(file_details, params.user_name))

    logger.info(f"File uploaded successfully for user_id: {params.user_id}")

    return {
        "status": "success",
        "message": "File uploaded successfully",
        "file_name": params.file.filename,
        "user_id": params.user_id,
        "subject_name": params.subject_name,
    }

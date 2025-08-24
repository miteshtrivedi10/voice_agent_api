import os
from typing import Optional
import uuid
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, Form
from livekit import api
from starlette.middleware.cors import CORSMiddleware
from model.dtos import VoiceSessionResponse

app = FastAPI(title="Voice Tutor Agent API")

_ = load_dotenv(override=True)

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "your-api-key")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "your-api-secret")


@app.post("/voice")
async def create_voice_session(
    user_id: str, name: Optional[str] = "NA", email: Optional[str] = "NA"
) -> VoiceSessionResponse:
    """Create new voice session with WebRTC connection"""
    try:

        print(
            f"Creating voice session for user_id: {user_id}, name: {name}, email: {email}"
        )

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

        # Note: The actual voice agent will be started by the LiveKit worker
        # when a user joins the room. This API just creates the room and token.

        return VoiceSessionResponse(
            room_name=room_name,
            token=jwt_token,
            ws_url=LIVEKIT_URL,
            participant_name=participant_name,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}


@app.post("/upload-files")
async def upload_files(
    file: UploadFile, user_id: str = Form(...), subject_name: str = Form(...)
):
    """Upload PDF files with validation and subject name"""
    try:
        # Check file type
        if file.content_type != "application/pdf":
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
                return {"status": "error", "message": "File size must be 20MB or less"}

        # Reconstruct file content
        content = b"".join(chunks)

        # Save file to uploaded_files directory
        file_path = f"uploaded_files/{file.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        return {
            "status": "success",
            "message": "File uploaded successfully",
            "file_name": file.filename,
            "user_id": user_id,
            "subject_name": subject_name,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", loop="asyncio")

from pydantic import BaseModel
from fastapi import UploadFile
from typing import Optional, List


class VoiceSessionResponse(BaseModel):
    room_name: str
    token: str
    ws_url: str
    participant_name: str


class FileDetails(BaseModel):
    user_id: str
    file_id: str
    file_name: str
    subject: str
    file_size: int
    file_type: str
    is_processed: bool
    total_generated_qna: int = 0
    upload_timestamp: str
    processed_timestamp: str
    user_name: str  # Newly added field


class QuestionAndAnswers(BaseModel):
    question_id: str
    user_id: str
    file_id: str
    question: str
    answer: str
    timestamp: str
    user_name: str  # Newly added field


class GenerateEmbeddingRequest(BaseModel):
    user_id: str
    absolute_filepath: str
    subject: str
    file_id: str
    user_name: str  # Newly added field


class QuestionAnswerPair(BaseModel):
    question: str
    answer: str


class UserInformation(BaseModel):
    user_id: str
    full_name: str
    email: str


class VoiceSessionParams(BaseModel):
    user_id: str
    name: Optional[str] = "NA"
    email: Optional[str] = "NA"
    session_id: Optional[str] = None  # Extracted from JWT token
    user_name: Optional[str] = None  # Newly added field  # Extracted from JWT token


class UploadFileParams(BaseModel):
    """Parameters for file upload service."""

    file: UploadFile
    user_id: str
    subject_name: str
    user_name: str


class GenerateEmbeddingResponse(BaseModel):
    status: str
    message: str
    collection_name: str
    file_id: str
    chunks_added: int = 0
    total_generated_qna: int = 0
    question_and_answers: list[QuestionAnswerPair] = []

from pydantic import BaseModel


class VoiceSessionResponse(BaseModel):
    room_name: str
    token: str
    ws_url: str
    participant_name: str


class LlmMetricCollectorDto(BaseModel):
    user_id: str
    session_id: str
    speech_id: str
    time_to_first_token: float
    cancelled: bool
    completion_tokens: int
    tokens_per_second: float
    prompt_tokens: int
    timestamp: float


class UserVoiceSessions(BaseModel):
    id: str
    user_id: str
    session_id: str
    room_name: str
    duration: int
    start_time: str
    end_time: str


class TtsMetricCollectorDto(BaseModel):
    user_id: str
    session_id: str
    speech_id: str
    request_id: str
    time_to_first_byte: float
    cancelled: bool
    audio_duration: float
    characters_count: int
    duration: float
    timestamp: float


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


class QuestionAndAnswers(BaseModel):
    question_id: str
    user_id: str
    file_id: str
    question: str
    answer: str
    timestamp: str

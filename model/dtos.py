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

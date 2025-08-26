"""Database models for Supabase tables."""
from model.dtos import UserVoiceSessions, FileDetails


class UserVoiceSessionsDB(UserVoiceSessions):
    """Database model for user voice sessions."""
    pass


class FileDetailsDB(FileDetails):
    """Database model for file details."""
    pass
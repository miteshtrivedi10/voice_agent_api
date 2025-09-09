"""Database models for Supabase tables."""
from model.dtos import FileDetails, QuestionAndAnswers


class FileDetailsDB(FileDetails):
    """Database model for file details."""
    pass


class QuestionAndAnswersDB(QuestionAndAnswers):
    """Database model for question and answers."""
    pass
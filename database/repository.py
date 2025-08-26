"""Repository layer for database operations."""
import asyncio
from typing import Any, Dict
from loguru import logger
from database.supabase_client import get_supabase_client
from database.models import UserVoiceSessionsDB, FileDetailsDB, QuestionAndAnswersDB


async def create_user_voice_session(session_data: UserVoiceSessionsDB) -> bool:
    """
    Asynchronously create a user voice session record in Supabase.
    
    Args:
        session_data: UserVoiceSessionsDB object containing session data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        supabase_client = get_supabase_client()
        if not supabase_client:
            logger.error("Supabase client not initialized")
            return False
            
        # Convert Pydantic model to dict
        session_dict = session_data.model_dump()
        
        # Insert into Supabase (create table if not exists)
        response = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: supabase_client.table("user_voice_sessions").upsert(session_dict).execute()
        )
        
        logger.info(f"User voice session created for user_id: {session_data.user_id}")
        return True
    except Exception as e:
        if "PGRST205" in str(e):
            logger.error(f"Table 'user_voice_sessions' does not exist in the database. Please create it through the Supabase dashboard. Error: {e}")
        else:
            logger.error(f"Error creating user voice session: {e}")
        return False


async def create_file_details(file_data: FileDetailsDB) -> bool:
    """
    Asynchronously create a file details record in Supabase.
    
    Args:
        file_data: FileDetailsDB object containing file data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        supabase_client = get_supabase_client()
        if not supabase_client:
            logger.error("Supabase client not initialized")
            return False
            
        # Convert Pydantic model to dict
        file_dict = file_data.model_dump()
        
        # Insert into Supabase (create table if not exists)
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supabase_client.table("file_details").upsert(file_dict).execute()
        )
        
        logger.info(f"File details created for user_id: {file_data.user_id}, file_id: {file_data.file_id}")
        return True
    except Exception as e:
        if "PGRST205" in str(e):
            logger.error(f"Table 'file_details' does not exist in the database. Please create it through the Supabase dashboard. Error: {e}")
        else:
            logger.error(f"Error creating file details: {e}")
        return False

async def create_question_and_answers(qna_data: QuestionAndAnswersDB) -> bool:
    """
    Asynchronously create a question and answers record in Supabase.
    
    Args:
        qna_data: QuestionAndAnswersDB object containing Q&A data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        supabase_client = get_supabase_client()
        if not supabase_client:
            logger.error("Supabase client not initialized")
            return False
            
        # Convert Pydantic model to dict
        qna_dict = qna_data.model_dump()
        
        # Insert into Supabase (create table if not exists)
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: supabase_client.table("question_and_answers").upsert(qna_dict).execute()
        )
        
        logger.info(f"Question and answers created for user_id: {qna_data.user_id}, file_id: {qna_data.file_id}")
        return True
    except Exception as e:
        if "PGRST205" in str(e):
            logger.error(f"Table 'question_and_answers' does not exist in the database. Please create it through the Supabase dashboard. Error: {e}")
        else:
            logger.error(f"Error creating question and answers: {e}")
        return False

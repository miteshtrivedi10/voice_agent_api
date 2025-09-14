"""Service layer for the voice agent API."""

import os
import uuid
import time
from datetime import datetime
from typing import Optional
import asyncio
from livekit import api
from loguru import logger

from model.dtos import (
    FileDetails,
    VoiceSessionResponse,
    VoiceSessionParams,
    GenerateEmbeddingResponse,
    QuestionAndAnswers,
    UploadFileParams,
    QuestionAnswerPair,
)
from database.models import FileDetailsDB, QuestionAndAnswersDB
from database.repository import (
    create_file_details,
    create_question_and_answers,
    update_file_details,
)

# Import RAG processor
from rag.rag.custom_processor import CustomRAGProcessor
from rag.config.settings import settings as rag_settings

# Import settings
from logic.config import settings as logic_settings

# Import the actual vision and LLM model functions from the RAG API server
import base64
import json
from rag.rag.openrouter import OpenRouterClient

# Debug: Print settings to verify they're loaded correctly
# logger.info(f"RAG Settings OPENROUTER_MODEL: {getattr(rag_settings, 'OPENROUTER_MODEL', 'NOT FOUND')}")

# Global variable to track the last LLM call time
last_llm_call_time = 0.0

def vision_model_func(content_item, context=None):
    """Real vision model function using Sonoma-Dusk-Alpha via OpenRouter for educational content analysis."""
    global last_llm_call_time
    
    # Rate limiting: Ensure at least 5 seconds between LLM calls
    current_time = time.time()
    time_since_last_call = current_time - last_llm_call_time
    
    if time_since_last_call < 5.0:
        wait_time = 5.0 - time_since_last_call
        logger.info(f"Rate limiting: Waiting {wait_time:.2f} seconds before next LLM call")
        time.sleep(wait_time)
    
    # Update the last call time
    last_llm_call_time = time.time()
    
    # Initialize OpenRouter client
    openrouter_client = OpenRouterClient()

    # Extract image data with enhanced error handling
    image_bytes = content_item.get("data")
    source_info = content_item.get("source_file", "unknown") or "unknown"
    page_info = content_item.get("page", "unknown") or "unknown"

    # Skip processing if no image data
    if not image_bytes:
        logger.warning(
            f"No image data found in content_item from {source_info}, page {page_info}"
        )
        return {
            "description": "No image data available",
            "scene_type": "unknown",
            "educational_concept": "missing_content",
            "complexity_level": "none",
        }

    # Convert to bytes if needed
    if not isinstance(image_bytes, bytes):
        try:
            image_bytes = base64.b64decode(image_bytes)
        except Exception as e:
            logger.error(
                f"Error decoding image data from {source_info}, page {page_info}: {e}"
            )
            return {
                "description": "Image data decoding failed",
                "scene_type": "corrupted",
                "educational_concept": "technical_issue",
                "complexity_level": "none",
            }

    # Skip very small images (likely icons, bullets, etc.)
    if len(image_bytes) < 1024:  # Less than 1KB, probably not meaningful
        logger.debug(
            f"Skipping small image ({len(image_bytes)} bytes) from {source_info}, page {page_info}"
        )
        return {
            "description": "Small/insignificant image skipped",
            "scene_type": "skipped",
            "educational_concept": "decorative_element",
            "complexity_level": "none",
        }

    # Base64 encode image
    try:
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        logger.error(
            f"Error encoding image data from {source_info}, page {page_info}: {e}"
        )
        return {
            "description": "Image encoding failed",
            "scene_type": "encoding_error",
            "educational_concept": "technical_issue",
            "complexity_level": "none",
        }

    image_mime = content_item.get("mime_type", "image/png")

    # Build context from surrounding content
    context_text = ""
    if context:
        context_texts = [item.get("text", "") for item in context if item.get("text")]
        context_text = " ".join(context_texts[:3])[
            :1000
        ]  # Limit context, shorter for better focus

    # Simplified prompt for educational image analysis
    prompt = f"""
    Analyze this educational image from a textbook. Provide a detailed description suitable for RAG processing and questionnaire generation.
    Context from surrounding content: {context_text}
    
    Focus on:
    - Main educational concept
    - Content type (diagram, chart, photo, illustration, table, equation)
    - Key visual elements and text content
    - Educational value and complexity
    
    Return ONLY this JSON format:
    {{
        "description": "Detailed 2-3 sentence description",
        "scene_type": "diagram|chart|photo|illustration|table|equation|other",
        "educational_concept": "main learning objective",
        "complexity_level": "simple|medium|advanced",
        "key_elements": ["3-5 key visual/text elements"],
        "question_types": ["multiple_choice", "short_answer", "diagram_labeling"]
    }}
    """

    messages = [
        {
            "role": "system",
            "content": "You are an expert educational content analyst. Analyze textbook images and return ONLY valid JSON. Never include markdown formatting.",
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_mime};base64,{image_base64}"},
                },
            ],
        },
    ]

    try:
        response = openrouter_client.chat_completion(
            model=rag_settings.OPENROUTER_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.2,  # Low temperature for factual analysis
        )

        # Parse JSON from response
        content = response["choices"][0]["message"]["content"]

        # Clean the response - remove any markdown formatting
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        if content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove ```

        # Parse JSON
        analysis = json.loads(content)

        logger.info(
            f"Generated vision analysis for image from {source_info}, page {page_info} ({len(image_bytes)} bytes)"
        )
        return analysis

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error for {source_info}, page {page_info}: {e}")
        logger.error(f"Response content: {content[:200]}...")
        # Return a fallback response
        return {
            "description": "Image analysis completed",
            "scene_type": "image",
            "educational_concept": "visual_content",
            "complexity_level": "medium",
            "key_elements": ["visual_content"],
            "question_types": ["short_answer"],
        }
    except Exception as e:
        logger.error(f"Vision model error for {source_info}, page {page_info}: {e}")
        # Check if the error is related to the OPENROUTER_MODEL setting
        if "OPENROUTER_MODEL" in str(e):
            logger.error("OPENROUTER_MODEL setting not found. Please check your environment configuration.")
        # Return None to indicate that no valid analysis could be generated
        # This will prevent the default question answer from being generated
        return None


def llm_model_func(content_item, context=None):
    """Real LLM model function using Sonoma-Dusk-Alpha via OpenRouter for educational content analysis."""
    global last_llm_call_time
    
    # Rate limiting: Ensure at least 5 seconds between LLM calls
    current_time = time.time()
    time_since_last_call = current_time - last_llm_call_time
    
    if time_since_last_call < 5.0:
        wait_time = 5.0 - time_since_last_call
        logger.info(f"Rate limiting: Waiting {wait_time:.2f} seconds before next LLM call")
        time.sleep(wait_time)
    
    # Update the last call time
    last_llm_call_time = time.time()
    
    # Initialize OpenRouter client
    openrouter_client = OpenRouterClient()

    content_type = content_item.get("type", "text")
    text_content = content_item.get("text", "") or content_item.get("enhanced_text", "")

    # Build context
    context_text = ""
    if context:
        context_items = [
            item.get("text", "") or item.get("enhanced_text", "")
            for item in context
            if item.get("text") or item.get("enhanced_text")
        ]
        context_text = " ".join(context_items[:2])[:800]  # Limit context length

    # Simplified prompt for content analysis based on type
    if content_type == "table":
        prompt = f"""
        Analyze this table from educational content for RAG processing and questionnaire generation.
        Table content: {text_content}
        Context: {context_text}
        
        Return ONLY this JSON format:
        {{
            "summary": "2-3 sentence summary",
            "key_points": ["3-5 bullet points"],
            "educational_value": "what students learn",
            "question_types": ["multiple_choice", "data_interpretation"]
        }}
        """
    elif content_type == "equation":
        prompt = f"""
        Analyze this mathematical equation from educational content.
        Equation: {text_content}
        Context: {context_text}
        
        Return ONLY this JSON format:
        {{
            "summary": "What the equation represents",
            "components": ["key variables and meanings"],
            "application": "Educational usage",
            "difficulty_level": "basic|intermediate|advanced",
            "question_types": ["problem_solving", "derivation"]
        }}
        """
    else:  # Generic text content
        prompt = f"""
        Analyze this educational text content for RAG processing and questionnaire generation.
        Content: {text_content}
        Context: {context_text}
        Content type: {content_type}
        
        Return ONLY this JSON format:
        {{
            "summary": "Concise 2-3 sentence summary",
            "key_points": ["3-5 main ideas"],
            "educational_objectives": ["what students should learn"],
            "complexity": "simple|medium|advanced",
            "question_types": ["multiple_choice", "short_answer", "essay"]
        }}
        """

    messages = [
        {
            "role": "system",
            "content": f"You are an expert educational content analyst for {content_type}. Return ONLY valid JSON. Never include markdown formatting.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = openrouter_client.chat_completion(
            model=rag_settings.OPENROUTER_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.2,  # Low for consistent analysis
        )

        content = response["choices"][0]["message"]["content"]

        # Clean the response - remove any markdown formatting
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        if content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove ```

        # Parse JSON
        analysis = json.loads(content)

        logger.debug(f"Generated LLM analysis for {content_type} content")
        return analysis

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error for {content_type} content: {e}")
        logger.error(f"Response content: {content[:200]}...")
        # Return a fallback response
        return {
            "summary": "Content analysis completed",
            "key_points": ["Educational content identified"],
            "educational_objectives": ["Content understanding"],
            "complexity": "medium",
            "question_types": ["short_answer"],
        }
    except Exception as e:
        logger.error(f"LLM model error for {content_type}: {e}")
        return {
            "summary": "Content analysis completed with basic information",
            "key_points": ["Educational content identified"],
            "educational_objectives": ["Content understanding"],
            "complexity": "medium",
            "question_types": ["short_answer"],
        }


# Initialize RAG processor instance with the actual model functions
# We'll create it on-demand to avoid async event loop issues
rag_processor = None


def get_rag_processor(user_name: Optional[str] = None):
    """Get or create RAG processor instance."""
    global rag_processor
    if rag_processor is None:
        rag_processor = CustomRAGProcessor(
            vision_model_func=vision_model_func,
            llm_model_func=llm_model_func,
            user_name=user_name
        )
    return rag_processor


def get_today_timestamp() -> str:
    """Get today's date as a timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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

            # Generate embeddings using RAG processor after successful insertion
            absolute_filepath = f"{logic_settings.UPLOAD_DIRECTORY}/{file_data.file_name}"

            # Get RAG processor instance with user_name
            processor = get_rag_processor(user_name=user_name)

            # Process file using RAG processor
            content_list = processor.process_file(absolute_filepath)

            # Generate questionnaires for the processed content
            questionnaire_data = []
            if hasattr(processor, "questionnaire_generator") and content_list:
                for content_item in content_list:
                    qa_pairs = processor.questionnaire_generator.generate_questionnaire_for_content(
                        content_item
                    )
                    questionnaire_data.extend(qa_pairs)

            embedding_response = GenerateEmbeddingResponse(
                status="success",
                message="Embeddings generated successfully using RAG processor",
                collection_name=file_data.subject,
                file_id=file_data.file_id,
                chunks_added=len(content_list),
                total_generated_qna=len(questionnaire_data),
                question_and_answers=[
                    QuestionAnswerPair(question=qa["question"], answer=qa["answer"])
                    for qa in questionnaire_data
                ],
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

    # Use user_name as participant_name if available, otherwise fallback to user_id
    participant_name = params.user_name if params.user_name else params.user_id

    # Generate unique room and participant
    room_name = f"{participant_name}_{uuid.uuid4().hex[:8]}"

    # Create room token
    token = api.AccessToken(logic_settings.LIVEKIT_API_KEY, logic_settings.LIVEKIT_API_SECRET)
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

    logger.info(f"Voice session created successfully for user_id: {params.user_id}")

    return VoiceSessionResponse(
        room_name=room_name,
        token=jwt_token,
        ws_url=logic_settings.LIVEKIT_URL,
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
    os.makedirs(logic_settings.UPLOAD_DIRECTORY, exist_ok=True)
    file_path = f"{logic_settings.UPLOAD_DIRECTORY}/{params.file.filename}"
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

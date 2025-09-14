from typing import List, Dict, Any, Optional
import logging
import json
import re
from rag.rag.openrouter import OpenRouterClient
from rag.config.settings import settings

logger = logging.getLogger(__name__)


class QuestionnaireGenerator:
    """
    Generates descriptive questions and answers for processed pages or images using LLM.

    This generator creates educational question-answer pairs from processed content
    without referencing the source material explicitly. It's designed for:
    - Creating assessment questions for student learning
    - Generating study materials from educational content
    - Producing self-assessment tools for learners
    """

    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        llm_model: str = None,
    ):
        """
        Initialize the QuestionnaireGenerator.

        Args:
            openrouter_client: OpenRouter client for LLM calls
            llm_model: LLM model to use for generation (will be replaced with actual model later)
        """
        self.openrouter_client = openrouter_client
        self.llm_model = llm_model or settings.OPENROUTER_MODEL

    def generate_questionnaire_for_content(
        self, content_item: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate a questionnaire (2-3 questions and answers) for a single content item.

        Args:
            content_item: Content item with text_content, source_file, page_id, etc.

        Returns:
            List of question-answer pairs with metadata
        """
        try:
            # Extract content information
            text_content = content_item.get("text_content", "")
            source_file = content_item.get("source_file", "unknown")
            page_id = content_item.get("page_id", "unknown")
            content_type = content_item.get("content_type", "generic")

            if not text_content:
                logger.warning(
                    f"No text content found for {source_file}, page {page_id}"
                )
                return []

            # Generate questions and answers using LLM
            qa_pairs = self._generate_qa_with_llm(
                text_content, source_file, page_id, content_type
            )

            return qa_pairs

        except Exception as e:
            logger.error(
                f"Error generating questionnaire for {source_file}, page {page_id}: {e}"
            )
            return []

    def _generate_qa_with_llm(
        self, text_content: str, source_file: str, page_id: str, content_type: str
    ) -> List[Dict[str, Any]]:
        """
        Generate questions and answers using the LLM model.

        Args:
            text_content: The text content to generate questions from
            source_file: Source file name
            page_id: Page identifier
            content_type: Type of content (text, image, etc.)

        Returns:
            List of question-answer pairs
        """
        try:
            # Create prompt for questionnaire generation
            content_type_description = (
                "educational content"
                if content_type == "generic"
                else f"{content_type} content"
            )

            prompt = f"""
            Based on the following {content_type_description}, generate 2-3 specific question-answer pairs 
            that test understanding of key educational concepts. The questions should be direct and specific, 
            without referencing the source material explicitly.

            Content:
            {text_content}

            Requirements:
            1. Generate 2-3 question-answer pairs 
            2. Questions should be specific and direct educational questions
            3. DO NOT add any outside context to either question or answer that is not part of the {text_content}
            4. DO NOT use phrases like "according to the content", "based on the diagram", "as per the text", etc.
            5. DO NOT reference the source material in any way
            6. Questions should test actual knowledge of the subject matter
            7. Answers should be concise but comprehensive
            8. Format each pair as a JSON object with "question" and "answer" fields

            Example of GOOD questions:
            - "What process describes the movement of nutrients through blood vessels?"
            - "Which veins carry blood from the upper and lower parts of the body to the heart?"
            - "Explain the major timelines of british history in India?"
            - "Provide the vowels in english language and atleast one noun associated with each vowels?"
            - "If I start from center of New Delhi and move towards Bangalore, which major states will I visit (assume you are travelling in straight line)?"

            Example of BAD questions:
            - "According to the content, what process describes..."
            - "As per the diagram shown, which veins carry..."
            - "Based on the text, what are the key concepts..."
            - "What does the symbol °C stand for ..."What does the symbol °C standWhat does the symbol °C stand
            - "Provide important timelines as mentioned in the text ..."
            - "What states are shown in the content ..."
            - "Show the path to reach from A to B with reference to diagram  ..."

            Return ONLY a JSON array with exactly 2 objects in this format:
            [
                {{
                    "question": "Your first specific question here",
                    "answer": "Your first direct answer here"
                }},
                {{
                    "question": "Your second specific question here",
                    "answer": "Your second direct answer here"
                }}
            ]
            """

            # Prepare messages for OpenRouter API
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert educational content analyst creating specific, direct question-answer pairs for student learning. Create tricky questions that test actual knowledge without referencing the source material.",
                },
                {"role": "user", "content": prompt},
            ]

            # Call OpenRouter API
            response = self.openrouter_client.chat_completion(
                model=self.llm_model,
                messages=messages,
                max_tokens=1000,
                temperature=0.3,  # Moderate creativity
            )

            # Parse response
            response_content = response["choices"][0]["message"]["content"]

            # Extract JSON from response
            qa_pairs = self._extract_json_from_response(response_content)

            # Add metadata to each QA pair
            for qa_pair in qa_pairs:
                qa_pair["source_file"] = source_file
                qa_pair["page_id"] = page_id

            logger.info(
                f"Generated {len(qa_pairs)} QA pairs for {source_file}, page {page_id}"
            )
            return qa_pairs

        except Exception as e:
            logger.error(
                f"Error generating QA with LLM for {source_file}, page {page_id}: {e}"
            )
            # Return default QA pairs as fallback
            return []

    def _extract_json_from_response(
        self, response_content: str
    ) -> List[Dict[str, Any]]:
        """
        Extract JSON array from LLM response.

        This method handles various response formats from LLMs:
        1. Direct JSON responses
        2. JSON wrapped in markdown code blocks
        3. Fallback to empty list for unparseable responses

        Args:
            response_content: Raw response from LLM

        Returns:
            List of question-answer pairs or empty list if parsing fails
        """
        try:
            # Try to parse as JSON directly
            return json.loads(response_content)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from markdown code blocks
            json_match = re.search(r"\[[\s\S]*\]", response_content)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # If all parsing fails, log and return empty list
            logger.warning(
                f"Could not parse JSON from LLM response: {response_content[:100]}..."
            )
            return []

    def generate_and_print_questionnaires(
        self, content_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate questionnaires for all content items and print them to console.
        Content items are grouped by page to generate one questionnaire per page.

        Args:
            content_items: List of content items processed by RAG pipeline

        Returns:
            List of all generated question-answer pairs
        """
        all_qa_pairs = []

        print("\n" + "=" * 80)
        print("GENERATED QUESTIONNAIRES")
        print("=" * 80)

        # Group content items by source_file and page_id
        grouped_content = {}
        for item in content_items:
            source_file = item.get("source_file", "unknown")
            page_id = str(item.get("page_id", "unknown"))
            key = (source_file, page_id)
            
            if key not in grouped_content:
                grouped_content[key] = []
            grouped_content[key].append(item)

        # Generate one questionnaire per page using consolidated content
        for (source_file, page_id), page_items in grouped_content.items():
            # Consolidate text content from all chunks for this page
            consolidated_content = "\n\n".join([
                item.get("text_content", "") or item.get("enhanced_text", "") or item.get("text", "")
                for item in page_items
                if item.get("text_content") or item.get("enhanced_text") or item.get("text")
            ])
            
            if not consolidated_content.strip():
                logger.warning(f"No text content found for {source_file}, page {page_id}")
                continue

            # Create a consolidated content item for questionnaire generation
            consolidated_item = {
                "text_content": consolidated_content,
                "source_file": source_file,
                "page_id": page_id,
                "content_type": page_items[0].get("content_type", "generic") if page_items else "generic"
            }

            # Generate questionnaire for the consolidated content
            qa_pairs = self.generate_questionnaire_for_content(consolidated_item)
            all_qa_pairs.extend(qa_pairs)

            print(f"\n--- Questionnaire for {source_file}, Page {page_id} ---")

            for i, qa_pair in enumerate(qa_pairs, 1):
                print(f"\nQ{i}: {qa_pair.get('question', 'No question generated')}")
                print(f"A{i}: {qa_pair.get('answer', 'No answer generated')}")
                print(f"F{i}: {qa_pair.get('source_file', 'unknown')}")
                print(f"P{i}: {qa_pair.get('page_id', 'unknown')}")

        print("\n" + "=" * 80)
        print(f"TOTAL QUESTIONNAIRES GENERATED: {len(all_qa_pairs)}")
        print("=" * 80)

        return all_qa_pairs

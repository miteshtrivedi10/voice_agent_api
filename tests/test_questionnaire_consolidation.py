import pytest
from unittest.mock import Mock, patch
from rag.rag.questionnaire_generator import QuestionnaireGenerator

class TestQuestionnaireConsolidation:
    """Test cases for questionnaire consolidation functionality."""
    
    def test_content_grouping_by_page(self):
        """Test that content items are properly grouped by page."""
        # Create mock content items from different pages
        content_items = [
            {
                "text_content": "Content A from page 1",
                "source_file": "document.pdf",
                "page_id": "1",
                "content_type": "text"
            },
            {
                "text_content": "Content B from page 1",
                "source_file": "document.pdf",
                "page_id": "1",
                "content_type": "text"
            },
            {
                "text_content": "Content from page 2",
                "source_file": "document.pdf",
                "page_id": "2",
                "content_type": "text"
            }
        ]
        
        # Create mock OpenRouter client
        mock_client = Mock()
        mock_client.chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": """[
                        {
                            "question": "Test question?",
                            "answer": "Test answer."
                        }
                    ]"""
                }
            }]
        }
        
        generator = QuestionnaireGenerator(openrouter_client=mock_client)
        
        # Mock the individual questionnaire generation to avoid actual API calls
        with patch.object(generator, 'generate_questionnaire_for_content') as mock_generate:
            mock_generate.return_value = [
                {
                    "question": "Test question?",
                    "answer": "Test answer.",
                    "source_file": "document.pdf",
                    "page_id": "1"
                }
            ]
            
            # Test the consolidation
            qa_pairs = generator.generate_and_print_questionnaires(content_items)
            
            # Should generate 2 questionnaires (one for each page)
            assert mock_generate.call_count == 2
            
            # First call should have consolidated content from page 1
            first_call_args = mock_generate.call_args_list[0][0][0]
            assert first_call_args["page_id"] == "1"
            assert "Content A from page 1" in first_call_args["text_content"]
            assert "Content B from page 1" in first_call_args["text_content"]
            
            # Second call should have content from page 2
            second_call_args = mock_generate.call_args_list[1][0][0]
            assert second_call_args["page_id"] == "2"
            assert "Content from page 2" in second_call_args["text_content"]
    
    def test_empty_content_handling(self):
        """Test handling of content items with no text."""
        content_items = [
            {
                "text_content": "",  # Empty content
                "source_file": "document.pdf",
                "page_id": "1",
                "content_type": "text"
            }
        ]
        
        mock_client = Mock()
        generator = QuestionnaireGenerator(openrouter_client=mock_client)
        
        # Should handle empty content gracefully
        with patch('rag.rag.questionnaire_generator.logger') as mock_logger:
            qa_pairs = generator.generate_and_print_questionnaires(content_items)
            # Should log a warning for empty content
            mock_logger.warning.assert_called()
            # Should return empty list
            assert len(qa_pairs) == 0
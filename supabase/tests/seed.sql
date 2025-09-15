-- Seed data for testing
-- Note: This should only be used for development/testing environments

-- Insert sample file details
INSERT INTO file_details (
  user_id,
  file_id,
  file_name,
  subject,
  file_size,
  file_type,
  is_processed,
  total_generated_qna,
  user_name
) VALUES
  ('test-user-1', 'file-001', 'sample.pdf', 'Mathematics', 1024000, 'application/pdf', true, 5, 'Test User 1'),
  ('test-user-1', 'file-002', 'document.png', 'Science', 2048000, 'image/png', true, 3, 'Test User 1'),
  ('test-user-2', 'file-003', 'presentation.jpg', 'History', 3072000, 'image/jpeg', false, 0, 'Test User 2');

-- Insert sample question and answers
INSERT INTO question_and_answers (
  question_id,
  user_id,
  file_id,
  question,
  answer,
  user_name
) VALUES
  ('qna-001', 'test-user-1', 'file-001', 'What is the Pythagorean theorem?', 'The Pythagorean theorem states that in a right-angled triangle, the square of the hypotenuse is equal to the sum of the squares of the other two sides.', 'Test User 1'),
  ('qna-002', 'test-user-1', 'file-001', 'What is the derivative of x^2?', 'The derivative of x^2 is 2x.', 'Test User 1'),
  ('qna-003', 'test-user-1', 'file-002', 'What is photosynthesis?', 'Photosynthesis is the process by which plants convert light energy into chemical energy.', 'Test User 1');
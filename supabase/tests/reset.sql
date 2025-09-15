-- Reset script - DANGER: This will delete all data!

-- Drop triggers
drop trigger if exists update_file_details_updated_at on file_details;
drop trigger if exists update_question_and_answers_updated_at on question_and_answers;
drop trigger if exists update_file_details_processed_timestamp on file_details;

-- Drop functions
drop function if exists update_updated_at_column() cascade;
drop function if exists update_processed_timestamp() cascade;
drop function if exists get_user_file_stats(text) cascade;
drop function if exists get_recent_qna(text, integer) cascade;

-- Drop tables
drop table if exists question_and_answers cascade;
drop table if exists file_details cascade;

-- Drop extensions
drop extension if exists "uuid-ossp";

-- Reset auto-increment sequences
select setval(pg_get_serial_sequence('file_details', 'id'), 1, false);
select setval(pg_get_serial_sequence('question_and_answers', 'id'), 1, false);
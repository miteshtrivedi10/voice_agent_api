-- Test script to verify database setup

-- Test 1: Check if tables exist
select 'file_details table exists' as test_name,
       (select count(*) > 0 from information_schema.tables where table_name = 'file_details') as result
union all
select 'question_and_answers table exists' as test_name,
       (select count(*) > 0 from information_schema.tables where table_name = 'question_and_answers') as result;

-- Test 2: Check if indexes exist
select 'file_details indexes exist' as test_name,
       (select count(*) >= 5 from pg_indexes where tablename = 'file_details') as result
union all
select 'question_and_answers indexes exist' as test_name,
       (select count(*) >= 4 from pg_indexes where tablename = 'question_and_answers') as result;

-- Test 3: Check if RLS is enabled
select 'file_details RLS enabled' as test_name,
       (select relrowsecurity from pg_class where relname = 'file_details') as result
union all
select 'question_and_answers RLS enabled' as test_name,
       (select relrowsecurity from pg_class where relname = 'question_and_answers') as result;

-- Test 4: Check if triggers exist
select 'update_updated_at_column function exists' as test_name,
       (select count(*) > 0 from pg_proc where proname = 'update_updated_at_column') as result
union all
select 'file_details update trigger exists' as test_name,
       (select count(*) > 0 from pg_trigger where tgname = 'update_file_details_updated_at') as result
union all
select 'question_and_answers update trigger exists' as test_name,
       (select count(*) > 0 from pg_trigger where tgname = 'update_question_and_answers_updated_at') as result;

-- Test 5: Check if custom functions exist
select 'get_user_file_stats function exists' as test_name,
       (select count(*) > 0 from pg_proc where proname = 'get_user_file_stats') as result
union all
select 'get_recent_qna function exists' as test_name,
       (select count(*) > 0 from pg_proc where proname = 'get_recent_qna') as result;

-- Test 6: Insert test data
begin;
  -- Insert test file
  insert into file_details (user_id, file_id, file_name, subject, file_size, file_type, is_processed, total_generated_qna, user_name)
  values ('test-user-123', 'test-file-123', 'test.pdf', 'Test Subject', 1000, 'application/pdf', false, 0, 'Test User');
  
  -- Update test file
  update file_details 
  set is_processed = true, total_generated_qna = 5 
  where file_id = 'test-file-123';
  
  -- Insert test Q&A
  insert into question_and_answers (question_id, user_id, file_id, question, answer, user_name)
  values ('test-qna-123', 'test-user-123', 'test-file-123', 'Test question?', 'Test answer.', 'Test User');
  
  -- Test functions
  select * from get_user_file_stats('test-user-123');
  select * from get_recent_qna('test-user-123', 5);
  
  -- Clean up
  delete from question_and_answers where question_id = 'test-qna-123';
  delete from file_details where file_id = 'test-file-123';
commit;

select 'All tests completed successfully' as test_name, true as result;
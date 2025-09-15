-- Test script to verify file_alias column functionality

-- Test 1: Check if file_alias column exists
select 'file_alias column exists' as test_name,
       (select count(*) > 0 from information_schema.columns where table_name = 'file_details' and column_name = 'file_alias') as result;

-- Test 2: Check if index exists
select 'file_alias index exists' as test_name,
       (select count(*) > 0 from pg_indexes where tablename = 'file_details' and indexname = 'idx_file_details_file_alias') as result;

-- Test 3: Insert test data with file_alias
begin;
  -- Insert test file with file_alias
  insert into file_details (user_id, file_id, file_name, file_alias, subject, file_size, file_type, is_processed, total_generated_qna, user_name)
  values ('test-user-456', 'test-file-456', 'uuid-based-filename.pdf', 'tutor ml.pdf', 'Test Subject', 1000, 'application/pdf', false, 0, 'Test User');
  
  -- Verify the data was inserted correctly
  select 'file_alias data inserted correctly' as test_name,
         (select count(*) = 1 from file_details where file_id = 'test-file-456' and file_alias = 'tutor ml.pdf') as result;
  
  -- Clean up
  delete from file_details where file_id = 'test-file-456';
commit;

select 'file_alias tests completed successfully' as test_name, true as result;
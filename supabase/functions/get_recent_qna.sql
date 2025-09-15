-- Create a function to get recent Q&A for a user
create or replace function get_recent_qna(user_id_param text, limit_count integer default 10)
returns table(
  question_id text,
  file_name text,
  subject text,
  question text,
  answer text,
  created_at timestamptz
) as $$
begin
  return query
  select 
    qna.question_id,
    fd.file_name,
    fd.subject,
    qna.question,
    qna.answer,
    qna.created_at
  from question_and_answers qna
  join file_details fd on qna.file_id = fd.file_id
  where qna.user_id = user_id_param
  order by qna.created_at desc
  limit limit_count;
end;
$$ language plpgsql security definer;

-- Grant execute permission on the function
grant execute on function get_recent_qna(text, integer) to authenticated;
-- Create a function to get user file statistics
create or replace function get_user_file_stats(user_id_param text)
returns table(
  total_files bigint,
  processed_files bigint,
  total_qna_generated bigint,
  avg_qna_per_file numeric
) as $$
begin
  return query
  select 
    count(*) as total_files,
    count(*) filter (where is_processed = true) as processed_files,
    sum(total_generated_qna) as total_qna_generated,
    case 
      when count(*) filter (where is_processed = true) > 0 
      then (sum(total_generated_qna) / count(*) filter (where is_processed = true))::numeric(10,2)
      else 0::numeric(10,2)
    end as avg_qna_per_file
  from file_details
  where user_id = user_id_param;
end;
$$ language plpgsql security definer;

-- Grant execute permission on the function
grant execute on function get_user_file_stats(text) to authenticated;
-- Create question_and_answers table
create table question_and_answers (
  id uuid primary key default gen_random_uuid(),
  question_id text unique not null,
  user_id text not null,
  file_id text not null,
  question text not null,
  answer text not null,
  timestamp timestamptz not null default now(),
  user_name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- Foreign key constraint to file_details
  constraint fk_file_details
    foreign key (file_id)
    references file_details (file_id)
    on delete cascade
);

-- Add indexes for better query performance
create index idx_question_and_answers_user_id on question_and_answers (user_id);
create index idx_question_and_answers_file_id on question_and_answers (file_id);
create index idx_question_and_answers_question_id on question_and_answers (question_id);
create index idx_question_and_answers_timestamp on question_and_answers (timestamp);

-- Enable RLS (Row Level Security)
alter table question_and_answers enable row level security;

-- Create policy to allow users to see only their own Q&A
create policy "Users can view their own Q&A" on question_and_answers
  for select using (auth.uid()::text = user_id);

create policy "Users can insert their own Q&A" on question_and_answers
  for insert with check (auth.uid()::text = user_id);

create policy "Users can update their own Q&A" on question_and_answers
  for update using (auth.uid()::text = user_id);

create policy "Users can delete their own Q&A" on question_and_answers
  for delete using (auth.uid()::text = user_id);

-- Grant necessary permissions
grant usage on schema public to authenticated;
grant all on table question_and_answers to authenticated;

-- Create trigger to automatically update updated_at column
create trigger update_question_and_answers_updated_at 
  before update on question_and_answers 
  for each row 
  execute procedure update_updated_at_column();
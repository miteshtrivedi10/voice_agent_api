-- Create file_details table
create table file_details (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  file_id text unique not null,
  file_name text not null,
  subject text not null,
  file_size bigint not null,
  file_type text not null,
  is_processed boolean not null default false,
  total_generated_qna integer not null default 0,
  upload_timestamp timestamptz not null default now(),
  processed_timestamp timestamptz not null default now(),
  user_name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Add indexes for better query performance
create index idx_file_details_user_id on file_details (user_id);
create index idx_file_details_file_id on file_details (file_id);
create index idx_file_details_subject on file_details (subject);
create index idx_file_details_is_processed on file_details (is_processed);
create index idx_file_details_upload_timestamp on file_details (upload_timestamp);

-- Enable RLS (Row Level Security)
alter table file_details enable row level security;

-- Create policy to allow users to see only their own files
create policy "Users can view their own files" on file_details
  for select using (auth.uid()::text = user_id);

create policy "Users can insert their own files" on file_details
  for insert with check (auth.uid()::text = user_id);

create policy "Users can update their own files" on file_details
  for update using (auth.uid()::text = user_id);

-- Grant necessary permissions
grant usage on schema public to authenticated;
grant all on table file_details to authenticated;

-- Create updated_at trigger function
create or replace function update_updated_at_column()
returns trigger as $$
begin
   NEW.updated_at = now(); 
   return NEW; 
end;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at column
create trigger update_file_details_updated_at 
  before update on file_details 
  for each row 
  execute procedure update_updated_at_column();
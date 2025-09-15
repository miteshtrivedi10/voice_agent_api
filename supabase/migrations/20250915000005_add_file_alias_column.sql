-- Add file_alias column to file_details table
alter table file_details 
add column file_alias text;

-- Add index for better query performance on file_alias
create index idx_file_details_file_alias on file_details (file_alias);

-- Update existing RLS policies to include the new column
-- Note: The existing policies should already work with the new column
-- but we'll recreate them to be explicit
drop policy if exists "Users can view their own files" on file_details;
drop policy if exists "Users can insert their own files" on file_details;
drop policy if exists "Users can update their own files" on file_details;

create policy "Users can view their own files" on file_details
  for select using (auth.uid()::text = user_id);

create policy "Users can insert their own files" on file_details
  for insert with check (auth.uid()::text = user_id);

create policy "Users can update their own files" on file_details
  for update using (auth.uid()::text = user_id);
-- Create function to automatically update processed_timestamp
create or replace function update_processed_timestamp()
returns trigger as $$
begin
  -- If is_processed changed from false to true, update processed_timestamp
  if (NEW.is_processed = true and (OLD.is_processed is null or OLD.is_processed = false)) then
    NEW.processed_timestamp = now();
  end if;
  return NEW;
end;
$$ language 'plpgsql';

-- Create trigger to automatically update processed_timestamp
create trigger update_file_details_processed_timestamp 
  before update on file_details 
  for each row 
  execute procedure update_processed_timestamp();
-- Add file_alias column to file_details table
ALTER TABLE file_details ADD COLUMN IF NOT EXISTS file_alias TEXT;

-- Add index for better query performance on file_alias
CREATE INDEX IF NOT EXISTS idx_file_details_file_alias ON file_details (file_alias);

-- Update existing RLS policies (they should work with new column automatically)
-- No changes needed to existing policies as they use generic SELECT/INSERT/UPDATE permissions

-- Verify the column was added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'file_details' AND column_name = 'file_alias';
# Supabase Database Structure

This directory contains all the necessary scripts and configurations to set up a production-level Supabase database for the Voice Agent API.

## Directory Structure

- `migrations/` - SQL migration scripts for creating and updating database tables
- `functions/` - Custom PostgreSQL functions and Supabase functions
- `tests/` - Database test scripts

## Database Tables

### 1. file_details
Stores information about uploaded files.

Columns:
- id (uuid, primary key)
- user_id (text) - User identifier
- file_id (text, unique) - File identifier
- file_name (text) - Processed file name (UUID-based)
- file_alias (text) - Original file name as uploaded by user
- subject (text) - Subject/category of the file
- file_size (bigint) - Size of the file in bytes
- file_type (text) - MIME type of the file
- is_processed (boolean) - Whether the file has been processed
- total_generated_qna (integer) - Number of Q&A pairs generated
- upload_timestamp (timestamptz) - When the file was uploaded
- processed_timestamp (timestamptz) - When the file was processed
- user_name (text) - Name of the user who uploaded the file
- created_at (timestamptz) - Record creation timestamp
- updated_at (timestamptz) - Record update timestamp

### 2. question_and_answers
Stores generated question and answer pairs for uploaded files.

Columns:
- id (uuid, primary key)
- question_id (text, unique) - Question identifier
- user_id (text) - User identifier
- file_id (text) - File identifier (foreign key to file_details)
- question (text) - Generated question
- answer (text) - Generated answer
- timestamp (timestamptz) - When the Q&A was generated
- user_name (text) - Name of the user
- created_at (timestamptz) - Record creation timestamp
- updated_at (timestamptz) - Record update timestamp

### 3. users (public.users)
Stores additional user profile information.

Columns:
- id (uuid, primary key) - References auth.users(id)
- email (text, unique) - User's email address
- full_name (text) - User's full name
- avatar_url (text) - URL to user's avatar image
- created_at (timestamptz) - Record creation timestamp
- updated_at (timestamptz) - Record update timestamp

## Custom Functions

### 1. get_user_file_stats(user_id)
Returns statistics about a user's files:
- total_files - Total number of files uploaded
- processed_files - Number of files that have been processed
- total_qna_generated - Total number of Q&A pairs generated
- avg_qna_per_file - Average number of Q&A pairs per processed file

### 2. get_recent_qna(user_id, limit_count)
Returns recent Q&A pairs for a user:
- question_id - Question identifier
- file_name - Name of the file the Q&A was generated from
- subject - Subject of the file
- question - The generated question
- answer - The generated answer
- created_at - When the Q&A was created

### 3. get_user_profile(user_id)
Returns user profile information:
- id - User identifier
- email - User's email address
- full_name - User's full name
- avatar_url - URL to user's avatar image
- created_at - When the profile was created
- updated_at - When the profile was last updated

## OAuth Provider Setup

See `oauth_setup_guide.md` for detailed instructions on setting up OAuth providers.

## Setup Instructions

1. Create a new Supabase project
2. Run the migration scripts in order:
   - `20250915000000_create_file_details_table.sql`
   - `20250915000001_create_question_and_answers_table.sql`
   - `20250915000002_setup_security.sql`
   - `20250915000003_add_processed_timestamp_trigger.sql`
   - `20250915000004_setup_oauth_and_auth.sql`
3. Deploy custom functions:
   - `functions/get_user_file_stats.sql`
   - `functions/get_recent_qna.sql`
   - `functions/get_user_profile.sql`
4. Configure OAuth providers through the Supabase dashboard (see `oauth_setup_guide.md`)
5. Run tests to verify setup:
   - `tests/test_setup.sql`

## Best Practices Implemented

- Row Level Security (RLS) to ensure data isolation
- Proper indexing for query performance
- Foreign key constraints for data integrity
- Automatic timestamp updates with triggers
- UUID primary keys for scalability
- Cascade delete for related records
- Automatic processed_timestamp update when file is marked as processed
- Comprehensive test suite for verification
- OAuth provider support for authentication
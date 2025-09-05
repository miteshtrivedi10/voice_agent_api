# Consolidated Supabase Migrations

This directory contains consolidated and organized SQL migration files for the Voice Agent API project. The files have been grouped logically to make it easier to understand and recreate the database environment.

## Directory Organization

- `core/` - Core database schema with all table definitions
- `rls/` - Row Level Security policies for all tables
- `functions/` - All utility functions and triggers
- `hooks/` - Custom authentication token hook

## Execution Order

To recreate the database environment, execute the files in this order:

1. `core/001_core_schema.sql`
2. `rls/002_rls_policies.sql`
3. `functions/003_functions.sql`
4. `hooks/004_auth_hook.sql`

## Manual Steps

After executing the SQL files, you need to manually enable the custom access token hook through the Supabase Dashboard:

1. Go to your Supabase project dashboard
2. Navigate to "Authentication" in the left sidebar
3. Click on "Hooks" in the Authentication menu
4. Find "Custom Access Token" and toggle it ON
5. Select the function "public.custom_access_token_hook" from the dropdown
6. Click "Save"

## Testing the Setup

After enabling the hook, you can test it by:

1. Logging out of your application
2. Logging back in through Google authentication
3. Checking the JWT token in your browser's developer tools:
   - Open Developer Tools (F12)
   - Go to Application tab
   - Look for Local Storage or Session Storage
   - Find the Supabase auth token
   - Decode it using a JWT decoder (like jwt.io)
   - Check if it contains the "user_name" field

## Verification Queries

Run these queries in your Supabase SQL Editor to verify everything is working:

```sql
-- Check if the function exists
SELECT proname, prosecdef FROM pg_proc WHERE proname = 'custom_access_token_hook';

-- Check if a specific user has a profile with user_name
SELECT id, user_name, full_name FROM user_profiles WHERE id = 'YOUR_USER_ID_HERE';

-- Check how many profiles have NULL user_name
SELECT COUNT(*) FROM user_profiles WHERE user_name IS NULL;

-- Run the fix function to populate any missing usernames
SELECT populate_missing_usernames();
```
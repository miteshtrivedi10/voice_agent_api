-- Utility Functions for Voice Agent API

-- Create a function to generate unique usernames
CREATE OR REPLACE FUNCTION generate_unique_username(user_name TEXT, user_email TEXT)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    base_username TEXT;
    candidate_username TEXT;
    counter INTEGER := 0;
    max_attempts INTEGER := 100;
BEGIN
    -- Create base username from name and email
    base_username := LOWER(REGEXP_REPLACE(user_name, '[^a-zA-Z0-9]', '', 'g'));
    
    -- If base username is too short, add part of email
    IF LENGTH(base_username) < 3 THEN
        base_username := base_username || LOWER(LEFT(SPLIT_PART(user_email, '@', 1), 10 - LENGTH(base_username)));
    END IF;
    
    -- Ensure minimum length
    IF LENGTH(base_username) < 3 THEN
        base_username := base_username || 'user';
    END IF;
    
    -- Truncate to reasonable length
    base_username := LEFT(base_username, 20);
    
    -- Start with base username
    candidate_username := base_username;
    
    -- Loop until we find a unique username or hit max attempts
    WHILE counter < max_attempts LOOP
        -- Check if this username already exists
        IF NOT EXISTS (SELECT 1 FROM users WHERE user_name = candidate_username) THEN
            RETURN candidate_username;
        END IF;
        
        -- Increment counter and try with a number suffix
        counter := counter + 1;
        candidate_username := base_username || counter;
    END LOOP;
    
    -- If we still haven't found a unique username, append timestamp
    RETURN base_username || EXTRACT(EPOCH FROM NOW())::BIGINT % 1000000;
END;
$$;

-- Add a comment to describe the function
COMMENT ON FUNCTION generate_unique_username(TEXT, TEXT) IS 'Generates a unique username based on user name and email';

-- Create a function to automatically generate a unique username
CREATE OR REPLACE FUNCTION generate_unique_username(base_name TEXT, user_email TEXT)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    base_username TEXT;
    candidate_username TEXT;
    counter INTEGER := 0;
    max_attempts INTEGER := 100;
BEGIN
    -- Create base username from name and email
    base_username := LOWER(REGEXP_REPLACE(base_name, '[^a-zA-Z0-9]', '', 'g'));
    
    -- If base username is too short, add part of email
    IF LENGTH(base_username) < 3 THEN
        base_username := base_username || LOWER(LEFT(SPLIT_PART(user_email, '@', 1), 10 - LENGTH(base_username)));
    END IF;
    
    -- Ensure minimum length
    IF LENGTH(base_username) < 3 THEN
        base_username := base_username || 'user';
    END IF;
    
    -- Truncate to reasonable length
    base_username := LEFT(base_username, 20);
    
    -- Start with base username
    candidate_username := base_username;
    
    -- Loop until we find a unique username or hit max attempts
    WHILE counter < max_attempts LOOP
        -- Check if this username already exists
        IF NOT EXISTS (SELECT 1 FROM user_profiles WHERE user_name = candidate_username) THEN
            RETURN candidate_username;
        END IF;
        
        -- Increment counter and try with a number suffix
        counter := counter + 1;
        candidate_username := base_username || counter;
    END LOOP;
    
    -- If we still haven't found a unique username, append timestamp
    RETURN base_username || EXTRACT(EPOCH FROM NOW())::BIGINT % 1000000;
END;
$$;

-- Add a comment to describe the function
COMMENT ON FUNCTION generate_unique_username(TEXT, TEXT) IS 'Generates a unique username based on user name and email';

-- Create a trigger function to automatically populate user_name when a profile is created
CREATE OR REPLACE FUNCTION populate_user_profile()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Generate a unique username if one wasn't provided
    IF NEW.user_name IS NULL THEN
        NEW.user_name := generate_unique_username(
            COALESCE(NEW.full_name, ''), 
            COALESCE((SELECT email FROM auth.users WHERE id = NEW.id), '')
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- Create the trigger to run before inserting a new user profile
DROP TRIGGER IF EXISTS trigger_populate_user_profile ON user_profiles;
CREATE TRIGGER trigger_populate_user_profile
    BEFORE INSERT ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION populate_user_profile();

-- Add a comment to describe the trigger function
COMMENT ON FUNCTION populate_user_profile() IS 'Trigger function to automatically populate user_name field when inserting new user profiles';

-- Create a function to automatically create user profiles when new users sign up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Safely insert user profile, handling any possible conflicts
  INSERT INTO public.user_profiles (id, full_name, avatar_url)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'name', SPLIT_PART(NEW.email, '@', 1)),
    NEW.raw_user_meta_data->>'picture'
  )
  ON CONFLICT (id) DO UPDATE SET
    full_name = COALESCE(EXCLUDED.full_name, user_profiles.full_name),
    avatar_url = COALESCE(EXCLUDED.avatar_url, user_profiles.avatar_url),
    updated_at = NOW();
  
  -- The user_name will be auto-generated by the existing trigger
  RETURN NEW;
EXCEPTION 
  WHEN OTHERS THEN
    -- Log the error but don't stop the authentication process
    RAISE WARNING 'Error creating user profile for user %: %', NEW.id, SQLERRM;
    RETURN NEW;
END;
$$;

-- Create the trigger on auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION public.handle_new_user TO supabase_auth_admin;
REVOKE EXECUTE ON FUNCTION public.handle_new_user FROM authenticated, anon, public;

-- Add a comment to describe the function
COMMENT ON FUNCTION public.handle_new_user() IS 'Handles new user creation by automatically creating user profiles';

-- Create a function to populate user_name for existing users
CREATE OR REPLACE FUNCTION populate_existing_users_username()
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    user_record RECORD;
    generated_username TEXT;
BEGIN
    -- Loop through all users who don't have a user_name
    FOR user_record IN 
        SELECT user_id, name, email 
        FROM users 
        WHERE user_name IS NULL OR user_name = ''
    LOOP
        -- Generate a unique username for this user
        generated_username := generate_unique_username(
            COALESCE(user_record.name, ''), 
            COALESCE(user_record.email, '')
        );
        
        -- Update the user record
        UPDATE users 
        SET user_name = generated_username 
        WHERE user_id = user_record.user_id;
    END LOOP;
END;
$$;

-- Add a comment to describe the function
COMMENT ON FUNCTION populate_existing_users_username() IS 'Populates user_name field for existing users who dont have one';

-- Create a function to populate user_name for existing users with NULL values
CREATE OR REPLACE FUNCTION populate_missing_usernames()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  updated_count INTEGER := 0;
  user_record RECORD;
  generated_username TEXT;
BEGIN
  -- Loop through all user profiles with NULL user_name
  FOR user_record IN 
    SELECT id, full_name 
    FROM user_profiles 
    WHERE user_name IS NULL
  LOOP
    -- Generate a username for this user
    BEGIN
      generated_username := public.generate_unique_username(
        COALESCE(user_record.full_name, ''), 
        COALESCE((SELECT email FROM auth.users WHERE id = user_record.id), '')
      );
      
      -- Update the user profile with the generated username
      UPDATE user_profiles 
      SET user_name = generated_username 
      WHERE id = user_record.id;
      
      updated_count := updated_count + 1;
    EXCEPTION 
      WHEN OTHERS THEN
        RAISE WARNING 'Error generating username for user %: %', user_record.id, SQLERRM;
    END;
  END LOOP;
  
  RETURN updated_count;
END;
$$;

-- Add a comment to describe the function
COMMENT ON FUNCTION populate_missing_usernames() IS 'Populates user_name field for user profiles that have NULL values';

-- Create a function that can be called to ensure a user profile exists
CREATE OR REPLACE FUNCTION public.ensure_user_profile_exists(user_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  user_record RECORD;
BEGIN
  -- Check if user profile already exists
  IF NOT EXISTS (SELECT 1 FROM user_profiles WHERE id = user_id) THEN
    -- Get user data from auth.users
    SELECT id, email, raw_user_meta_data 
    INTO user_record
    FROM auth.users 
    WHERE id = user_id;
    
    -- Create user profile if user exists
    IF FOUND THEN
      INSERT INTO public.user_profiles (id, full_name, avatar_url)
      VALUES (
        user_record.id,
        COALESCE(user_record.raw_user_meta_data->>'name', SPLIT_PART(user_record.email, '@', 1)),
        user_record.raw_user_meta_data->>'picture'
      )
      ON CONFLICT (id) DO NOTHING;
    END IF;
  END IF;
END;
$$;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION public.ensure_user_profile_exists(UUID) TO authenticated;

-- Add a comment to describe the function
COMMENT ON FUNCTION public.ensure_user_profile_exists(UUID) IS 'Ensures a user profile exists for the given user ID, creating one if necessary';
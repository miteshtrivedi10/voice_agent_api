-- Custom Access Token Hook for Supabase Authentication

-- Create the custom access token hook function that adds user_name to JWT claims
CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $function$
DECLARE
  original_claims jsonb;
  new_claims jsonb;
  user_id uuid;
  user_name_text text;
BEGIN
  original_claims := event->'claims';
  new_claims := '{}'::jsonb;

  -- Copy ALL required standard claims (Supabase requires these)
  IF original_claims ? 'sub' THEN
    new_claims := jsonb_set(new_claims, '{sub}', original_claims->'sub');
  END IF;
  
  IF original_claims ? 'aud' THEN
    new_claims := jsonb_set(new_claims, '{aud}', original_claims->'aud');
  END IF;
  
  IF original_claims ? 'exp' THEN
    new_claims := jsonb_set(new_claims, '{exp}', original_claims->'exp');
  END IF;
  
  IF original_claims ? 'iat' THEN
    new_claims := jsonb_set(new_claims, '{iat}', original_claims->'iat');
  END IF;
  
  IF original_claims ? 'email' THEN
    new_claims := jsonb_set(new_claims, '{email}', original_claims->'email');
  END IF;
  
  IF original_claims ? 'phone' THEN
    new_claims := jsonb_set(new_claims, '{phone}', original_claims->'phone');
  END IF;
  
  IF original_claims ? 'role' THEN
    new_claims := jsonb_set(new_claims, '{role}', original_claims->'role');
  END IF;
  
  IF original_claims ? 'aal' THEN
    new_claims := jsonb_set(new_claims, '{aal}', original_claims->'aal');
  END IF;
  
  IF original_claims ? 'session_id' THEN
    new_claims := jsonb_set(new_claims, '{session_id}', original_claims->'session_id');
  END IF;
  
  IF original_claims ? 'is_anonymous' THEN
    new_claims := jsonb_set(new_claims, '{is_anonymous}', original_claims->'is_anonymous');
  END IF;
  
  -- Copy optional claims you specifically requested
  -- Handle name fields from user_metadata if they exist
  IF original_claims ? 'user_metadata' THEN
    IF (original_claims->'user_metadata') ? 'full_name' THEN
      new_claims := jsonb_set(new_claims, '{full_name}', original_claims->'user_metadata'->'full_name');
    END IF;
    
    IF (original_claims->'user_metadata') ? 'name' THEN
      new_claims := jsonb_set(new_claims, '{name}', original_claims->'user_metadata'->'name');
    END IF;
  END IF;
  
  -- Add uid as an alias for sub
  IF original_claims ? 'sub' THEN
    new_claims := jsonb_set(new_claims, '{uid}', original_claims->'sub');
  END IF;
  
  -- Fetch and add user_name from user_profiles table
  IF original_claims ? 'sub' THEN
    user_id := (original_claims->>'sub')::uuid;
    
    -- Get user_name from user_profiles table
    BEGIN
      SELECT user_name INTO user_name_text
      FROM user_profiles
      WHERE id = user_id;
      
      -- Add user_name to claims if found
      IF user_name_text IS NOT NULL THEN
        new_claims := jsonb_set(new_claims, '{user_name}', to_jsonb(user_name_text));
      ELSE
        -- If user_name is NULL, try to generate one on-the-fly
        -- This handles edge cases where the trigger might have failed
        DECLARE
          user_email TEXT;
          user_full_name TEXT;
        BEGIN
          SELECT email, raw_user_meta_data->>'name' 
          INTO user_email, user_full_name
          FROM auth.users 
          WHERE id = user_id;
          
          IF user_full_name IS NOT NULL OR user_email IS NOT NULL THEN
            user_name_text := public.generate_unique_username(
              COALESCE(user_full_name, ''), 
              COALESCE(user_email, '')
            );
            
            -- Update the user profile with the generated username
            UPDATE user_profiles 
            SET user_name = user_name_text 
            WHERE id = user_id;
            
            -- Add the generated user_name to claims
            new_claims := jsonb_set(new_claims, '{user_name}', to_jsonb(user_name_text));
          END IF;
        EXCEPTION 
          WHEN OTHERS THEN
            -- Log error but don't stop the process
            RAISE WARNING 'Error generating user_name on-the-fly for user %: %', user_id, SQLERRM;
        END;
      END IF;
    EXCEPTION 
      WHEN OTHERS THEN
        -- Log error but don't stop the process
        RAISE WARNING 'Error fetching user_name for user %: %', user_id, SQLERRM;
    END;
  END IF;

  -- Return the modified event with new claims
  RETURN jsonb_set(event, '{claims}', new_claims);
END;
$function$;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO supabase_auth_admin;
REVOKE EXECUTE ON FUNCTION public.custom_access_token_hook FROM authenticated, anon, public;

-- Add a comment to describe the function
COMMENT ON FUNCTION public.custom_access_token_hook() IS 'Custom access token hook that adds user_name to JWT claims';
-- Database schema for Voice Agent API
-- This file contains the complete table definitions for all tables in the public schema

-- Enable pgcrypto extension for UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Table: users (extends auth.users)
CREATE TABLE IF NOT EXISTS public.users (
    user_id character varying NOT NULL,
    name character varying NOT NULL,
    email character varying NOT NULL,
    picture text,
    login_count integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    user_name TEXT UNIQUE,
    CONSTRAINT users_pkey PRIMARY KEY (user_id),
    CONSTRAINT users_email_key UNIQUE (email)
);

-- Table: user_voice_sessions
CREATE TABLE IF NOT EXISTS public.user_voice_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    room_name TEXT NOT NULL,
    duration INTEGER DEFAULT 0,
    start_time TEXT,
    end_time TEXT
);

-- Table: file_details
CREATE TABLE IF NOT EXISTS public.file_details (
    user_id TEXT NOT NULL,
    file_id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    subject TEXT,
    file_size INTEGER,
    file_type TEXT,
    is_processed BOOLEAN DEFAULT FALSE,
    total_generated_qna INTEGER DEFAULT 0,
    upload_timestamp TEXT,
    processed_timestamp TEXT,
    user_name TEXT
);

-- Table: question_and_answers
CREATE TABLE IF NOT EXISTS public.question_and_answers (
    question_id text NOT NULL,
    user_id text NOT NULL,
    file_id text NOT NULL,
    question text NOT NULL,
    answer text NOT NULL,
    timestamp text NOT NULL,
    CONSTRAINT question_and_answers_pkey PRIMARY KEY (question_id)
);

-- Table: user_profiles
CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  user_name TEXT UNIQUE,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_voice_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.file_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.question_and_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "users_select" ON public.users FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "users_insert" ON public.users FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "users_update" ON public.users FOR UPDATE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "users_delete" ON public.users FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- RLS Policies for user_voice_sessions table
CREATE POLICY "user_voice_sessions_select" ON public.user_voice_sessions FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "user_voice_sessions_insert" ON public.user_voice_sessions FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "user_voice_sessions_update" ON public.user_voice_sessions FOR UPDATE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "user_voice_sessions_delete" ON public.user_voice_sessions FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- RLS Policies for file_details table
CREATE POLICY "file_details_select" ON public.file_details FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "file_details_insert" ON public.file_details FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "file_details_update" ON public.file_details FOR UPDATE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "file_details_delete" ON public.file_details FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- RLS Policies for question_and_answers table
CREATE POLICY "question_and_answers_select" ON public.question_and_answers FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "question_and_answers_insert" ON public.question_and_answers FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "question_and_answers_update" ON public.question_and_answers FOR UPDATE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "question_and_answers_delete" ON public.question_and_answers FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- RLS Policies for user_profiles table
CREATE POLICY "Users can read their own profile" ON user_profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile" ON user_profiles
  FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert their own profile" ON user_profiles
  FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Service role can delete profiles" ON user_profiles
  FOR DELETE USING (CURRENT_USER = 'supabase_admin');

-- Grant necessary permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE users TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE user_voice_sessions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE file_details TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE question_and_answers TO authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE user_profiles TO authenticated;

-- Grant all permissions to service role (used by Supabase dashboard)
GRANT ALL ON TABLE user_profiles TO supabase_admin;

-- Revoke DELETE permission from authenticated users for user_profiles
REVOKE DELETE ON TABLE user_profiles FROM authenticated;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_user_name ON users(user_name);
CREATE INDEX IF NOT EXISTS idx_file_details_user_name ON file_details(user_name);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_name ON user_profiles(user_name);
CREATE INDEX IF NOT EXISTS idx_files_user_id ON file_details(user_id);

-- Add comments to describe the purpose of the tables
COMMENT ON TABLE user_profiles IS 'User profiles that extend auth.users with additional information';
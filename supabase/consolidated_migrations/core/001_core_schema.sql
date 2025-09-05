-- Core Database Schema for Voice Agent API
-- This file contains all the base table definitions

-- Enable required extensions
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

-- Add comments to describe the purpose of the tables
COMMENT ON TABLE user_profiles IS 'User profiles that extend auth.users with additional information';

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_user_name ON users(user_name);
CREATE INDEX IF NOT EXISTS idx_file_details_user_name ON file_details(user_name);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_name ON user_profiles(user_name);
CREATE INDEX IF NOT EXISTS idx_files_user_id ON file_details(user_id);
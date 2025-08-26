-- Database schema for Voice Agent API
-- This file contains the table definitions for all tables in the public schema

-- Enable pgcrypto extension for UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Table: users
CREATE TABLE IF NOT EXISTS public.users (
    user_id character varying NOT NULL,
    name character varying NOT NULL,
    email character varying NOT NULL,
    picture text,
    login_count integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT users_pkey PRIMARY KEY (user_id),
    CONSTRAINT users_email_key UNIQUE (email)
);

-- Enable RLS for users table
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Table: user_voice_sessions
-- (Originally from database/schema.sql)
CREATE TABLE IF NOT EXISTS public.user_voice_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    room_name TEXT NOT NULL,
    duration INTEGER DEFAULT 0,
    start_time TEXT,
    end_time TEXT
);

-- Enable RLS for user_voice_sessions table
ALTER TABLE public.user_voice_sessions ENABLE ROW LEVEL SECURITY;

-- Table: file_details
-- (Originally from database/schema.sql)
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
    processed_timestamp TEXT
);

-- Enable RLS for file_details table
ALTER TABLE public.file_details ENABLE ROW LEVEL SECURITY;

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

-- Enable RLS for question_and_answers table
ALTER TABLE public.question_and_answers ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "users_select" ON public.users FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "users_insert" ON public.users FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "users_update" ON public.users FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "users_delete" ON public.users FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for user_voice_sessions table
CREATE POLICY "user_voice_sessions_select" ON public.user_voice_sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "user_voice_sessions_insert" ON public.user_voice_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "user_voice_sessions_update" ON public.user_voice_sessions FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "user_voice_sessions_delete" ON public.user_voice_sessions FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for file_details table
CREATE POLICY "file_details_select" ON public.file_details FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "file_details_insert" ON public.file_details FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "file_details_update" ON public.file_details FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "file_details_delete" ON public.file_details FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for question_and_answers table
CREATE POLICY "question_and_answers_select" ON public.question_and_answers FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "question_and_answers_insert" ON public.question_and_answers FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "question_and_answers_update" ON public.question_and_answers FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "question_and_answers_delete" ON public.question_and_answers FOR DELETE USING (auth.uid() = user_id);
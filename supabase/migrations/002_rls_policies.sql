-- Row Level Security Policies for all tables

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
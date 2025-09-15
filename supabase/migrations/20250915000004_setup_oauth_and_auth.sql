-- Setup OAuth providers and authentication settings

-- Enable the auth schema
create schema if not exists auth;

-- Create auth.users table (simplified version for reference)
-- Note: In Supabase, this table is typically managed by the auth system
-- This is just for reference and testing purposes
create table if not exists auth.users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  encrypted_password text,
  email_confirmed_at timestamptz,
  invited_at timestamptz,
  confirmation_token text,
  confirmation_sent_at timestamptz,
  recovery_token text,
  recovery_sent_at timestamptz,
  email_change_token_new text,
  email_change text,
  email_change_sent_at timestamptz,
  last_sign_in_at timestamptz,
  raw_app_meta_data jsonb,
  raw_user_meta_data jsonb,
  is_super_admin bool,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Create a function to handle new user creation
create or replace function public.handle_new_user()
returns trigger as $$
begin
  -- Insert into public.users table when a new auth user is created
  insert into public.users (id, email, full_name, created_at)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data->>'full_name',
    new.created_at
  );
  return new;
end;
$$ language plpgsql security definer;

-- Create a trigger to automatically create a public user record when a new auth user is created
-- Note: This would typically be handled by Supabase auth hooks
-- create trigger on_auth_user_created
--   after insert on auth.users
--   for each row execute procedure public.handle_new_user();

-- Create a simplified public users table to store additional user information
create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique not null,
  full_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Enable RLS on public.users
alter table public.users enable row level security;

-- Create policies for public.users
create policy "Users can view their own profile" on public.users
  for select using (auth.uid() = id);

create policy "Users can update their own profile" on public.users
  for update using (auth.uid() = id);

-- Grant necessary permissions
grant usage on schema public to authenticated;
grant all on table public.users to authenticated;

-- Create trigger to automatically update updated_at column
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
   NEW.updated_at = now(); 
   return NEW; 
end;
$$ language 'plpgsql';

create trigger update_users_updated_at 
  before update on public.users 
  for each row 
  execute procedure public.update_updated_at_column();
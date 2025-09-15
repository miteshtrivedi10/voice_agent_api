# OAuth Provider Configuration Guide

This document provides guidance on setting up OAuth providers for your Supabase project.

## Supported OAuth Providers

Supabase supports the following OAuth providers:
1. Google
2. GitHub
3. GitLab
4. Bitbucket
5. Discord
6. Twitch
7. Twitter
8. Facebook
9. LinkedIn
10. Azure Active Directory
11. Apple
12. Slack
13. Spotify

## Configuration Steps

### 1. Google OAuth Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application" as the application type
6. Add the following authorized redirect URIs:
   - `https://<your-project-ref>.supabase.co/auth/v1/callback`
   - `http://localhost:3000/**` (for local development)
7. Save and note the Client ID and Client Secret

### 2. GitHub OAuth Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the application details:
   - Application name: Your app name
   - Homepage URL: Your app's homepage
   - Authorization callback URL: `https://<your-project-ref>.supabase.co/auth/v1/callback`
4. Save and note the Client ID and Client Secret

### 3. Configuring Providers in Supabase Dashboard

1. Log in to your Supabase project dashboard
2. Navigate to "Authentication" > "Providers"
3. Enable the providers you want to use
4. For each enabled provider, enter:
   - Client ID (from the provider setup)
   - Client Secret (from the provider setup)
   - Redirect URL (should be automatically set by Supabase)

## Environment Variables

Add the following to your `.env` file:

```env
# OAuth Client IDs and Secrets (add as needed)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

## Supabase Auth Configuration

The following SQL script sets up the necessary database structures for authentication:

```sql
-- Enable the auth schema
create schema if not exists auth;

-- Create auth.users table (managed by Supabase auth)
-- Note: This is typically managed automatically by Supabase

-- Create a public users table for additional user information
create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique not null,
  full_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Enable RLS
alter table public.users enable row level security;

-- Create policies
create policy "Users can view their own profile" on public.users
  for select using (auth.uid() = id);

create policy "Users can update their own profile" on public.users
  for update using (auth.uid() = id);

-- Grant permissions
grant usage on schema public to authenticated;
grant all on table public.users to authenticated;

-- Create updated_at trigger
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
```

## Client-Side Implementation

To implement OAuth login in your frontend application:

```javascript
// Example with Google OAuth
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'google',
  options: {
    redirectTo: 'http://localhost:3000/welcome'
  }
});

// Example with GitHub OAuth
const { data, error } = await supabase.auth.signInWithOAuth({
  provider: 'github',
  options: {
    redirectTo: 'http://localhost:3000/welcome'
  }
});
```

## Security Best Practices

1. Always use HTTPS in production
2. Store client secrets securely (never in client-side code)
3. Use PKCE for public clients
4. Implement proper session management
5. Regularly rotate client secrets
6. Monitor authentication logs for suspicious activity
-- Security and authentication setup script

-- Enable necessary extensions
create extension if not exists "uuid-ossp";

-- Create roles if they don't exist
do $$
begin
  create role authenticated;
  exception when duplicate_object then null;
end
$$;

do $$
begin
  create role anon;
  exception when duplicate_object then null;
end
$$;

-- Grant default privileges
alter default privileges in schema public grant all on tables to authenticated;
alter default privileges in schema public grant all on functions to authenticated;
alter default privileges in schema public grant all on sequences to authenticated;

-- Set up authentication
create schema if not exists auth;
grant usage on schema auth to authenticated, anon;

-- Create a function to get the current user ID
create or replace function auth.uid()
returns text as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::text;
$$ language sql stable;

-- Create a function to get user email
create or replace function auth.email()
returns text as $$
  select nullif(current_setting('request.jwt.claim.email', true), '')::text;
$$ language sql stable;

-- Create a function to check if user is authenticated
create or replace function auth.role()
returns text as $$
  select nullif(current_setting('request.jwt.claim.role', true), '')::text;
$$ language sql stable;

-- Grant necessary permissions
grant usage on schema public to authenticated, anon;
grant select on all tables in schema public to authenticated;
grant insert on all tables in schema public to authenticated;
grant update on all tables in schema public to authenticated;
grant delete on all tables in schema public to authenticated;
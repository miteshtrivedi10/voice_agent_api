-- Create a function to get user profile information
create or replace function get_user_profile(user_id_param uuid)
returns table(
  id uuid,
  email text,
  full_name text,
  avatar_url text,
  created_at timestamptz,
  updated_at timestamptz
) as $$
begin
  return query
  select 
    u.id,
    u.email,
    u.full_name,
    u.avatar_url,
    u.created_at,
    u.updated_at
  from public.users u
  where u.id = user_id_param;
end;
$$ language plpgsql security definer;

-- Grant execute permission on the function
grant execute on function get_user_profile(uuid) to authenticated;
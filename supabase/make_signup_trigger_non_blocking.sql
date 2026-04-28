-- Make Supabase auth signup resilient by moving profile/data_sources creation to FastAPI.
--
-- Why this exists:
-- Supabase returns "Database error creating new user" whenever the auth.users
-- trigger fails. That hides the real DB error and blocks registration entirely.
-- The backend now creates/updates public.profiles and public.data_sources after
-- auth user creation, so this trigger should never block auth signup.
--
-- Run this whole file once in Supabase SQL Editor.

begin;

create or replace function public.handle_new_user()
returns trigger as $$
begin
  -- Do not write application rows here. FastAPI /auth/register seeds them with
  -- the service role after Supabase Auth successfully creates the user.
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

commit;

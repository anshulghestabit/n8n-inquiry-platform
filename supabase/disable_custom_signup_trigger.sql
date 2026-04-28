-- Emergency fix for Supabase Auth error:
--   "Database error creating new user"
--
-- The FastAPI backend now creates public.profiles and public.data_sources after
-- Supabase Auth creates the user. Therefore the custom auth.users trigger is no
-- longer required, and removing it prevents trigger failures from blocking signup.
--
-- Run this file in Supabase SQL Editor, then retry registration.

drop trigger if exists on_auth_user_created on auth.users;

-- Optional verification: should return zero rows for on_auth_user_created.
select
  trigger_name,
  event_object_schema,
  event_object_table,
  action_statement
from information_schema.triggers
where event_object_schema = 'auth'
  and event_object_table = 'users'
  and trigger_name = 'on_auth_user_created';

-- Fix registration failures after switching the optional second channel from WhatsApp to Telegram.
--
-- Symptom in FastAPI /auth/register:
--   AuthApiError: Database error creating new user
--
-- Root cause:
--   Supabase runs public.handle_new_user() inside the auth user creation transaction.
--   If an older database still has CHECK constraints that allow 'whatsapp' but not
--   'telegram', the trigger insert into public.data_sources fails and Supabase rolls
--   back the auth user creation.
--
-- Run this whole file once in Supabase SQL Editor.

begin;

-- Drop old CHECK constraints by table/column, regardless of generated constraint name.
do $$
declare
  c record;
begin
  for c in
    select conname, conrelid::regclass as table_name
    from pg_constraint
    where contype = 'c'
      and conrelid in (
        'public.workflows'::regclass,
        'public.executions'::regclass,
        'public.data_sources'::regclass
      )
      and (
        pg_get_constraintdef(oid) like '%trigger_channel%'
        or pg_get_constraintdef(oid) like '%source_channel%'
        or pg_get_constraintdef(oid) like '%source_type%'
      )
  loop
    execute format('alter table %s drop constraint if exists %I', c.table_name, c.conname);
  end loop;
end $$;

-- Normalize existing legacy rows before re-adding constraints.
update public.workflows
set trigger_channel = 'telegram'
where trigger_channel = 'whatsapp';

update public.executions
set source_channel = 'telegram'
where source_channel = 'whatsapp';

-- Merge data_sources whatsapp rows into telegram rows without violating unique(user_id, source_type).
insert into public.data_sources (user_id, source_type, is_connected, last_verified_at)
select user_id, 'telegram', is_connected, last_verified_at
from public.data_sources
where source_type = 'whatsapp'
on conflict (user_id, source_type) do update
set
  is_connected = public.data_sources.is_connected or excluded.is_connected,
  last_verified_at = coalesce(excluded.last_verified_at, public.data_sources.last_verified_at);

delete from public.data_sources
where source_type = 'whatsapp';

-- Recreate constraints matching the current application code.
alter table public.workflows
  add constraint workflows_trigger_channel_check
  check (trigger_channel in ('gmail','telegram','both'));

alter table public.executions
  add constraint executions_source_channel_check
  check (source_channel in ('gmail','telegram','test'));

alter table public.data_sources
  add constraint data_sources_source_type_check
  check (source_type in ('gmail','telegram','google_drive','google_sheets'));

-- Recreate signup trigger function with current source rows and conflict safety.
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', '')
  )
  on conflict (id) do update
  set
    email = excluded.email,
    full_name = excluded.full_name;

  insert into public.data_sources (user_id, source_type, is_connected)
  values
    (new.id, 'gmail', false),
    (new.id, 'telegram', false),
    (new.id, 'google_drive', false),
    (new.id, 'google_sheets', false)
  on conflict (user_id, source_type) do nothing;

  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

commit;

-- Quick verification after running this file:
-- select source_type from public.data_sources group by source_type order by source_type;
-- Expected values: gmail, google_drive, google_sheets, telegram

-- Migrates the live Supabase channel model from WhatsApp to Telegram.
-- Safe to run after the original schema was applied with whatsapp checks/data.

begin;

alter table public.workflows
drop constraint if exists workflows_trigger_channel_check;

update public.workflows
set trigger_channel = 'telegram'
where trigger_channel = 'whatsapp';

alter table public.workflows
add constraint workflows_trigger_channel_check
check (trigger_channel in ('gmail','telegram','both'));

alter table public.executions
drop constraint if exists executions_source_channel_check;

update public.executions
set source_channel = 'telegram'
where source_channel = 'whatsapp';

alter table public.executions
add constraint executions_source_channel_check
check (source_channel in ('gmail','telegram','test'));

alter table public.data_sources
drop constraint if exists data_sources_source_type_check;

-- Merge old whatsapp integration rows into telegram rows without violating
-- the unique(user_id, source_type) constraint if both rows already exist.
insert into public.data_sources (user_id, source_type, is_connected, last_verified_at)
select
  user_id,
  'telegram',
  bool_or(is_connected),
  max(last_verified_at)
from public.data_sources
where source_type = 'whatsapp'
group by user_id
on conflict (user_id, source_type) do update
set
  is_connected = public.data_sources.is_connected or excluded.is_connected,
  last_verified_at = greatest(public.data_sources.last_verified_at, excluded.last_verified_at);

delete from public.data_sources
where source_type = 'whatsapp';

alter table public.data_sources
add constraint data_sources_source_type_check
check (source_type in ('gmail','telegram','google_drive','google_sheets'));

commit;

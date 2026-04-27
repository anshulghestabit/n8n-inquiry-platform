-- ============================================
-- PART 1: TABLES
-- ============================================

create extension if not exists "uuid-ossp";

create table public.profiles (
  id uuid references auth.users(id) on delete cascade primary key,
  email text not null,
  full_name text,
  avatar_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table public.workflows (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  description text,
  trigger_channel text check (
    trigger_channel in ('gmail','whatsapp','both')
  ) default 'gmail',
  status text check (
    status in ('active','inactive','draft')
  ) default 'draft',
  n8n_workflow_id text,
  agent_config jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table public.agents (
  id uuid default uuid_generate_v4() primary key,
  workflow_id uuid references public.workflows(id) on delete cascade not null,
  name text not null,
  role text check (
    role in ('classifier','researcher','qualifier','responder','executor')
  ) not null,
  system_prompt text not null,
  tools jsonb default '[]',
  handoff_rules text,
  output_format text default 'json',
  order_index integer not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table public.executions (
  id uuid default uuid_generate_v4() primary key,
  workflow_id uuid references public.workflows(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  n8n_execution_id text,
  source_channel text check (
    source_channel in ('gmail','whatsapp','test')
  ),
  status text check (
    status in ('running','success','failed','cancelled')
  ) default 'running',
  inquiry_snippet text,
  sender_id text,
  final_reply text,
  started_at timestamptz default now(),
  finished_at timestamptz,
  duration_ms integer,
  score integer check (score >= 1 and score <= 10),
  scorecard_detail jsonb default '{}'
);

create table public.agent_logs (
  id uuid default uuid_generate_v4() primary key,
  execution_id uuid references public.executions(id) on delete cascade not null,
  agent_role text check (
    agent_role in ('classifier','researcher','qualifier','responder','executor')
  ) not null,
  input jsonb,
  output jsonb,
  duration_ms integer not null default 0,
  status text check (
    status in ('success','failed','skipped')
  ) default 'success',
  error_message text,
  created_at timestamptz default now()
);

create table public.data_sources (
  id uuid default uuid_generate_v4() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  source_type text check (
    source_type in ('gmail','whatsapp','google_drive','google_sheets')
  ) not null,
  is_connected boolean default false,
  last_verified_at timestamptz,
  created_at timestamptz default now(),
  unique(user_id, source_type)
);

-- ============================================
-- PART 2: INDEXES + TRIGGERS
-- ============================================

create index on public.workflows(user_id);
create index on public.executions(workflow_id);
create index on public.executions(user_id);
create index on public.executions(started_at desc);
create index on public.agent_logs(execution_id);
create index on public.agent_logs(agent_role);

create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger workflows_updated_at
  before update on public.workflows
  for each row execute function update_updated_at();

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute function update_updated_at();

create trigger agents_updated_at
  before update on public.agents
  for each row execute function update_updated_at();

create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', '')
  );
  insert into public.data_sources (user_id, source_type, is_connected)
  values
    (new.id, 'gmail', false),
    (new.id, 'whatsapp', false),
    (new.id, 'google_drive', false),
    (new.id, 'google_sheets', false);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================
-- PART 3: ROW LEVEL SECURITY
-- ============================================

alter table public.profiles enable row level security;
alter table public.workflows enable row level security;
alter table public.agents enable row level security;
alter table public.executions enable row level security;
alter table public.agent_logs enable row level security;
alter table public.data_sources enable row level security;

create policy "own profile"
  on public.profiles for all using (auth.uid() = id);

create policy "own workflows"
  on public.workflows for all using (auth.uid() = user_id);

create policy "own agents"
  on public.agents for all using (
    exists (
      select 1 from public.workflows
      where id = agents.workflow_id and user_id = auth.uid()
    )
  );

create policy "own executions"
  on public.executions for all using (auth.uid() = user_id);

create policy "own agent logs"
  on public.agent_logs for all using (
    exists (
      select 1 from public.executions
      where id = agent_logs.execution_id and user_id = auth.uid()
    )
  );

create policy "own data sources"
  on public.data_sources for all using (auth.uid() = user_id);

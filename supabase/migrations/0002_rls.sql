-- Supabase RLS — defesa em profundidade (PREPARADO, NÃO APLICADO).
--
-- Contexto: ADR-001, docs/migrations/SUPABASE_MIGRATION.md, docs/security/SECURITY.md.
-- O runtime atual é SQLAlchemy com role de servidor; RLS só passa a valer se
-- houver acesso PostgREST direto. Nunca desative RLS para contornar erro.
--
-- PRÉ-REQUISITO DE IDENTIDADE (decisão pendente do cutover):
-- `auth.uid()` do Supabase é UUID, enquanto public.users.id é SERIAL/INTEGER.
-- Para não criar coluna nova, esta versão usa a claim de sessão `app.user_id`,
-- que a camada de aplicação DEVE definir por requisição:
--     SET LOCAL app.user_id = '42';
-- (com PostgREST, via `request.headers` + trigger/função de mapeamento).
-- Se o projeto adotar Supabase Auth, substitua app_current_user_id() por um
-- mapeamento explícito auth.users.id -> public.users.id antes de aplicar.

create or replace function public.app_current_user_id()
returns integer
language sql
stable
as $$
  select nullif(current_setting('app.user_id', true), '')::integer;
$$;

comment on function public.app_current_user_id() is
  'ID do usuário Finance OS derivado da claim de sessão app.user_id (SET LOCAL).';

-- ---------------------------------------------------------------------------
-- Habilita RLS em TODAS as tabelas de aplicação.
-- alembic_version é internally gerenciada pelo Alembic e fica de fora.
-- ---------------------------------------------------------------------------
alter table public.users enable row level security;
alter table public.accounts enable row level security;
alter table public.assets enable row level security;
alter table public.asset_prices enable row level security;
alter table public.categories enable row level security;
alter table public.transactions enable row level security;
alter table public.investment_operations enable row level security;
alter table public.credit_cards enable row level security;
alter table public.vaults enable row level security;
alter table public.budgets enable row level security;
alter table public.goals enable row level security;
alter table public.scheduled_bills enable row level security;
alter table public.password_reset_tokens enable row level security;
alter table public.refresh_tokens enable row level security;
alter table public.rate_limit_hits enable row level security;
alter table public.login_attempts enable row level security;

-- ---------------------------------------------------------------------------
-- Isolamento por usuário.
-- ---------------------------------------------------------------------------
drop policy if exists owner_isolation on public.users;
create policy owner_isolation on public.users
  for all using (id = public.app_current_user_id())
  with check (id = public.app_current_user_id());

-- Categorias do sistema (is_system) são legíveis por todos; as demais, só do dono.
-- NUNCA use `user_id is null` como critério de acesso irrestrito.
drop policy if exists owner_isolation on public.categories;
create policy owner_isolation on public.categories
  for all using (
    user_id = public.app_current_user_id()
    or (is_system and user_id is null)
  )
  with check (
    user_id = public.app_current_user_id()
    or (is_system and user_id is null)
  );

drop policy if exists owner_isolation on public.accounts;
create policy owner_isolation on public.accounts
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

drop policy if exists owner_isolation on public.assets;
create policy owner_isolation on public.assets
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

drop policy if exists owner_isolation on public.transactions;
create policy owner_isolation on public.transactions
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

drop policy if exists owner_isolation on public.budgets;
create policy owner_isolation on public.budgets
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

drop policy if exists owner_isolation on public.goals;
create policy owner_isolation on public.goals
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

drop policy if exists owner_isolation on public.scheduled_bills;
create policy owner_isolation on public.scheduled_bills
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

drop policy if exists owner_isolation on public.credit_cards;
create policy owner_isolation on public.credit_cards
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

drop policy if exists owner_isolation on public.vaults;
create policy owner_isolation on public.vaults
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

drop policy if exists owner_isolation on public.password_reset_tokens;
create policy owner_isolation on public.password_reset_tokens
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

drop policy if exists owner_isolation on public.refresh_tokens;
create policy owner_isolation on public.refresh_tokens
  for all using (user_id = public.app_current_user_id())
  with check (user_id = public.app_current_user_id());

-- Sem coluna user_id: isolamento via ativo dono.
drop policy if exists owner_isolation on public.asset_prices;
create policy owner_isolation on public.asset_prices
  for all using (
    exists (
      select 1 from public.assets a
      where a.id = asset_id and a.user_id = public.app_current_user_id()
    )
  )
  with check (
    exists (
      select 1 from public.assets a
      where a.id = asset_id and a.user_id = public.app_current_user_id()
    )
  );

drop policy if exists owner_isolation on public.investment_operations;
create policy owner_isolation on public.investment_operations
  for all using (
    exists (
      select 1 from public.assets a
      where a.id = asset_id and a.user_id = public.app_current_user_id()
    )
  )
  with check (
    exists (
      select 1 from public.assets a
      where a.id = asset_id and a.user_id = public.app_current_user_id()
    )
  );

-- rate_limit_hits e login_attempts são por IP/e-mail e não têm user_id.
-- RLS habilitado SEM política => authenticated não acessa; apenas a role de
-- servidor (dono da tabela) opera, como no comportamento atual.

-- ---------------------------------------------------------------------------
-- Menor privilégio: anon e service_role não leem dados financeiros.
-- A role de servidor usada pelo SQLAlchemy continua responsável pelo acesso
-- transacional (RLS não se aplica ao dono da tabela).
-- ---------------------------------------------------------------------------
revoke all on all tables in schema public from anon, service_role;
grant select, insert, update, delete on all tables in schema public to authenticated;

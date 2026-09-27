-- Supabase RLS — defesa em profundidade (NÃO APLICAR sem aprovação).
-- Contexto: docs/migrations/SUPABASE_MIGRATION.md §4, ADR-001.
-- Hoje o acesso é via SQLAlchemy (role servidor); estas políticas valem
-- para futuro PostgREST direto e como segunda camada.
-- Regra dura: nunca desative RLS para contornar erro de permissão.
-- Pré-requisito: vínculo auth.uid() ↔ public.users.id (a definir se adotar Supabase Auth).

-- Habilita RLS em todas as tabelas owned:
alter table public.users enable row level security;
alter table public.accounts enable row level security;
alter table public.categories enable row level security;
alter table public.transactions enable row level security;
alter table public.budgets enable row level security;
alter table public.goals enable row level security;
alter table public.scheduled_bills enable row level security;
alter table public.assets enable row level security;
alter table public.investment_operations enable row level security;

-- Isolamento por usuário (template — repetir por tabela):
-- users: cada um vê só a própria linha
drop policy if exists "owner_isolation" on public.users;
create policy "owner_isolation" on public.users
  for all using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists "owner_isolation" on public.accounts;
create policy "owner_isolation" on public.accounts
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "owner_isolation" on public.categories;
create policy "owner_isolation" on public.categories
  for all using (user_id = auth.uid() or user_id is null)
  with check (user_id = auth.uid() or user_id is null);

drop policy if exists "owner_isolation" on public.transactions;
create policy "owner_isolation" on public.transactions
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "owner_isolation" on public.budgets;
create policy "owner_isolation" on public.budgets
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "owner_isolation" on public.goals;
create policy "owner_isolation" on public.goals
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "owner_isolation" on public.scheduled_bills;
create policy "owner_isolation" on public.scheduled_bills
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "owner_isolation" on public.assets;
create policy "owner_isolation" on public.assets
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- investment_operations: via asset dono (join); alternativa simples: checar por account.user_id
-- Nota: requer função SECURITY DEFINER se PostgREST direto; manter como referência:
-- drop policy if exists "owner_isolation" on public.investment_operations;
-- create policy "owner_isolation" on public.investment_operations
--   for all using (
--     exists (select 1 from public.assets a where a.id = asset_id and a.user_id = auth.uid())
--   );

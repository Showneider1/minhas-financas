# Relatório de Staging — SQLite → Supabase (sem cutover)

**Data:** 2026-09-27. **Commit P0:** `c0c2b78ebe95d018d1612b1d30605e9c3c80ee1f` (90 arquivos).
**App continua em SQLite.** Nenhum dado destruído; `data/finance.db` intacto.

## 1. Conexão Supabase

`scripts/check_supabase_connection.py` → **exit 2: credenciais ausentes**.
`.env` contém `DATABASE_URL=sqlite…` e segredos de app, mas **nenhuma** de
`SUPABASE_DB_URL_POOLER` / `SUPABASE_URL` / `SUPABASE_ANON_KEY` /
`SUPABASE_SERVICE_ROLE_KEY` (verificado por nome, sem expor valores).
Sem Docker/Postgres local no ambiente → sem staging alternativo possível.
**Fases remotas abortadas por regra (não inventar credenciais).**

## 2. Migrations (offline, sem servidor)

Baseline `916651f2e591` renderizado para dialeto Postgres
(`supabase/migrations/0001_baseline_postgres.sql`, referência de revisão):
11 `CREATE TABLE`, **zero FLOAT/DOUBLE**, `NUMERIC(12,2)`/`NUMERIC(14,4)`,
enums como `VARCHAR` (`native_enum=False`), FKs com `ON DELETE`, `UNIQUE`
(`uq_category_name_user`, `uq_asset_ticker_user`, `unique_budget_per_month`),
`CHECK` (mês 1–12, valores > 0), 34 índices. `alembic upgrade head` real
pende das credenciais.

## 3. ETL (validado fim-a-fim em SQLite→SQLite com schema atual)

`scripts/migrate_sqlite_to_postgres.py` (ordem FK, IDs preservados, quantização
Q2/Q4, falha alta com rollback, `setval` no Postgres, `login_attempts` fora
por design): **28 linhas, 10/10 tabelas OK** (users 1, accounts 4, categories 11,
transactions 12, demais 0). Ramos Postgres (`setval`, NUMERIC) codificados mas
**não executados live** — marcados no relatório.

## 4. Reconciliação (prova matemática)

`scripts/reconcile_balances.py` (mesmo `BalanceService` nos dois bancos +
contagens + somas por tipo/status, tudo no centavo): **todas as diferenças ZERO** —
contas 1–4 (8746.45 / 0.00 / 0.00 / −574.67), somas por tipo/status idênticas, exit 0.

## 5. Riscos / bugs de dialeto mapeados

- SQLite DDL legado usa FLOAT; ETL quantiza (Q2/Q4) — poeira float eliminada na borda.
- `scheduled_bill_id REFERENCES scheduled_bill(id)` (nome errado) existiu no SQLite dev;
  corrigido; baseline usa `scheduled_bills` ✓ (verificado no SQL).
- Enums nativos evitados (`native_enum=False`) — `ALTER` futuro não trava.
- Timezone: SQLite naive × `timestamptz` — SQLAlchemy converte; validar 1 linha com tz no staging real.
- Sequences: `setval(max(id))` incluído no ETL (não executado live).

## 6. Próximo passo (cutover real, com credenciais)

1. Preencher `SUPABASE_DB_URL_POOLER` (+ `SUPABASE_URL/ANON_KEY`) no `.env`.
2. `check_supabase_connection.py` → exit 0.
3. `alembic upgrade head` no Supabase (via driver com DATABASE_URL temporário em memória).
4. ETL (`MIGRATION_TARGET_URL`=pooler) → reconcile exit 0.
5. Só então: janela de cutover (manutenção, dump final, switch, monitoramento).

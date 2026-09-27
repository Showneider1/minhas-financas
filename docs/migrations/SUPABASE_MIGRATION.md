# Plano de Migração — SQLite → Supabase Postgres

**Decisão:** `docs/decisions/ADR-001-supabase-migration.md` (manter SQLAlchemy; não adotar Supabase Auth agora).
**Núcleo:** `docs/decisions/ADR-002-financial-core.md` (contrato canônico P0).
**Status P0 (2026-09-27):** sistema preparado; **remoto NÃO configurado, NÃO validado** (sem credenciais — ver §7).
**Status staging (mesma data):** commit P0 `c0c2b78`; checker `scripts/check_supabase_connection.py`
(exit 2 = credenciais ausentes); ETL `scripts/migrate_sqlite_to_postgres.py` + reconciliação
`scripts/reconcile_balances.py` validados fim-a-fim em SQLite→SQLite (28 linhas, diff ZERO);
DDL Postgres do baseline renderizado offline em `supabase/migrations/0001_baseline_postgres.sql`
(11 CREATE TABLE, zero FLOAT, NUMERIC/VARCHAR/constraints OK). `upgrade head` + ETL + reconcile
contra o Supabase real pendem das credenciais (§7).
**Princípio:** migração segura, reversível, sem destrutivas no remoto sem aprovação humana.

## 1. Retrato do banco atual (verificado, não assumido)

| Item | Valor real |
|---|---|
| Banco | SQLite `data/finance.db` (~120 KB) |
| ORM | SQLAlchemy 2.0.36 síncrono (`database/connection.py:5-6`, `requirements.txt:10`) |
| Migrations | Nenhuma versionada. `alembic==1.13.3` declarado mas sem `alembic.ini`/`versions/`. Evolução via `Base.metadata.create_all()` (`database/connection.py:70`) + scripts ad-hoc |
| Tabelas físicas | `users, accounts, categories, assets, transactions, budgets, investment_operations, login_attempts` |
| Tabelas-modelo sem tabela física | `goals, scheduled_bills` (`init_db()` importa só 5 models — `database/connection.py:63-67`) |
| Volume | `users:1, accounts:4, categories:11, transactions:12, budgets:0, assets:0, investment_operations:0` (+ `login_attempts` operacional). `integrity_check=ok`, `foreign_key_check=[]` |
| Triggers/views/functions | Zero |
| Backup | Inexistente (nenhum `pg_dump`, PITR ou rotina; `data/*.db` no `.gitignore:7-10`) |
| Auth | JWT+bcrypt próprios (`config/security.py`, `services/auth_services.py`); `users.password_hash` local. Nenhuma dependência de provedor externo |
| Quem acessa o banco | Tudo via `get_db_session()` → repos/services chamados por callbacks Dash. Sem API HTTP. `LoginAttempt` cria tabela por side-effect no import (`middleware/rate_limiter.py:40-46`) |
| Ambientes | `config/settings.py:41` default SQLite; Postgres do `docker-compose.yml:4-14` só via override de `DATABASE_URL`; `ENVIRONMENT`/`DEBUG` com defaults inseguros (`settings.py:33-34,46-47`) |

## 2. Schema-alvo (normalização P0 — fazer ANTES do remoto)

Uma única migration de quebra (Alembic rev `0001_normalize`), depois só incrementais:

1. Dinheiro `Float→Numeric(12,2)` (`accounts.balance/initial_balance/credit_limit`, `transactions.base_amount`, `budgets.amount`, `goals.*amount`, `scheduled_bills.amount/paid_amount`); `Numeric(14,4)` para `investment_operations.quantity/price_per_unit/total_amount/fees`.
2. Decidir `amount` vs `base_amount` (ver `CODE_AUDIT.md` C1): ou adiciona `amount/interest/discount/cashback` ao model, ou remove dos repos. Não manter os dois.
3. Fonte única de “pago”: manter `status` ENUM + sincronizar com `paid_date` via validação aplicacional (sugestão), remover dupla semântica.
4. `is_deleted` onde repos filtram, ou remover filtro; implementar `Account.update_balance()` ou remover chamada (`account_repo.py:111`).
5. Enums: `native_enum=False` (ou `VARCHAR+CheckConstraint`) para não travar `ALTER` no Postgres.
6. `ondelete` em todas as FKs (`CASCADE`/`SET NULL` espelhando o cascade ORM em `user.py:31-36`); `server_default` nos booleans (`users.is_active/is_verified/is_deleted` hoje nullable); `UniqueConstraint(ticker,user_id)`, `UniqueConstraint(name,user_id)` (categories/accounts); `CheckConstraint(month 1-12, amount>0)`.
7. Trazer `LoginAttempt` para `database/models/`; padronizar tz (`now(timezone.utc)`); `String(32+)` para `Category.icon`.
8. Índices compostos do extrato: `transactions(user_id, paid_date)`, `transactions(user_id, due_date)`, `scheduled_bills(user_id, due_date, status)`, `investment_operations(asset_id, date)`.

## 3. Estratégia de conexão (segura)

- **Staging local:** Postgres do `docker-compose.yml` (adicionar `env_file`, healthcheck, serviço da app — ver §8).
- **Supabase (prod/staging remoto):** **Transaction Pooler porta 6543 + `sslmode=require`**. `DATABASE_URL` **somente** via env/Supabase Secrets. Formato:
  `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require`
- Engine: `pool_pre_ping=True, pool_size=5, max_overflow=10, pool_recycle=300, echo=False em prod`. SQLite permanece **só** para `pytest :memory:`.
- **Nunca logar a URL** (corrigido localmente em `database/connection.py` — máscara aplicada nesta sessão). `echo` desligado quando Postgres.
- Cliente Supabase opcional (`config/supabase.py`, lazy, só se `SUPABASE_URL`+`SUPABASE_ANON_KEY` existirem; service_role **nunca** no frontend, **nunca** commitado).

## 4. RLS (Row Level Security)

- **Hoje (acesso via SQLAlchemy, role servidor):** RLS **desligado para o role do backend** — o isolamento é aplicacional (`user_id` em toda query + `verify_token` nos callbacks). Ligar RLS no role servidor só quebraria o app.
- **Defesa em profundidade + futuro PostgREST:** criar políticas (arquivo `supabase/migrations/0002_rls.sql` nesta sessão) sem aplicá-las no remoto sem aprovação:
  ```sql
  alter table public.users enable row level security;
  -- ... idem para accounts, categories, transactions, budgets, goals, scheduled_bills, assets, investment_operations
  create policy "owner_isolation" on public.transactions for all using (user_id = auth.uid()) with check (user_id = auth.uid());
  -- repetir por tabela owned; tabelas vêem apenas as próprias linhas
  ```
- **Regra dura:** nunca desative RLS para contornar erro de permissão; corrija o `user_id`/JWT.
- **Testes de isolamento** (`tests/test_user_isolation.py`, criados nesta sessão, rodando em SQLite): usuário A não lê/atualiza/exclui dados de B. Devem passar no Postgres/Supabase antes do cutover.

## 5. Plano de migração de dados (Fase 4 — executar primeiro em local/homologação)

1. **Backup verificável:** `cp data/finance.db data/finance.db.pre-supabase-<data>` + `sha256sum` registrado; `sqlite3 .dump` versionado. Não excluir o SQLite.
2. **Mapeamento:** 1:1 por tabela (nomes iguais); `Float→Numeric` com `ROUND(x,2)`; `DATETIME` naive → `timestamptz`; `Enum` → `VARCHAR`/enum Postgres conforme §2; `import_hash` como chave de idempotência (re-run não duplica).
3. **Carga (banco minúsculo):** `alembic upgrade head` no Supabase vazio + script ETL `scripts/migrate_sqlite_to_supabase.py` (a criar na execução — `SELECT` SQLite → `INSERT` Postgres em transação, `ON CONFLICT(import_hash) DO NOTHING`).
4. **Verificação de integridade (gate do cutover):**
   - contagens por tabela origem == destino;
   - `SELECT SUM(base_amount)` por `transaction_type/status` origem == destino (±0,01);
   - FKs: zero órfãos (`LEFT JOIN ... WHERE ... IS NULL` vazio);
   - login + extrato + KPI + create/mark-paid smoke no staging apontado ao Supabase.
5. **Rollback:** voltar `DATABASE_URL` ao SQLite (arquivo preservado). Tempo estimado < 5 min (troca de env + restart).
6. **Cutover:** janela curta — `maintenance on → dump final → load → smoke → switch env → monitorar `pg_stat_statements` + logs (sem URL)`. Só com aprovação humana explícita.
7. **Destrutivas:** nenhuma `DROP/ALTER destrutivo` no remoto sem aprovação explícita. `create_db.reset_and_seed_db()` **proibido** em prod (trava por `ENVIRONMENT` a implementar).

## 6. O que foi implementado (P0 Missão 2 — local, seguro, reversível)

- `alembic/` + `alembic.ini` + `env.py` (URL via settings, batch, compare_type) +
  baseline `916651f2e591` (10 tabelas, Numeric, `native_enum=False`, ondelete,
  Unique/Check, índices compostos). **Validado:** `upgrade head` em banco fresco
  cria tudo; `stamp head` em cópia preserva dados; dev DB com `stamp` aplicado.
- Models Numeric + colunas de transferência (`destination_account_id`,
  `transfer_group_id`, `client_transfer_id` UNIQUE) + `scheduled_bill_id` +
  `password_reset_tokens`; dev DB evoluído de forma aditiva (backup
  `data/finance.db.pre-p0-*`, integrity ok, 12 tx preservadas) + saldos
  reconciliados via `BalanceService.reconcile`.
- `config/supabase.py` (lazy), `.env.example` (só nomes + POSTGRES_*),
  `supabase/migrations/0002_rls.sql` (pronto, **não aplicado**).
- `tests/test_user_isolation.py` expandidos (get_owned/update_owned/delete_owned).
- **Nada** apontado para remoto; **nenhuma** credencial inventada.

## 7. Pendências de configuração (bloqueiam validação remota — NÃO inventar)

- [x] Normalização P0 (§2): Numeric, amount canônico, pago único, ondelete/enums/tz, LoginAttempt documentado, índices.
- [x] `alembic` baseline + `stamp` dev + `upgrade` validado em fresco.
- [x] Isolamento por usuário + testes A×B.
- [ ] Criar projeto Supabase (região + ref). Necessário: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (vault só), `SUPABASE_DB_URL_POOLER` (6543 + `sslmode=require`).
- [ ] ETL `migrate_sqlite_to_supabase.py` + conciliação (`reconcile()` + contagens + somas ±0,01 + zero órfãos) assinada.
- [ ] Teste real de conexão (`SELECT 1` + `alembic upgrade head` em staging) — **não declarado como validado até ser executado**.
- [ ] Aprovação humana para cutover/rollback e para qualquer DDL destrutivo.

## 8. Ajustes futuros no `docker-compose.yml` (proposta, não aplicada sem aprovação)

Adicionar `env_file: [.env]`, `healthcheck: pg_isready`, remover credenciais hardcoded, decidir sobre `redis` (remover ou implementar cache — hoje morto), adicionar serviço da app com `release: alembic upgrade head`.

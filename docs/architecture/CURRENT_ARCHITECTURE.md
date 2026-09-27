# Arquitetura Atual — Finance OS (código REAL pós-P0, 2026-09-27)

> Substitui, para o código atual, `docs/architecture/ARCHITECTURE.md`
> (Next.js/NestJS/Prisma — proposta futura, nada disso executa).

## Estilo

**Monólito Dash + SQLAlchemy síncrono, sem API HTTP.** Mesma origem, server-side.

```
browser (Dash/Bootstrap)
  │ dcc.Store auth-store (JWT) — user_id derivado no backend (auth_context)
  ▼
myindex.py (roteamento + valida JWT) → pages/* + components/*
  │ callbacks/* (finos: resolve_user → service → formata Decimal p/ UI)
  ▼
services/* (regras: Finance, Balance, Transfer, Recurrence, Bills, Goals...)
  │ Decimal em tudo; commit/rollback explícitos
  ▼
database/* (models Numeric + repositories com get_owned)
  │ SQLAlchemy 2.0 sync — SQLite dev/test, Postgres (Supabase) alvo
  ▼
SQLite data/finance.db (Alembic baseline 916651f2e591, stamp aplicado)
```

## Camadas e contratos

| Camada | Papel | Contrato |
|---|---|---|
| `config/` | settings (fail-fast prod), security (JWT/bcrypt/reset jti), supabase (lazy) | env-only; sem segredo default em prod |
| `middleware/auth_context.py` | `resolve_user(auth_data, claimed?)` | única fonte de user_id p/ callbacks |
| `utils/money.py` | `to_money2/split_money/money_sum/avg_price` | Decimal-only; rejeita float/bool |
| `services/balance_service.py` | fórmula única de saldo + resumos + reconcile | ADR-002 §2 |
| `services/transfer_service.py` | 1 linha TRANSFER, idempotente | ADR-002 §3 |
| `services/finance_service.py` | CRUD INCOME/EXPENSE + sync status/saldo | base_amount Decimal; TRANSFER rejeitado |
| `services/recurrence_service.py` | parcelas (rateio) + recorrência mensal | soma == base; guards PENDING |
| `services/scheduled_bill_service.py` | contas a pagar/receber; pagar gera Transaction | vínculo scheduled_bill_id |
| `database/repositories/*` | queries com `user_id`; `get_owned/*_owned` | anti-IDOR |
| `alembic/` | baseline P0 (10 tabelas, Numeric, constraints, índices) | `upgrade` em banco novo; `stamp` em existente |
| `tests/` | 78 testes (segurança, financeiro, precisão, banco, import) | `pytest` verde |

## Auth e isolamento

JWT próprio (access 30min / refresh 7d / reset 15min uso-único jti).
`auth-store.sessionStorage` guarda o token; backend revalida a cada callback.
`store-user-id` é espelho legado (não-autoridade). RLS do Supabase reservado
para futuro PostgREST direto (ver `supabase/migrations/0002_rls.sql`).

## O que NÃO existe (não assumir)

Next.js, NestJS, Prisma, REST, `apps/web`, `services/ai`, `infrastructure`,
`packages/ui` (esqueletos vazios); página de contas agendadas (service sem UI);
Supabase Auth; realtime; CI.

## Preparação PostgreSQL

Models `Numeric/native_enum=False/ondelete/constraints/índices` prontos;
`alembic upgrade head` validado em banco fresco; ETL + cutover pendentes
(ver `docs/migrations/SUPABASE_MIGRATION.md`).

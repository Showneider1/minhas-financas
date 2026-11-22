# Finance OS — Agent Team

## ⚠️ Stack atual (autoridade)

O código em produção é um **monólito Python**:

- **UI:** Dash 2.18 + Dash Bootstrap Components + Plotly (`app.py`, `myindex.py`, `pages/`, `callbacks/`)
- **Domínio:** `services/*` com `Decimal` (ADR-002), `utils/money.py`
- **Persistência:** SQLAlchemy 2.0 síncrono + SQLite em dev (`data/finance.db`), Alembic com head `b7e9c1a4d2f0`
- **Server:** Gunicorn `wsgi:server` + Caddy (Dockerfile / docker-compose.yml)
- **Auth:** JWT próprio (access/refresh/reset), bcrypt, `resolve_user()` anti-IDOR
- **Testes:** pytest, `sqlite:///:memory:` forçado no `tests/conftest.py`

**Fonte de verdade:** `docs/architecture/CURRENT_ARCHITECTURE.md` + ADRs.
Para onboarding, comece pelo `README.md`.

## Stack proposta — NÃO implementada

Next.js/React, NestJS/TypeScript, Prisma, Postgres/Supabase, double-entry ledger e IA (FastAPI/LLM) existem **apenas como proposta** em `docs/architecture/ARCHITECTURE.md`, `docs/product/PRD.md` e esqueletos congelados (`apps/web/`, `packages/*`, `services/api/`, `infrastructure/`). A ADR-001 registra a decisão de manter SQLAlchemy. **Não implemente nesses diretórios sem decisão formal.**

## Core Management
- **Orchestrator**: coordenação, decomposição de tarefas e gates de validação.
- **Product Manager**: backlog, PRD e critérios de aceite.
- **Software Architect**: desenho e integridade estrutural.
- **Fintech Domain Expert**: regras financeiras, contabilidade e investimentos — **autoridade máxima em matéria financeira**.

## Engineering Team (escopo real)
- **UX/UI Designer**: design system e componentes Dash Bootstrap.
- **Frontend Engineer**: `pages/`, `components/`, `callbacks/` (Dash/Python).
- **Backend Engineer**: `services/`, `schemas/`, `middleware/` (Python).
- **Database Engineer**: `database/`, `alembic/versions/`, `supabase/migrations/`.
- **Data Engineer**: `services/import_service.py`, normalização OFX/CSV.
- **Integration Engineer**: `services/market_data_service.py`, `services/email_service.py`.
- **AI Engineer**: módulo de IA — **ainda não iniciado**.

## Quality & Security
- **Security Engineer**, **Privacy Compliance** (LGPD), **QA Engineer**,
  **DevOps Engineer**, **Performance Engineer**, **Code Reviewer**,
  **Documentation Engineer**.

## Collaboration Flow
1. **PM** define requisitos → **Architect** desenha → **Domain Expert** valida a lógica financeira.
2. **UX/UI** desenha → **Frontend** implementa em Dash → **Backend** fornece services.
3. **Security** e **Architect** revisam → implementação → **Code Reviewer** aprova.
4. **QA** valida os critérios (suíte financeira + callbacks).
5. **Orchestrator** gerencia o fluxo, aplica gates entre fases e reporta progresso.

## Invariantes financeiras (verificação obrigatória)
Decimal em valores monetários; saldo com escritor único (`BalanceService`); transferência nunca como receita+despesa; idempotência em importações/pagamentos; estorno por `CANCELLED` (sem compensatório); histórico preservado; estados `PENDING`/`PAID`/`CANCELLED` distintos; testes de falha/retry/reprocessamento.

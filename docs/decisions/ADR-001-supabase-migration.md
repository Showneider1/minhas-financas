# ADR-001 — Migração do banco para Supabase (Postgres gerenciado)

**Status:** Proposto (aguardando correção P0 + credenciais)
**Data:** 2026-09-27
**Contexto:** `docs/audits/CODE_AUDIT.md` §§1-2,6.

## Contexto

- Banco atual: **SQLite** (`data/finance.db`, ~120 KB, ~30 linhas úteis: 1 user, 4 accounts, 11 categories, 12 transactions). ORM: **SQLAlchemy 2.0.36 síncrono**. Migrations: **nenhuma** (só `create_all` + scripts ad-hoc, um deles com conflito Git).
- `docker-compose.yml` oferece Postgres 15 local, mas nada aponta para ele por padrão.
- `docs/architecture/ARCHITECTURE.md` propõe NestJS+Prisma, mas o código real é Dash+SQLAlchemy — a decisão deve seguir o **código real**, não o doc divergente.

## Decisão

1. **Destino: Supabase Postgres** (Postgres padrão, pooler 6543, `sslmode=require`).
2. **Manter SQLAlchemy síncrono + `psycopg2-binary`** como dono do schema e das transações. **Não** reescrever para `supabase-py` / Prisma / async nesta fase.
   - Justificativa: 100% dos models/repos/services/testes são SQLAlchemy sync; `supabase-py` (PostgREST) não dá transação multi-tabela, controle de `Numeric`, nem reaproveita o código; Prisma/NestJS são esqueletos mortos (`apps/web` vazio, `services/api` órfão). Trocar = rewrite sem ganho.
   - `supabase-py` fica reservado para uso futuro **opcional** (Auth/Storage/Realtime), nunca como substituto do ORM transacional.
3. **Autenticação: manter JWT+bcrypt próprios.** Não migrar automaticamente para Supabase Auth.
   - Justificativa: todo o fluxo (hash, login, callbacks, stores) é JWT próprio (`config/security.py`, `services/auth_services.py`); Supabase Auth exigiria vínculo `auth.users.id ↔ public.users.id`, reescrita dos callbacks e rotação de sessão. Custo alto, benefício incerto para app monólito Dash mesma-origem. Reavaliar apenas se houver necessidade de OAuth/SSO ou PostgREST direto.
   - Se um dia adotar Supabase Auth: `public.users.id` = `auth.uid()` (UUID) ou tabela ponte `auth_user_id UNIQUE`; RLS `user_id = auth.uid()`; migração de senhas impossível (bcrypt → redefinir senha).
4. **Alembic passa a ser obrigatório** a partir de agora. Proibir `create_all`/`ALTER` manual em prod; `release: alembic upgrade head`.
5. **Pré-requisitos bloqueantes (P0) antes de apontar para o remoto:** unificar `amount` vs `base_amount`, migrar `Float→Numeric`, importar todos models em `init_db()`, mascarar `DATABASE_URL` nos logs, corrigir isolamento por usuário. Sem isso, a migração herda corrupção/vazamento.

## Alternativas consideradas

| Alternativa | Veredito |
|---|---|
| Reescrever tudo em Prisma/NestJS+Next.js (doc atual) | Rejeitado: joga fora 95% do código funcional sem justificativa; viola “não recrie do zero”. |
| Trocar ORM por `supabase-py` direto | Rejeitado para dados transacionais (sem transações, sem Numeric controlado). Aceitável só como cliente auxiliar. |
| Manter SQLite para sempre | Rejeitado: sem concorrência, sem PITR, sem RLS, sem acesso remoto. SQLite fica só para `pytest :memory:`. |
| Postgres self-hosted (compose) | Válido como staging local, mas Supabase dá PITR, dashboard, RLS e pooler sem operar servidor. |

## Consequências

- Positivas: PITR/backup gerenciado, Postgres real (tipos, constraints, índices), caminho para RLS, pooler para Gunicorn multi-worker.
- Negativas: exige normalização do schema primeiro; latência de rede vs SQLite (mitigar com pool + `pool_pre_ping`); segredos passam a existir (exige `.env.example`, vault, nunca commitar).
- Riscos: drift `amount/status/is_deleted` quebra na primeira escrita se migrar sem P0; `Enum` nativo trava `ALTER` (usar `native_enum=False`).

## Conformidade com a missão

- Sem `service_role` no frontend; sem `RLS OFF` para contornar erro; sem migration destrutiva no remoto sem aprovação; sem excluir SQLite antes da conciliação; sem inventar credenciais nem declarar conexão remota validada sem teste real.

# Relatório Final — Missão 2 P0: Recuperação do Core Financeiro (2026-09-27)

## 1. Problemas encontrados (partida: auditoria + baseline)

Baseline pré-correção: `pytest` 16 failed/0 passed; flake8 728 (escopo config+database+services);
SQLite com 8 tabelas (`goals`/`scheduled_bills` sem tabela); sem Alembic; sem `.env.example`;
`migrate_add_import_columns.py` com conflito Git; `Transaction.amount` fantasma em 10+ pontos;
parcelamento multiplicador; tudo `Float`; TRANSFER ignorada; 3 saldos divergentes; IDOR via
`store-user-id`; reset-token virava access-token; segredos default; callbacks órfãos/duplicados;
importação com SQL para coluna inexistente; `get_accounts_by_user`/`create_category`/
`delete_category`/`delete_transaction` inexistentes chamados em produção.

## 2. Problemas corrigidos

- **F2 contrato:** `base_amount` único (alias `amount` removido de repos/services/callbacks/relatórios); `TransactionUpdate` no update; `purchase_date` preservado.
- **F3 Decimal:** 14 colunas `Float→Numeric`; `utils/money.py` (rejeita float/bool, quantize na borda); schemas `Decimal`; parse BR estrito; importação via `FinanceService`; `auto_categorize` com `text()`; fallback nunca-None.
- **F4 parcelas:** `split_money` resto-nas-primeiras (100/3=[33.34,33.33,33.33]); guards base-paga/duplo-clique/TRANSFER.
- **F5 transfers:** `TransferService` (1 linha, débito+crédito, patrimônio intacto, fora de KPIs, idempotente com chave + race, divergência rejeitada, auditável).
- **F6 saldos:** `BalanceService` regra única; `Account.balance` só via `recalculate_and_persist`; dev DB reconciliado; `get_dashboard_summary` delegado.
- **F7 IDOR:** `resolve_user` (JWT-only + mismatch) em TODOS os callbacks de dados + roteamento; `get_owned/update_owned/delete_owned`; posse de conta/categoria em bills/goals/transfers/import; categoria-tipo validada; escritor único de save; `salvar_edicao` duplicado removido; `ALL` real no pattern-matching; `delete_account`/`delete_conta` com dono (soft-delete, checa origem E destino).
- **F8 tokens:** reset com `jti` persistido, 15 min, `verify`/`consume` separados, reuso negado; `verify_refresh_token`; matriz cross-type negada nos 6 sentidos.
- **F9 segredos:** `DEBUG=False` default; fail-fast prod; `create_db` travado (só SQLite não-prod, hash bcrypt, sem fallback, sem print de senha); compose sem hardcoded + healthcheck + redis comentado; `.env.example` só nomes.
- **F10 banco:** backup `data/finance.db.pre-p0-*`; 11 tabelas; colunas de transferência aditivas (+1 correção de FK `scheduled_bill→scheduled_bills`); `integrity_check=ok`; 12 tx + 1 user preservados.
- **F11 Alembic:** `alembic.ini` + `env.py` + baseline `916651f2e591` (10 tabelas, Numeric, `native_enum=False`, ondelete, Unique/Check, 34 índices); `upgrade` validado em fresco; `stamp` em cópia e no dev (sem DDL).
- **F12 testes:** 16 legados reescritos à API real (soft-delete documentado; `BillType` real); + cobertura segurança/financeiro/precisão/banco/import.
- **F13–F15:** revisão fintech + code-review independentes executados; 2 bloqueadores reais achados e corrigidos (`store-user-id` residual em goals, `"__all__"` literal, crash `health_score`, IDOR em bills/goals, CANCELLED, `health_score`); F/E9 zerados.

## 3. Arquivos modificados (54 via git: 2291+/1501-)

Models (7 + `password_reset_token.py` novo), repos (3), services (13 + `balance_service.py`/`transfer_service.py` novos),
`middleware/auth_context.py` (novo) + `audit_log`/`error_handler`, `config/settings|security`,
`create_db.py`, `database/connection.py`, 11 callbacks, `myindex.py`, 4 schemas, `utils/money.py` + formatters/date_helpers,
`docker-compose.yml`, `alembic*`, 9 arquivos de teste, 6 docs.

## 4–5. Testes executados e resultado

`pytest tests/`: **78 passed, 0 failed** (era 16 failed/0 passed). Composição: goals 10, bills 8,
money 10, balance 5, transfer 9, tokens 4, contract 6, installments 9, isolation 4, auth 5,
bank 6, import 2. Wiring: `import myindex, callbacks` OK. F/E9 flake8: **0** (era 57).

## 6. Lint antes/depois (honesto)

- Escopo baseline (config+database+services): **728 → 712**. F/E9/E7/W6: **→ 2 residuais** (`==True` idiomático SQLAlchemy em scheduler + E722 corrigidos em formatters).
- Escopo amplo: F/E9 **57 → 0**. Restante ≈ E501 (sem teto configurado; reformatar 600 linhas seria churn — P3: ruff/black linha 100).

## 7–8. Questões financeiras e de segurança corrigidas

Ver §§2 e `docs/audits/FINANCIAL_VALIDATION.md` (16 temas: 11 ✅, 5 ⚠️ P1). Segurança: IDOR,
tokens, segredos, PII/logs, `str(e)` em UI, rate (documentado P1: chave IP+email).

## 9–10. Arquitetura e Supabase

`docs/architecture/CURRENT_ARCHITECTURE.md` (monólito Dash real) + `ADR-002`.
Supabase: tipos/constraints/índices/baseline/RLS prontos; **remoto não configurado, não validado**
(sem credenciais, nada inventado); ETL + cutover pendem de aprovação.

## 11–13. Pendências, riscos e próximo passo

**Pendências humanas:** credenciais Supabase; ETL + conciliação assinada; aprovação cutover;
`git add/commit` (não commitado — sem aprovação).
**Riscos:** recorrência fuzzy; multi-moeda; investimentos P1; `/relatorios` morta (P3);
`export_service` sem engine (P3); E501.
**Próximo passo recomendado:** (1) credenciais → staging Postgres (`upgrade head` + ETL em cópia);
(2) P1 investimentos/recorrência/enums únicos/rate-IP; (3) P3 frontend (modal único, relatórios, 1 CSS).

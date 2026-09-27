# Finance OS — Auditoria de Código (CODE_AUDIT)

> **ADENDO P0 (2026-09-27, Missão 2):** os itens C1, C3, C4, C5, C8-reset,
> C7-parcial, A1-parcial, A2-aceito, A7, C2 e A8 foram corrigidos; detalhes em
> `docs/audits/SESSION_REPORT_2026-09-27_P0.md`, `docs/decisions/ADR-002-financial-core.md`
> e `docs/architecture/CURRENT_ARCHITECTURE.md`. O corpo abaixo preserva o
> diagnóstico original (baseline pré-correção) como registro histórico.

**Data:** 2026-09-27 (UTC)
**Escopo:** inspeção real do repositório em `/mnt/c/Users/rapha/Documents/Scripts Python/Minhas_Financas`, respeitando `.gitignore` (`.env` **não lido**, segredos não expostos).
**Método:** leitura direta de arquivos + 5 frentes especializadas (arquitetura, database, segurança, fintech/QA, frontend) + baseline executado localmente.
**Premissa respeitada:** não assumir que `docs/architecture/ARCHITECTURE.md` corresponde ao código. Ela **não corresponde** (ver §1).

## Baseline registrado ANTES de qualquer modificação

| Verificação | Resultado |
|---|---|
| `venv/Scripts/python.exe -m pytest tests/ -q` | **16 failed, 0 passed** — suíte 100% quebrada (todos os testes chamam API inexistente: `GoalService.create_goal(db=...)`, `BillType.EXPENSE`, `get_pending_bills`, etc.). Detalhe: `tests/test_goal_service.py:11`, `tests/test_scheduled_bill_service.py:11`. |
| `flake8 config/ database/ services/` | **728 problemas** (E501, E221, E712 dominantes; exemplo `services/scheduler_service.py:119,145,150`). Sem config `pyproject/setup.cfg`. |
| `black --check` / `mypy` | Não configurados; sem CI (`.github/` vazio). |
| Banco real | `data/finance.db` (SQLite). Tabelas existentes: `users, accounts, categories, assets, transactions, budgets, investment_operations, login_attempts`. **Ausentes:** `goals, scheduled_bills` (models existem, tabela não). |
| `alembic` | Declarado (`requirements.txt:11`) mas **sem `alembic.ini`, sem `migrations/`**. Schema evolui via `create_all` + scripts ad-hoc. |
| `.env.example` | **Não existe**. `.env` existe localmente mas não foi lido (correto). |
| `scripts/migrate_add_import_columns.py` | **Sintaxe inválida** — marcadores de conflito Git (`<<<<<<< HEAD` em `:25`, `:37`, etc.). |

---

## 1. Diagnóstico da arquitetura (real vs. documentada)

**Arquitetura real: monólito Dash + SQLAlchemy síncrono, sem API HTTP.**

- Entry: `app.py:22-33` cria `app/server`; `myindex.py:23-54` define layout/stores; `Procfile.txt:1` → `gunicorn myindex:server`.
- Fluxo: `config/ → database/models+repositories → services/* → callbacks/* → pages/* + components/*`. Callbacks Dash abrem `get_db_session()` inline e chamam Services/Repos direto. **Não há REST.**
- `docs/architecture/ARCHITECTURE.md:6-8,13-26` descreve `Next.js → NestJS → PostgreSQL + Prisma, FastAPI AI, double-entry ledger Decimal(19,4)`. **Nada disso executa.** `apps/web/` vazio, `infrastructure/` vazio, `packages/ui/` vazio, `services/ai/` vazio, `services/api/src/` contém apenas esqueletos NestJS/Prisma órfãos (`transactions.controller.ts:1-39`). `package.json:4-13` (`turbo`, workspaces) é fantasma — o Python é ~95% do repo.
- Duplo entrypoint: `python app.py` sobe app sem layout (inútil); `python myindex.py` é o real. Sob Gunicorn, `initialize_application()` **nunca executa** (`app.py:79-82` só em `__main__`), então tabelas/seed não são criados em prod.
- Estado: apenas `dcc.Store` no browser (`myindex.py:28-43` + stores por página). Sem React Query/Zustand.
- `docker-compose.yml:4-20` oferece `postgres:15 + redis:7`, mas `config/settings.py:41` default é `sqlite:///./data/finance.db`; `redis` não é importado em nenhum lugar.

---

## 2. Problemas identificados

### 🔴 CRÍTICOS (impedem execução / corrompem dados / vazam dados)

#### C1 — `Transaction.amount` não existe no model, mas tudo o usa
- **Evidências:** model só tem `base_amount:Float` (`database/models/transaction.py:32-34`). Usos fantasmas: `database/repositories/transaction_repo.py:44,52-56,158,160,231,275`, `services/report_service.py:93,210-211,228`, `database/repositories/account_repo.py:133,141`. `scripts/update_dabase.py:60-63` tenta `UPDATE transactions SET amount=base_amount`.
- **Impacto:** extrato, relatório mensal/anual/custom, `sum_by_type`, `recalculate_balance` levantam `AttributeError/OperationalError`. Caminho feliz quebrado.
- **Solução:** decidir fonte única (adicionar migração `amount+interest+discount+cashback` OU trocar tudo para `base_amount`). Congelar `ReportService` até o fix.

#### C2 — Chamadas a métodos inexistentes + callbacks duplicados competindo
- **Evidências:** `callbacks/dashboard_callbacks.py:374` → `svc.delete_transaction(...)` inexistente em `services/dashboard_service.py:16-331`; `callbacks/extrato_callbacks.py:469` → `FinanceService(db).delete_transaction` inexistente em `services/finance_service.py:12-146`. Três donos de `store-reload-dashboard` (`transactions_callbacks.py:169` sem `allow_duplicate`, `dashboard_callbacks.py:383` e `extrato_callbacks.py:339` com). `salvar_edicao` (`extrato_callbacks.py:337-425`) lê IDs que não existem (`select-tipo`, `input-data-competencia`); IDs reais em `components/sidebar.py:144-237`.
- **Impacto:** exclusão via dashboard/extrato = `AttributeError` + `str(e)` exposto na UI. Edição silenciosamente falha. `DuplicateCallbackOutput` / loop de reload.
- **Solução:** criar `TransactionService.delete(id,user_id)` único com checagem `user_id` + audit; manter só `transactions_callbacks.salvar_transacao` como escritor; alinhar IDs ao `sidebar.py`.

#### C3 — Bypass de autorização / IDOR via `store-user-id`
- **Evidências:** `myindex.py:68` só checa existência de `auth_data`, sem `verify_token`. `middleware/auth_middleware.py:43-53` sempre retorna `None`; `require_auth/check_auth` nunca usados. Todos os dados confiam em `State("store-user-id","data")` (`dashboard_callbacks.py:53`, `transactions_callbacks.py:188`, `extrato_callbacks.py:126`, `export_callbacks.py:23`) sem validar JWT.
- **Impacto:** editar `sessionStorage` no DevTools permite ver/alterar dados de qualquer `user_id`. Vazamento horizontal total (LGPD).
- **Solução:** derivar `user_id = verify_token(auth-store.token)` em todo callback; rejeitar mismatch/expirado; remover `store-user-id` como autoridade.

#### C4 — Parcelamento multiplica valor em vez de ratear
- **Evidências:** `services/recurrence_service.py:83-86` copia `base_amount` integral para cada parcela (`total` lançamentos de valor cheio).
- **Impacto:** compra R$1.200 em 6x vira R$7.200. Corrompe saldo, evolução patrimonial, orçamento.
- **Solução:** `base_amount/total` com ajuste de centavos na última parcela + `Decimal`.

#### C5 — Todo dinheiro é `Float`, nenhum `Decimal/Numeric`
- **Evidências:** ~20 ocorrências (`transaction.py:34`, `account.py:29-30,32`, `budget.py:15`, `goal.py:53-55`, `investment.py:74-77`, `scheduled_bill.py:54-55`). `grep Numeric` = 0. `utils/formatters.py:44,85,154` formata erro binário.
- **Impacto:** `0.1+0.2`, rateio, preço médio, IRPF divergem. Migração Supabase **exige** `Numeric(12,2)` / `Numeric(14,4)`.
- **Solução:** migrar colunas monetárias para `Numeric` + `Decimal` nos services/schemas (uma migration de quebra, antes do Supabase).

#### C6 — `TRANSFER` existe no enum mas é ignorada; 3 saldos divergentes
- **Evidências:** `TRANSFER` definido (`category.py:13`, `transaction_schema.py:26`), zero `if TRANSFER` em `services/`. `finance_service.py:116,121,128,133` só soma `INCOME/EXPENSE`. Três leituras de saldo divergem: `dashboard_service.py:40-58` (`sum(base_amount)` paid), `:65-67` (`sum(Account.balance)`), `account_repo.py:133-149` (`sum(Transaction.amount)` quebrado). `FinanceService.create` não toca `Account.balance`; `mark_as_paid` não atualiza conta nem `status`.
- **Impacto:** transferência some ou duplica; “saldo em contas” ≠ “receitas−despesas” ≠ “initial+in−out”. Auditoria impossível.
- **Solução:** especificar transferência como lançamento duplo ou documentar como não-suportada; eleger **uma** fonte de saldo; unificar “pago = `status==PAID`” (ou `paid_date`, não ambos).

#### C7 — Segredos default + `DEBUG=True` + hash demo incompatível
- **Evidências:** `config/settings.py:34,46-47` (`DEBUG=True`, `SECRET_KEY/JWT...="dev-...-change-in-production"`). `docker-compose.yml:8-9` (`password`). `create_db.py:15,50` usa `werkzeug.generate_password_hash` vs runtime `bcrypt.checkpw` (`config/security.py:29-34`) → seed nunca autentica; fallback `Demo@2024!` printado (`create_db.py:43,99-100`).
- **Impacto:** JWT forjável; debugger/RCE; login demo quebrado.
- **Solução:** fail-fast em prod (abortar se segredo default ou `DEBUG`), `DEBUG=False` default, usar `hash_password()` no seed, nunca printar senha.

#### C8 — `password_reset_token` vira `access_token` + suíte 100% quebrada
- **Evidências:** `config/security.py:94-98` monta `type=password_reset` e chama `create_access_token()` que sobrescreve para `type=access` (`:48-52`); `verify_password_reset_token:106` nunca passa. Testes: 16/16 falham (`test_goal_service.py:11`, `test_scheduled_bill_service.py:11` — API inexistente).
- **Impacto:** se reset ativado (`settings.py:71`), token de reset é sessão válida. Zero cobertura real de cálculos críticos.
- **Solução:** função dedicada de reset (`exp=15min`, `jti` single-use); reescrever `tests/` para a API instanciada atual.

### 🟠 ALTOS

| ID | Problema | Evidências | Impacto / Solução |
|---|---|---|---|
| A1 | `init_db()` não importa `goal/scheduled_bill/investment/LoginAttempt`; Gunicorn nunca roda init | `database/connection.py:63-67`, `app.py:79-82`, `Procfile.txt:1` | `goals`/`scheduled_bills` sem tabela física. **Solução (segura, aditiva):** importar todos os models em `init_db()`; criar entrypoint que chame init antes do Gunicorn. |
| A2 | `get_db_session()` dá `commit()` até em leitura; double-commit nos services | `database/connection.py:28-44`, `services/finance_service.py:42-43,87-88` | Side-effects em leitura. **Solução:** commit explícito nos services; context só `rollback/close`. |
| A3 | Workspaces Turbo/NestJS fantasmas | `apps/web` vazio, `infrastructure/` vazio, `packages/ui` vazio, `services/ai` vazio | `npm run build` engana; dev implementa ledger double-entry que nunca executa. **Solução:** deletar ou mover para `legacy/` + documentar “proposta futura”. |
| A4 | Acoplamento global `from app import app` (13 pontos) + `DATABASE_URL` logada com senha | `callbacks/*.py`, `components/extratos.py:6`, `database/connection.py:15` | Import circular; segredo em `logs/`. **Solução (segura):** mascarar URL no log; factory `create_app()` / `register_callbacks(app)` no médio prazo. |
| A5 | JWT em `sessionStorage`, logout só client-side, refresh nunca validado | `myindex.py:28-29`, `auth_callbacks.py:53-58,176-184`, `security.py:56-65` | XSS rouba sessão. **Solução:** access curto + refresh rotation + denylist + CSP; considerar cookie `HttpOnly`. |
| A6 | Rate limit só no login por email | `middleware/rate_limiter.py:60-109`, `services/auth_services.py:77` | Bypass rotacionando email; registro sem limite. **Solução:** chave `IP+email`, aplicar a register/reset/import, backoff. |
| A7 | `BaseRepository.get/update/delete` sem `user_id` | `database/repositories/base_repo.py:39-100`, `transaction_repo.py:63-82`, `account_repo.py:96-153` | Qualquer novo uso vira IDOR. **Solução:** `get_owned(id,user_id)` obrigatório para entidades owned + teste SAST. |
| A8 | 4 definições de “total do mês” divergentes | `finance_service.py:91-146`, `dashboard_service.py:20-92`, `transaction_repo.py:222-286`, `report_service.py:61-131` | Dashboard ≠ Extrato ≠ Relatório. **Solução:** eleger `DashboardService` como única agregação. |
| A9 | Investimentos: oversell mascarado, taxas fora do PM, SPLIT frágil, sem valor de mercado | `services/investment_service.py:279-344,121-135,241-242` | PM errado, IRPF errado, gráfico engana. **Solução:** levantar em oversell, incorporar fees ao PM, validar SPLIT, separar custo histórico vs mercado. |
| A10 | `ScheduledBill` não gera `Transaction`; `Scheduler` morto (`hasattr` silencia) | `scheduled_bill_service.py:132-171,247-290`, `scheduler_service.py:66-68`, `recurrence_service.py:226` | Fluxo de caixa errado; job 00:10 nunca gera. **Solução:** gerar `Transaction` ao pagar bill; corrigir nome do método; cobrir `receivable overdue`. |
| A11 | Frontend: 4 modais com mesmos IDs; callbacks para IDs inexistentes (silenciados por `suppress_callback_exceptions`); página `/relatorios` morta; código morto `components/dashboard.py`, `extratos.py` | `components/sidebar.py:129`, `transaction_modal.py:107`, `shared/modals.py:6`, `app.py:25`, `dashboard_callbacks.py:330-365`, `extrato_callbacks.py:312,349-358`, `export_callbacks.py:22-27`, `relatorios_page.py:54+` | Criação/edição/export quebram sem erro visível. **Solução:** modal único + `config/ids.py`; remover `suppress` em dev; religar ou remover rotas órfãs. |
| A12 | N+queries no dashboard (~25 por troca de data); paginação em Python (`page_size=1000` em memória) | `dashboard_callbacks.py:53-91,99-301`, `dashboard_service.py:102-130`, `transaction_repo.py:196-216`, `extrato_callbacks.py:141-181` | Lentidão. **Solução:** consolidar KPIs/charts em 1 callback/transação; `LIMIT/OFFSET` SQL. |
| A13 | Sem `ondelete` em 90% FKs; enums nativos travam Postgres; tz inconsistente; `docker-compose` sem healthcheck/backup | Ver §database | Quebra migração. **Solução:** ver plano Supabase (§6). |

### 🟡 MÉDIOS

- M1 — Erros expostos (`str(e)`, `traceback.print_exc`) + PII em logs (`auth_callbacks.py:89-92,162-164`, `extrato_callbacks.py:249,473`, `audit_log.py:43`). **Solução:** códigos genéricos na UI; `handle_error()` em todos callbacks; redigir email.
- M2 — XSS armazenado potencial (`sanitize_string` nunca chamada; `import_service.py:154`; render `extrato_callbacks.py:202-222`). **Solução:** sanitizar + CSP.
- M3 — Registro aberto sem verificação/CAPTCHA (`settings.py:69-70`; `is_verified` nunca checado). **Solução:** CAPTCHA/throttle ou ativar verificação.
- M4 — `requirements.txt` duplicado (`dash` `:4` vs `:16`, `SQLAlchemy/alembic` `:10-11` vs `:21-22`); `xlsxwriter` usado mas só `openpyxl` instalado (`export_service.py:46` → `ImportError`); `redis` no compose sem uso; `CACHE_KEYS` mortos.
- M5 — Responsividade quebrada (sidebar `fixed 240px` vs `marginLeft 280px` em `myindex.py:114`; sem toggler mobile; `custom.css` vs `styles.css` conflitantes); a11y ausente (emoji como único significado, labels sem `html_for`, status só por cor).
- M6 — `Base.metadata.create_all` ingênuo; `create_db.reset_and_seed_db()` destrutivo sem trava (`create_db.py:23-32`); `mixins.py` morto; `Category.icon String(10)` estoura emoji; falta unicidade (`ticker,user`), `CheckConstraint(month 1-12)`.

### 🔵 BAIXOS

- `declarative_base` depreciado (`database/base.py:4`); `lazy="dynamic"` legado (`account.py:43`); `backref` vs `back_populates`; `datetime.utcnow` naive remanescente (`budget.py:21`, `schemas/common.py:26`); `bcrypt.gensalt()` sem rounds fixos; JWT sem `iss/aud`; `locale.setlocale` global em import; `print` em vez de `app_logger` nos callbacks.

---

## 3. Dependências entre correções (ordem obrigatória)

1. **Congelar schema primeiro:** C1 (amount) + C5 (Numeric) + unificar “pago” + `ondelete`/enums/tz — **antes** de qualquer migração. Migrar com drift = incidente.
2. **Depois auth/isolamento:** C3 + A5/A6/A7 + testes de isolamento (usuário A × B) — antes de expor qualquer dado no Supabase.
3. **Depois cálculos:** C4 + C6 + A9/A10 — antes de conciliar saldos.
4. **Depois arquitetura:** A1/A2 (init/commit) → A8 (agregação única) → A11/A12 (frontend) → A3 (remover fantasmas).
5. **Por último:** médios/baixos (logs, XSS, compose, CSS, lint).

## 4. Prioridades de implementação

| Prioridade | Itens | Critério |
|---|---|---|
| P0 — antes da migração | C1, C5, C3, A1, A2 | Sem isso, Supabase herda corrupção/vazamento |
| P1 — conciliação | C4, C6, A8, A9, A10, C8-testes | Saldos e relatórios precisam bater |
| P2 — hardening | C7, A5, A6, A7, M1-M3 | Auth, rate, logs, registro |
| P3 — escala/UX | A11, A12, M4-M6, baixos | Performance, frontend, higiene |

## 5. Backlog técnico inicial (Issues sugeridas)

1. `[P0] Unificar `amount` vs `base_amount` (migration Alembic + repos + reports).`
2. `[P0] Migrar dinheiro Float→Numeric/Decimal.`
3. `[P0] Isolamento por usuário: `verify_token` em todo callback + `get_owned` + testes A×B.`
4. `[P0] `init_db()` importar todos models + entrypoint Gunicorn + travar `drop_all` em prod.`
5. `[P0] `get_db_session` sem commit implícito.`
6. `[P1] Rateio de parcelas + transferência duplo-lançamento + fonte única de saldo.`
7. `[P1] Reescrever `tests/` para API real + `pyproject` com `cov-fail-under=80` + CI mínimo.`
8. `[P2] Reset token dedicado + refresh rotation + logout server-side.`
9. `[P2] Mascarar `DATABASE_URL`/PII nos logs; `handle_error` global.`
10. `[P3] Modal único, IDs únicos, religar relatórios/export, paginação SQL, 1 CSS, Offcanvas mobile.`

---

## 6. Nota sobre Supabase (resumo — detalhe em `docs/migrations/SUPABASE_MIGRATION.md`)

- **Decisão:** manter **SQLAlchemy síncrono** (todo o código é sync 2.0; `psycopg2-binary` já instalado; Supabase Postgres é Postgres padrão). **Não** reescrever para `supabase-py` nos dados transacionais; `supabase-py` só se precisar de Auth/Storage/Realtime depois. **Não** migrar para Prisma/NestJS (fantasma).
- **Pré-requisitos bloqueantes:** corrigir C1/C5/A1 (schema) e C3 (isolamento) antes de apontar para o remoto. Sem credenciais configuradas, **não validar** conexão remota — preparar integração, `.env.example` e RLS, sem inventar credenciais.
- **RLS:** com acesso via SQLAlchemy (role servidor), RLS no backend só atrapalha; habilitar RLS **com políticas por `auth.uid()`** apenas se expor PostgREST direto. De todo modo, criar políticas `user_id = auth.uid()` como defesa em profundidade + testes A×B.
- **Nunca:** expor `service_role` no frontend; desativar RLS para “corrigir” permissão; aplicar migration destrutiva no remoto sem aprovação; excluir o SQLite antes da conciliação.

## 7. Riscos remanescentes (pós-auditoria, pré-correção)

- Qualquer deploy atual em Postgres vazio retorna 500 (init nunca roda no Gunicorn).
- `create_db.reset_and_seed_db()` pode apagar tudo se executado em prod.
- Transferências/parcelas/investimentos calculados errados — não usar números atuais para decisão fiscal.
- Sessão forjável via DevTools — tratar como ambiente single-user local até C3 ser corrigido.

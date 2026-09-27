# ADR-002 — Núcleo Financeiro Canônico (P0, Missão 2)

**Status:** Implementado (2026-09-27). Testes: suíte pytest verde.
**Contexto:** `docs/audits/CODE_AUDIT.md` C1/C4/C5/C6, revisões fintech e code-review P0.

## 1. Representação monetária

- **Regra:** todo valor monetário é `Decimal` em Python e `NUMERIC` no banco —
  `Numeric(12,2)` para dinheiro, `Numeric(14,4)` para quantidades/preços.
  `float` é proibido em caminho financeiro (`utils/money.py::_coerce` levanta
  `TypeError`; testes `tests/test_money.py` travam regressão).
- **Camada central:** `utils/money.py` — `to_money2/to_qty4` (quantize só na
  borda, `ROUND_HALF_UP`), `split_money` (rateio exato), `money_sum`, `avg_price`.
- **Decisão C1:** `Transaction.base_amount` é o ÚNICO valor do lançamento.
  `amount/interest/discount/cashback` nunca existiram no model e foram
  removidos de repos/services/callbacks (sem alias `getattr or`).
- **Fronteira UI:** formulários digitam string BR ("1.234,56") → `Decimal` no
  callback; gráficos Plotly/JSON recebem `float()` só na borda (Decimal não
  serializa); `Decimal→float` nunca ocorre em cálculo.
- **Pendente (P1):** unificar os enums duplicados `TransactionType/Status`
  (schema × model) — hoje normalizados na fronteira dos services
  (`FinanceService._coerce_type`, `TransactionRepository.filter_transactions`).

## 2. Cálculo de saldo (regra única)

```
saldo_conta(A) = initial_balance(A)
    + Σ base_amount (INCOME,  pago, account=A)
    − Σ base_amount (EXPENSE, pago, account=A)
    + Σ base_amount (TRANSFER pago, destination=A)
    − Σ base_amount (TRANSFER pago, account=A)
pago ≡ status == PAID AND paid_date IS NOT NULL
patrimônio = Σ saldos das contas ativas (moeda única BRL no P0)
```

- **Fonte:** `services/balance_service.py` (único lugar com a fórmula).
  `Account.balance` é CACHE persistido só por `recalculate_and_persist()`.
- `DashboardService`, `FinanceService.get_dashboard_summary` (delegado),
  `ReportService` e repos consomem o BalanceService — as 4 definições
  divergentes foram eliminadas (previsto = realizado + pendente do mês).
- `reconcile()` detecta divergência calculado × persistido (usado no cutover).

## 3. Transferências

- UMA linha `TRANSFER` (`account_id` origem + `destination_account_id` destino
  + `transfer_group_id` vínculo + `client_transfer_id` idempotência).
- Somente `TransferService`: valida posse/atividade das contas, categoria
  TRANSFER do dono, valor > 0, origem ≠ destino; retry idêntico retorna a
  linha; chave reutilizada com parâmetros divergentes levanta erro; race
  resolvida pelo UNIQUE (`IntegrityError` → retorna vencedora).
- Pendente não move saldo; `confirm_transfer` efetiva. Excluída de
  receitas/despesas/KPIs/orçamento em todos os somatórios.
- `FinanceService` rejeita TRANSFER direto (orienta ao TransferService).

## 4. Parcelamento

- `split_money(total, n)`: soma exata, resto de centavos nas PRIMEIRAS
  parcelas (100,00/3 → [33,34, 33,33, 33,33]). Base vira parcela 1/N.
- Guards: base `PAID` não parcela; base já parcelada não regenera
  (anti-duplo-clique); TRANSFER não parcela; vencimentos +1 mês.

## 5. Isolamento por usuário

- `user_id` nunca vem do frontend: `middleware/auth_context.resolve_user()`
  deriva do JWT (`auth-store`) e rejeita ausente/expirado/adulterado/mismatch.
- Aplicado em todos os callbacks de dados + roteamento (`myindex` valida JWT).
- Repos: `get_owned/update_owned/delete_owned`; services filtram `user_id`
  (inclui conta/categoria vinculadas em bills, goals, transfers, importação).

## 6. Consequências / limites conhecidos (P1)

- Recorrência com dedup fuzzy e janela de 1 mês; sem `parent_recurrence_id`.
- Multi-moeda sem conversão (BRL único); investimentos fora do patrimônio.
- `get_db_session` mantém commit-on-success (unit-of-work; services dão commit
  explícito) — mudança adiada por risco de regressão em escritas.
- Enums schema×model a unificar; E501/lint de estilo com teto P3 (ruff/black).

# ADR-004 — Motor de Investimentos (P1)

**Status:** Implementado (2026-09-27). Suíte: 107 passed.

## 1. Modelagem

- `Asset` + `InvestmentOperation` existentes, elevados a `NUMERIC(18,8)`
  (quantity/price/fees/total) — cotas fracionárias cripto/fundos até 8 casas.
  Alembic `92ca3cae3903` (batch, cobre FLOAT legado e 14,4 do baseline).
- **Position é DERIVADA** (replay do ledger em `get_position`), sem tabela
  própria — elimina divergência por escrita dupla. `PositionSummary` mantido
  como alias para callers legados.

## 2. Matemática (Decimal nativo; float/bool rejeitados)

- **PM:** `PM = custo / qty`, onde cada BUY soma `qty×price + fees` ao custo.
  Equivalente à fórmula da missão por indução.
- **SELL:** valida `qty ≤ posição` (`InsufficientPositionError`); `PM` intacto;
  custo baixa proporcionalmente; P&L = `qty×(preço − PM) − taxas`.
- **DIVIDEND/INTEREST:** só ganho (`total_amount`); qty/PM intactos.
- **SPLIT f:** `qty ×= f`, custo intacto. Fator via `quantity` da operação.
- Escalas: 8 casas (qty/preço/PM/custo), 2 casas (proventos, P&L, totais).

## 3. Liquidação no caixa (P1 liquidação)

- `investment_operations.transaction_id → transactions.id` (FK NULL, UNIQUE 1:1;
  NULL só para SPLIT). Migration `7da1acfc6143`.
- BUY debita EXPENSE paga de `qty×price + fees`; SELL/DIVIDEND creditam INCOME
  (`qty×price − fees` / valor); categoria auto (`Investimentos`/`Proventos`).
- Uma única unidade de trabalho: operação + transação + `recalculate` no mesmo
  commit; `rollback` total em falha. Compra sem saldo → `InsufficientFundsError`
  sem persistir nada. `void_operation` estorna op + transação e recusa se a
  posição ficaria negativa.
- SPLIT não liquida (`transaction_id` NULL).

## 4. Limites (P2)

Valor de mercado (cotações), IRPF com vendas parciais multi-ano além do
`until(date,id)`, integração conta-corrente no dividendo, UI.

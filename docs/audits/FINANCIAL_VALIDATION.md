# Validação Financeira — pós-P0 (2026-09-27, Missão 2)

**Referência:** ADR-002, `CURRENT_ARCHITECTURE.md`. Suíte: **78 passed, 0 failed** (SQLite `:memory:`).

## Veredito por tema (atualizado)

| Tema | Status | Evidência |
|---|---|---|
| Receitas/despesas | ✅ | `FinanceService` Decimal, status sincronizado, categoria validada; `tests/test_transaction_contract.py` |
| Transferências | ✅ | `TransferService` origem−X/destino+X, patrimônio intacto, fora de KPIs, idempotente, auditável; `tests/test_transfer_service.py` (8) |
| Saldo consolidado | ✅ | Regra única (`BalanceService`); `reconcile()`; dev DB reconciliado (Carteira 8746.45 etc.); `tests/test_balance_service.py` |
| Parcelamentos | ✅ | `split_money` resto-nas-primeiras; guards (base paga, duplo-clique, TRANSFER); 100/3=[33.34,33.33,33.33]; `tests/test_installment_regression.py` (9) |
| Recorrências | ⚠️ | Geração idempotente OK; dedup fuzzy + janela 1 mês = P1 |
| Investimentos (PM/proventos) | ⚠️ | Fora do P0; `avg_price` central existe; oversell/SPLIT/IRPF = P1 |
| Preço médio | ⚠️ | `avg_price` com guard qty>0; ponderado com taxas = P1 |
| Cartões | ⚠️ | Modelo + validações de criação; fatura/limite = P1 |
| Orçamentos | ✅ parcial | Decimal + validações + ownership; atomicidade de cópia = P1 |
| Metas | ✅ | Decimal, ownership de conta, prazo iminente corrigido; 10 testes |
| Contas a pagar/receber | ✅ | Pagar gera Transaction (idempotente), receivable overdue no fluxo; 8 testes |
| Precisão decimal | ✅ | `utils/money.py` + Numeric; float rejeitado; `tests/test_money.py` (10) |
| Idempotência | ✅ | Parcelas, transfers (chave + race), bills (`scheduled_bill_id`), import (`import_hash`) |
| Integridade transacional | ✅ | Commit/rollback explícitos nos writers; `get_db_session` como unit-of-work (documentado) |
| Rastreabilidade | ✅ parcial | bill→transaction, transfer group/client ids; audit sem PII nos novos fluxos |
| Isolamento por usuário | ✅ | `resolve_user` em todos os callbacks + `get_owned` + testes A×B expandidos |

## Divergências conhecidas (P1, não bloqueiam P0)

- Série mensal mistura realizado (passado) + realizado/previsto (mês atual) — documentado por design.
- Multi-moeda sem conversão (BRL único); investimentos fora do patrimônio.
- Recorrência fuzzy; health_score heurístico (borda float explícita).

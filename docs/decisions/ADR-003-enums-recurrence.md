# ADR-003 — Enums Unificados + Motor de Recorrência (P1)

**Status:** Implementado (2026-09-27). Suíte: 95 passed.

## 1. Enums — fonte única

`database/enums.py` concentra os 10 enums (todos `str, Enum`, valores idênticos
aos legados — sem reescrita de dados). Models re-exportam para compatibilidade
(`from database.models.category import TransactionType` continua válido);
`schemas/transaction_schema.py` importa de lá (fim da duplicação que quebrava
`==` entre camadas). SQLAlchemy segue `native_enum=False` (VARCHAR no SQLite e
no Postgres). Coerções temporárias do P0 (`_coerce_type`) removidas.

## 2. Recorrência de contas agendadas

`services/bill_recurrence_service.py`:
- Entrada: `ScheduledBill` com `recurrence != NONE`, não pausada/cancelada/excluída.
- Ocorrências ancoradas no `due_date` (mensal trava fim do mês; semanal +7d).
- **Dia útil:** sábado/domingo → próxima segunda (convenção BR). Feriados fora
  do escopo (sem tabela — P2).
- Gera `Transaction` PENDENTE vinculada por `scheduled_bill_id`; pendente não
  move saldo (consistente com ADR-002).
- **Idempotência exata:** existe lançamento da conta para o vencimento ajustado?
  Re-execução no mês retorna `skipped`, nunca duplica (inclusive quando o ajuste
  empurra o vencimento para o mês seguinte).
- `is_paused` (coluna aditiva + Alembic `d2729976`) pausa sem cancelar.
- Lote com relatório `{generated, skipped, errors}`; `project_period` só prevê.

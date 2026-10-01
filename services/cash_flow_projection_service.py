"""Projeção de fluxo de caixa futuro (Predictive Analytics)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from config.logging_config import app_logger
from database.enums import BillType, TransactionStatus, TransactionType
from database.models.transaction import Transaction
from services.balance_service import BalanceService
from services.bill_recurrence_service import BillRecurrenceService
from utils.money import to_money2

ZERO = Decimal("0.00")


class CashFlowProjectionService:
    """Projeta o saldo diário futuro com base em pendências e recorrências."""

    def __init__(self, db: Session):
        self.db = db

    def get_projected_daily_balance(
        self,
        user_id: int,
        months_ahead: int = 3,
    ) -> list[dict[str, str]]:
        """Retorna o saldo projetado por dia até o horizonte informado.

        - Não altera nada no banco (Read-Only).
        - Inclui:
          * transações pendentes futuras
          * faturas de cartão de crédito pendentes
          * recorrências ainda não materializadas em transações
        """
        if months_ahead < 1:
            raise ValueError("O horizonte deve ter pelo menos 1 mês.")
        if months_ahead > 24:
            raise ValueError("O horizonte não pode exceder 24 meses.")

        today = date.today()
        horizon = today + relativedelta(months=months_ahead)
        current_balance = BalanceService(self.db).get_total_balance(user_id)

        regular_flows = self._regular_future_flows(user_id, today, horizon)
        card_invoices = self._card_invoice_future_flows(user_id, today, horizon)
        recurring_flows = self._recurring_future_flows(user_id, today, horizon)

        all_flows = regular_flows + card_invoices + recurring_flows
        frame = self._build_frame(all_flows, today, horizon)
        frame["projected_balance"] = current_balance + frame["net_cash_flow"]

        projected = [
            {
                "date": row["date"].isoformat(),
                "projected_balance": f"{row['projected_balance']:.2f}",
            }
            for _, row in frame.iterrows()
        ]
        app_logger.info(
            f"Projeção de caixa gerada: usuário {user_id}, "
            f"horizonte {months_ahead} meses, {len(projected)} dias."
        )
        return projected

    def _regular_future_flows(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[tuple[date, Decimal]]:
        """Entradas e saídas pendentes futuras em contas correntes."""
        rows = (
            self.db.query(
                Transaction.due_date,
                Transaction.transaction_type,
                func.sum(Transaction.base_amount).label("total"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.credit_card_id.is_(None),
                Transaction.status != TransactionStatus.CANCELLED,
                Transaction.paid_date.is_(None),
                Transaction.due_date > start_date,
                Transaction.due_date <= end_date,
                Transaction.transaction_type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
            )
            .group_by(
                Transaction.due_date,
                Transaction.transaction_type,
            )
            .all()
        )

        flows: list[tuple[date, Decimal]] = []
        for due_date, transaction_type, total in rows:
            value = to_money2(total or 0, where="cashflow.projection.regular")
            if transaction_type == TransactionType.INCOME:
                flows.append((due_date, value))
            else:
                flows.append((due_date, -value))
        return flows

    def _card_invoice_future_flows(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[tuple[date, Decimal]]:
        """Faturas de cartão pendentes, agrupadas por data de vencimento."""
        rows = (
            self.db.query(
                Transaction.due_date,
                func.sum(Transaction.base_amount).label("total"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.credit_card_id.isnot(None),
                Transaction.status != TransactionStatus.CANCELLED,
                Transaction.paid_date.is_(None),
                Transaction.due_date > start_date,
                Transaction.due_date <= end_date,
            )
            .group_by(Transaction.due_date)
            .all()
        )

        return [
            (
                due_date,
                -to_money2(total or 0, where="cashflow.projection.card_invoice"),
            )
            for due_date, total in rows
        ]

    def _recurring_future_flows(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> list[tuple[date, Decimal]]:
        """Recorrências ainda não materializadas em transações."""
        service = BillRecurrenceService(self.db)
        flows: list[tuple[date, Decimal]] = []

        cursor = start_date.replace(day=1)
        while cursor <= end_date:
            previews = service.project_period(user_id, cursor.year, cursor.month)
            for preview in previews:
                if preview["already_generated"]:
                    continue
                due = date.fromisoformat(preview["due_date"])
                if due <= start_date or due > end_date:
                    continue
                amount = to_money2(
                    preview["amount"],
                    where="cashflow.projection.recurring",
                )
                if preview["bill_type"] == BillType.RECEIVABLE.value:
                    flows.append((due, amount))
                else:
                    flows.append((due, -amount))
            cursor += relativedelta(months=1)
        return flows

    @staticmethod
    def _build_frame(
        flows: list[tuple[date, Decimal]],
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Cria o DataFrame diário e aplica a soma cumulativa dos fluxos."""
        if flows:
            frame = pd.DataFrame(
                flows,
                columns=["date", "cash_flow"],
            )
        else:
            frame = pd.DataFrame(
                {
                    "date": pd.Series([], dtype="object"),
                    "cash_flow": pd.Series([], dtype="object"),
                }
            )

        frame["date"] = pd.to_datetime(frame["date"])
        grouped = frame.groupby("date", as_index=False)["cash_flow"].sum()
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        calendar = pd.DataFrame({"date": date_range})
        merged = calendar.merge(grouped, on="date", how="left")
        merged["cash_flow"] = merged["cash_flow"].fillna(Decimal("0.00"))
        merged["net_cash_flow"] = merged["cash_flow"].cumsum()
        merged["date"] = merged["date"].dt.date
        return merged[["date", "net_cash_flow"]].copy()

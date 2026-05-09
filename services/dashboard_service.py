"""
Serviço para agregações e métricas do dashboard.
Inclui get_forecast_balance para projeção Efetivado + Previsto.
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from database.models.transaction import Transaction, TransactionType
from database.models.account import Account
from database.models.category import Category
from config.logging_config import app_logger

class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def _get_sum(self, user_id: int, type_: TransactionType,
                 start_date: date, end_date: date, paid: bool = True) -> float:
        query = self.db.query(func.sum(Transaction.base_amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == type_
        )
        if paid:
            query = query.filter(
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= start_date,
                Transaction.paid_date <= end_date
            )
        else:
            query = query.filter(
                Transaction.paid_date.is_(None),
                Transaction.due_date >= start_date,
                Transaction.due_date <= end_date
            )
        return query.scalar() or 0.0

    def get_overview(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        receitas_pagas     = self._get_sum(user_id, TransactionType.INCOME,   start_date, end_date, paid=True)
        receitas_pendentes = self._get_sum(user_id, TransactionType.INCOME,   start_date, end_date, paid=False)
        despesas_pagas     = self._get_sum(user_id, TransactionType.EXPENSE,  start_date, end_date, paid=True)
        despesas_pendentes = self._get_sum(user_id, TransactionType.EXPENSE,  start_date, end_date, paid=False)
        saldo_contas = self.db.query(func.sum(Account.balance)).filter(
            Account.user_id == user_id, Account.is_active == True
        ).scalar() or 0.0
        return {
            "receitas":  {"pagas": receitas_pagas,  "pendentes": receitas_pendentes,
                          "total": receitas_pagas + receitas_pendentes},
            "despesas":  {"pagas": despesas_pagas,  "pendentes": despesas_pendentes,
                          "total": despesas_pagas + despesas_pendentes},
            "saldo":     {"contas": saldo_contas,
                          "periodo": receitas_pagas - despesas_pagas},
        }

    # ─── NOVO: Projeção "Como fecho o mês?" ─────────────────────────────────
    def get_forecast_balance(self, user_id: int, start_date: date, end_date: date) -> Dict[str, float]:
        """
        Retorna o saldo projetado para fechar o período:
          - efetivado   = receitas pagas - despesas pagas (o que já aconteceu)
          - previsto    = (receitas pagas + rec. pendentes) - (desp. pagas + desp. pendentes)
          - delta       = previsto - efetivado  (quanto ainda entra/sai)
        """
        rec_pago   = self._get_sum(user_id, TransactionType.INCOME,  start_date, end_date, paid=True)
        rec_pend   = self._get_sum(user_id, TransactionType.INCOME,  start_date, end_date, paid=False)
        desp_pago  = self._get_sum(user_id, TransactionType.EXPENSE, start_date, end_date, paid=True)
        desp_pend  = self._get_sum(user_id, TransactionType.EXPENSE, start_date, end_date, paid=False)

        efetivado = rec_pago  - desp_pago
        previsto  = (rec_pago + rec_pend) - (desp_pago + desp_pend)
        return {
            "efetivado":        efetivado,
            "previsto":         previsto,
            "delta":            previsto - efetivado,
            "rec_pago":         rec_pago,
            "rec_pendente":     rec_pend,
            "desp_pago":        desp_pago,
            "desp_pendente":    desp_pend,
        }

    def get_monthly_evolution(self, user_id: int, months: int = 6) -> Dict[str, List[Dict[str, Any]]]:
        evolution = {"receitas": [], "despesas": []}
        today = date.today()
        for i in range(months - 1, -1, -1):
            date_cursor = today - relativedelta(months=i)
            start_date  = date_cursor.replace(day=1)
            end_date    = start_date + relativedelta(months=1) - timedelta(days=1)
            rec  = self._get_sum(user_id, TransactionType.INCOME,  start_date, end_date, paid=True)
            desp = self._get_sum(user_id, TransactionType.EXPENSE, start_date, end_date, paid=True)
            label = start_date.strftime("%b/%Y")
            evolution["receitas"].append({"month": label, "value": rec})
            evolution["despesas"].append({"month": label, "value": desp})
        return evolution

    def get_category_breakdown(self, user_id, transaction_type, start_date, end_date):
        results = self.db.query(
            Category.name, Category.icon, Category.color,
            func.sum(Transaction.base_amount).label("total")
        ).join(Transaction, Transaction.category_id == Category.id).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type,
            Transaction.paid_date.isnot(None),
            Transaction.paid_date >= start_date,
            Transaction.paid_date <= end_date
        ).group_by(Category.name, Category.icon, Category.color).order_by(desc("total")).limit(10).all()
        return [{"name": r.name, "icon": r.icon or "📁",
                 "color": r.color or "#95a5a6", "total": r.total} for r in results]

    def get_upcoming_expenses(self, user_id: int, limit: int = 5) -> List[Transaction]:
        today = date.today()
        # Inclui atrasadas (due_date < hoje sem paid_date) e próximas (até 30 dias)
        horizon = today + timedelta(days=30)
        return self.db.query(Transaction).options(
            joinedload(Transaction.category)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.paid_date.is_(None),
            Transaction.due_date <= horizon,
        ).order_by(asc(Transaction.due_date)).limit(limit).all()

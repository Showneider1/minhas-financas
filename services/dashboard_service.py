"""
Serviço para agregações e métricas do dashboard.
"""
from typing import Dict, Any, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, asc, case
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

    def get_saldo_calculado(self, user_id: int) -> float:
        """
        Recalcula saldo real somando todas as transações pagas:
        receitas pagas - despesas pagas (independe de período).
        Usado porque Account.balance pode não ser atualizado automaticamente.
        """
        resultado = self.db.query(
            func.sum(
                case(
                    (Transaction.transaction_type == TransactionType.INCOME,   Transaction.base_amount),
                    (Transaction.transaction_type == TransactionType.EXPENSE, -Transaction.base_amount),
                    else_=0
                )
            )
        ).filter(
            Transaction.user_id == user_id,
            Transaction.paid_date.isnot(None),
        ).scalar() or 0.0
        return resultado

    def get_overview(self, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        receitas_pagas     = self._get_sum(user_id, TransactionType.INCOME,  start_date, end_date, paid=True)
        receitas_pendentes = self._get_sum(user_id, TransactionType.INCOME,  start_date, end_date, paid=False)
        despesas_pagas     = self._get_sum(user_id, TransactionType.EXPENSE, start_date, end_date, paid=True)
        despesas_pendentes = self._get_sum(user_id, TransactionType.EXPENSE, start_date, end_date, paid=False)
        saldo_contas = self.db.query(func.sum(Account.balance)).filter(
            Account.user_id == user_id, Account.is_active == True
        ).scalar() or 0.0
        return {
            "receitas": {"pagas": receitas_pagas,  "pendentes": receitas_pendentes,
                         "total": receitas_pagas + receitas_pendentes},
            "despesas": {"pagas": despesas_pagas,  "pendentes": despesas_pendentes,
                         "total": despesas_pagas + despesas_pendentes},
            "saldo":    {"contas": saldo_contas,
                         "periodo": receitas_pagas - despesas_pagas},
        }

    def get_forecast_balance(self, user_id: int, start_date: date, end_date: date) -> Dict[str, float]:
        rec_pago  = self._get_sum(user_id, TransactionType.INCOME,  start_date, end_date, paid=True)
        rec_pend  = self._get_sum(user_id, TransactionType.INCOME,  start_date, end_date, paid=False)
        desp_pago = self._get_sum(user_id, TransactionType.EXPENSE, start_date, end_date, paid=True)
        desp_pend = self._get_sum(user_id, TransactionType.EXPENSE, start_date, end_date, paid=False)
        efetivado = rec_pago - desp_pago
        previsto  = (rec_pago + rec_pend) - (desp_pago + desp_pend)
        return {
            "efetivado":     efetivado,
            "previsto":      previsto,
            "delta":         previsto - efetivado,
            "rec_pago":      rec_pago,
            "rec_pendente":  rec_pend,
            "desp_pago":     desp_pago,
            "desp_pendente": desp_pend,
        }

    def get_monthly_evolution(self, user_id: int, months: int = 6) -> Dict[str, List[Dict[str, Any]]]:
        """
        Evolução mensal — inclui pagas E pendentes para refletir
        o mês atual mesmo sem efetivações.
        """
        evolution = {"receitas": [], "despesas": []}
        today = date.today()
        for i in range(months - 1, -1, -1):
            date_cursor = today - relativedelta(months=i)
            start_date  = date_cursor.replace(day=1)
            end_date    = start_date + relativedelta(months=1) - timedelta(days=1)

            # Meses passados: apenas pagas. Mês atual: pagas + pendentes
            is_current = (date_cursor.year == today.year and date_cursor.month == today.month)
            rec_pago  = self._get_sum(user_id, TransactionType.INCOME,  start_date, end_date, paid=True)
            desp_pago = self._get_sum(user_id, TransactionType.EXPENSE, start_date, end_date, paid=True)

            if is_current:
                rec_pend  = self._get_sum(user_id, TransactionType.INCOME,  start_date, end_date, paid=False)
                desp_pend = self._get_sum(user_id, TransactionType.EXPENSE, start_date, end_date, paid=False)
                rec  = rec_pago  + rec_pend
                desp = desp_pago + desp_pend
            else:
                rec  = rec_pago
                desp = desp_pago

            label = start_date.strftime("%b/%Y")
            evolution["receitas"].append({"month": label, "value": rec})
            evolution["despesas"].append({"month": label, "value": desp})
        return evolution

    def get_category_breakdown(self, user_id, transaction_type, start_date, end_date):
        """Categorias com transações PAGAS no período."""
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

    def get_category_breakdown_pending(self, user_id, transaction_type, start_date, end_date):
        """Categorias com transações PENDENTES no período (fallback quando não há pagas)."""
        results = self.db.query(
            Category.name, Category.icon, Category.color,
            func.sum(Transaction.base_amount).label("total")
        ).join(Transaction, Transaction.category_id == Category.id).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type,
            Transaction.paid_date.is_(None),
            Transaction.due_date >= start_date,
            Transaction.due_date <= end_date,
        ).group_by(Category.name, Category.icon, Category.color).order_by(desc("total")).limit(10).all()
        return [{"name": r.name, "icon": r.icon or "📁",
                 "color": r.color or "#95a5a6", "total": r.total} for r in results]

    def get_category_breakdown_all(self, user_id, transaction_type, start_date, end_date):
        """Categorias com transações PAGAS + PENDENTES no período."""
        results = self.db.query(
            Category.name, Category.icon, Category.color,
            func.sum(Transaction.base_amount).label("total")
        ).join(Transaction, Transaction.category_id == Category.id).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type,
            # due_date OU paid_date dentro do período
            func.coalesce(Transaction.paid_date, Transaction.due_date) >= start_date,
            func.coalesce(Transaction.paid_date, Transaction.due_date) <= end_date,
        ).group_by(Category.name, Category.icon, Category.color).order_by(desc("total")).limit(10).all()
        return [{"name": r.name, "icon": r.icon or "📁",
                 "color": r.color or "#95a5a6", "total": r.total} for r in results]

    def get_upcoming_expenses(self, user_id: int, limit: int = 5) -> List[Transaction]:
        today = date.today()
        horizon = today + timedelta(days=30)
        return self.db.query(Transaction).options(
            joinedload(Transaction.category)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.paid_date.is_(None),
            Transaction.due_date <= horizon,
        ).order_by(asc(Transaction.due_date)).limit(limit).all()

    def get_pending_sum(self, user_id: int, transaction_type: TransactionType,
                        start_date: date, end_date: date) -> float:
        """Soma das transações pendentes (sem paid_date) no período."""
        return self._get_sum(user_id, transaction_type, start_date, end_date, paid=False)

    def get_upcoming_transactions(self, user_id: int, days_ahead: int = 30,
                                  limit: int = 10) -> List[Transaction]:
        """Transações pendentes (receitas e despesas) — inclui atrasadas dos últimos 30 dias."""
        today   = date.today()
        horizon = today + timedelta(days=days_ahead)
        return (
            self.db.query(Transaction)
            .options(joinedload(Transaction.category))
            .filter(
                Transaction.user_id == user_id,
                Transaction.paid_date.is_(None),
                Transaction.due_date >= today - timedelta(days=30),
                Transaction.due_date <= horizon,
            )
            .order_by(asc(Transaction.due_date))
            .limit(limit)
            .all()
        )

    def get_financial_health_score(self, user_id: int) -> Dict[str, Any]:
        import math

        today            = date.today()
        start_this_month = today.replace(day=1)
        end_this_month   = today

        receita_mes = self._get_sum(user_id, TransactionType.INCOME,  start_this_month, end_this_month, paid=True)
        despesa_mes = self._get_sum(user_id, TransactionType.EXPENSE, start_this_month, end_this_month, paid=True)

        poupanca          = max(receita_mes - despesa_mes, 0)
        taxa_poupanca_pct = (poupanca / receita_mes * 100) if receita_mes > 0 else 0
        score_poupanca    = min(taxa_poupanca_pct / 20.0 * 30, 30)

        if receita_mes > 0:
            ratio_desp    = despesa_mes / receita_mes
            score_despesa = max(0.0, (1 - ratio_desp) / 0.2 * 25)
            score_despesa = min(score_despesa, 25)
        else:
            ratio_desp    = 1.0
            score_despesa = 0.0

        monthly_incomes = []
        for i in range(3):
            m_start = (today.replace(day=1) - relativedelta(months=i+1)).replace(day=1)
            m_end   = m_start + relativedelta(months=1) - timedelta(days=1)
            val = self._get_sum(user_id, TransactionType.INCOME, m_start, m_end, paid=True)
            monthly_incomes.append(val)

        if len(monthly_incomes) >= 2 and sum(monthly_incomes) > 0:
            mean_inc           = sum(monthly_incomes) / len(monthly_incomes)
            variance           = sum((x - mean_inc) ** 2 for x in monthly_incomes) / len(monthly_incomes)
            std_dev            = math.sqrt(variance)
            cv                 = std_dev / mean_inc if mean_inc > 0 else 1.0
            score_regularidade = max(0.0, (0.5 - cv) / 0.4 * 20)
            score_regularidade = min(score_regularidade, 20)
        else:
            score_regularidade = 10.0

        saldo_contas = self.get_saldo_calculado(user_id)

        media_despesa_mensal = (
            sum(
                self._get_sum(
                    user_id, TransactionType.EXPENSE,
                    (today.replace(day=1) - relativedelta(months=i+1)).replace(day=1),
                    ((today.replace(day=1) - relativedelta(months=i+1)).replace(day=1)
                     + relativedelta(months=1) - timedelta(days=1)),
                    paid=True,
                )
                for i in range(3)
            ) / 3
        )

        if media_despesa_mensal > 0:
            meses_reserva  = saldo_contas / media_despesa_mensal
            score_liquidez = min(meses_reserva / 3.0 * 15, 15)
        else:
            score_liquidez = 0.0

        start_3m = today.replace(day=1) - relativedelta(months=3)
        num_categorias = (
            self.db.query(Transaction.category_id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.paid_date >= start_3m,
            )
            .distinct()
            .count()
        )
        score_diversificacao = min(num_categorias / 5.0 * 10, 10)

        score_total = round(
            score_poupanca + score_despesa + score_regularidade
            + score_liquidez + score_diversificacao, 1,
        )

        if score_total >= 80:   classificacao = "Excelente"
        elif score_total >= 60: classificacao = "Bom"
        elif score_total >= 40: classificacao = "Regular"
        elif score_total >= 20: classificacao = "Atencao"
        else:                   classificacao = "Critico"

        recomendacoes = []
        if taxa_poupanca_pct < 10:
            recomendacoes.append(
                "Sua taxa de poupanca esta abaixo de 10%. Tente reduzir despesas "
                "nao essenciais ou aumentar suas receitas."
            )
        elif taxa_poupanca_pct < 20:
            recomendacoes.append(
                f"Voce esta poupando {taxa_poupanca_pct:.1f}% da sua renda. "
                "A meta recomendada e de 20% ou mais."
            )
        if ratio_desp > 0.9:
            recomendacoes.append(
                "Seus gastos representam mais de 90% da sua renda. "
                "Revise suas despesas fixas urgentemente."
            )
        if saldo_contas < media_despesa_mensal:
            recomendacoes.append(
                "Seu saldo atual e menor do que um mes de despesas. "
                "Priorize a construcao de uma reserva de emergencia."
            )
        if not recomendacoes:
            recomendacoes.append(
                "Parabens! Sua saude financeira esta em boa forma. "
                "Continue monitorando seus gastos e investimentos."
            )

        return {
            "score_total":   score_total,
            "classificacao": classificacao,
            "dimensoes": {
                "poupanca":      {"score": round(score_poupanca, 1),      "max": 30, "valor_pct": round(taxa_poupanca_pct, 1)},
                "despesas":      {"score": round(score_despesa, 1),       "max": 25, "ratio_pct": round(ratio_desp * 100, 1)},
                "regularidade":  {"score": round(score_regularidade, 1),  "max": 20},
                "liquidez":      {"score": round(score_liquidez, 1),      "max": 15, "meses_reserva": round(saldo_contas / media_despesa_mensal if media_despesa_mensal > 0 else 0, 1)},
                "diversificacao":{"score": round(score_diversificacao, 1),"max": 10, "num_categorias": num_categorias},
            },
            "recomendacoes": recomendacoes,
            "receita_mes":   round(receita_mes, 2),
            "despesa_mes":   round(despesa_mes, 2),
            "saldo_contas":  round(saldo_contas, 2),
        }
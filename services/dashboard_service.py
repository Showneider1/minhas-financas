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


    def get_financial_health_score(self, user_id: int) -> Dict[str, Any]:
        """Calcula o Score de Saude Financeira do usuario (0-100).

        O score e composto por 5 dimensoes ponderadas:

        1. Taxa de Poupanca (30 pts):
           Percentual de receita guardado no mes. Meta: >= 20%.
           Pontuacao proporcional: min(poupanca% / 20% * 30, 30)

        2. Controle de Despesas (25 pts):
           Despesas totais vs receita total. Meta: despesas < 80% da receita.
           Pontuacao: max(0, (1 - desp/rec) / 0.2 * 25), capped em 25

        3. Regularidade de Receitas (20 pts):
           Analisa os ultimos 3 meses. Receita consistente (desvio-padrao baixo)
           indica estabilidade financeira.

        4. Liquidez (15 pts):
           Saldo total de contas em relacao a media mensal de despesas.
           Meta: saldo >= 3x despesas mensais (reserva de emergencia minima).

        5. Diversificacao (10 pts):
           Numero de categorias de despesa distintas nos ultimos 3 meses.
           Score maximo com >= 5 categorias diferentes.

        Returns:
            Dict com score_total (0-100), classificacao, dimensoes detalhadas
            e lista de recomendacoes personalizadas.
        """
        from dateutil.relativedelta import relativedelta
        import math

        today = date.today()
        start_this_month = today.replace(day=1)
        end_this_month   = today

        # Receita e despesa do mes corrente (pagas)
        receita_mes = self._get_sum(
            user_id, TransactionType.INCOME,
            start_this_month, end_this_month, paid=True
        )
        despesa_mes = self._get_sum(
            user_id, TransactionType.EXPENSE,
            start_this_month, end_this_month, paid=True
        )

        # ---- 1. Taxa de Poupanca (30 pts) ----
        poupanca = max(receita_mes - despesa_mes, 0)
        taxa_poupanca_pct = (poupanca / receita_mes * 100) if receita_mes > 0 else 0
        score_poupanca = min(taxa_poupanca_pct / 20.0 * 30, 30)  # Meta: 20%

        # ---- 2. Controle de Despesas (25 pts) ----
        if receita_mes > 0:
            ratio_desp = despesa_mes / receita_mes
            # Abaixo de 80%: score proporcional; acima: 0
            score_despesa = max(0.0, (1 - ratio_desp) / 0.2 * 25)
            score_despesa = min(score_despesa, 25)
        else:
            ratio_desp = 1.0
            score_despesa = 0.0

        # ---- 3. Regularidade de Receitas (20 pts) ----
        monthly_incomes = []
        for i in range(3):
            m_start = (today.replace(day=1) - relativedelta(months=i+1)).replace(day=1)
            m_end   = m_start + relativedelta(months=1) - timedelta(days=1)
            val = self._get_sum(user_id, TransactionType.INCOME, m_start, m_end, paid=True)
            monthly_incomes.append(val)

        if len(monthly_incomes) >= 2 and sum(monthly_incomes) > 0:
            mean_inc = sum(monthly_incomes) / len(monthly_incomes)
            variance = sum((x - mean_inc) ** 2 for x in monthly_incomes) / len(monthly_incomes)
            std_dev  = math.sqrt(variance)
            cv = std_dev / mean_inc if mean_inc > 0 else 1.0  # Coeficiente de Variacao
            # CV <= 0.1 = 20 pts; CV >= 0.5 = 0 pts
            score_regularidade = max(0.0, (0.5 - cv) / 0.4 * 20)
            score_regularidade = min(score_regularidade, 20)
        else:
            score_regularidade = 10.0  # Dados insuficientes -> score neutro

        # ---- 4. Liquidez - Reserva de Emergencia (15 pts) ----
        saldo_contas = (
            self.db.query(func.sum(Account.balance))
            .filter(Account.user_id == user_id, Account.is_active == True)
            .scalar() or 0.0
        )
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
            meses_reserva = saldo_contas / media_despesa_mensal
            # Meta: 3 meses de reserva = 15 pts
            score_liquidez = min(meses_reserva / 3.0 * 15, 15)
        else:
            score_liquidez = 0.0

        # ---- 5. Diversificacao de Despesas (10 pts) ----
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
        # Meta: >= 5 categorias = 10 pts
        score_diversificacao = min(num_categorias / 5.0 * 10, 10)

        # ---- Score Total ----
        score_total = round(
            score_poupanca + score_despesa + score_regularidade
            + score_liquidez + score_diversificacao,
            1,
        )

        # Classificacao
        if score_total >= 80:
            classificacao = "Excelente"
        elif score_total >= 60:
            classificacao = "Bom"
        elif score_total >= 40:
            classificacao = "Regular"
        elif score_total >= 20:
            classificacao = "Atencao"
        else:
            classificacao = "Critico"

        # Recomendacoes personalizadas
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
            "score_total": score_total,
            "classificacao": classificacao,
            "dimensoes": {
                "poupanca":      {"score": round(score_poupanca, 1),      "max": 30, "valor_pct": round(taxa_poupanca_pct, 1)},
                "despesas":      {"score": round(score_despesa, 1),       "max": 25, "ratio_pct": round(ratio_desp * 100, 1)},
                "regularidade":  {"score": round(score_regularidade, 1), "max": 20},
                "liquidez":      {"score": round(score_liquidez, 1),      "max": 15, "meses_reserva": round(saldo_contas / media_despesa_mensal if media_despesa_mensal > 0 else 0, 1)},
                "diversificacao":{"score": round(score_diversificacao, 1),"max": 10, "num_categorias": num_categorias},
            },
            "recomendacoes": recomendacoes,
            "receita_mes": round(receita_mes, 2),
            "despesa_mes": round(despesa_mes, 2),
            "saldo_contas": round(saldo_contas, 2),
        }

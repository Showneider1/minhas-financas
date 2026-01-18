"""
Serviço para agregações e métricas do dashboard.
"""
from datetime import date, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from database.repositories.transaction_repo import TransactionRepository
from database.repositories.account_repo import AccountRepository
from database.models.category import TransactionType
from database.models.transaction import TransactionStatus
from utils.date_helpers import (
    get_current_month_range,
    get_last_month_range,
    add_months,
)
from config.logging_config import app_logger


class DashboardService:
    """
    Serviço especializado em métricas e agregações para dashboard.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.account_repo = AccountRepository(db)
    
    def get_overview(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Retorna visão geral financeira do período.
        
        Args:
            user_id: ID do usuário
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            Dict com métricas gerais
        """
        # Receitas
        receitas_pagas = self.transaction_repo.sum_by_type(
            user_id, TransactionType.INCOME, start_date, end_date, TransactionStatus.PAID
        )
        receitas_pendentes = self.transaction_repo.sum_by_type(
            user_id, TransactionType.INCOME, start_date, end_date, TransactionStatus.PENDING
        )
        
        # Despesas
        despesas_pagas = self.transaction_repo.sum_by_type(
            user_id, TransactionType.EXPENSE, start_date, end_date, TransactionStatus.PAID
        )
        despesas_pendentes = self.transaction_repo.sum_by_type(
            user_id, TransactionType.EXPENSE, start_date, end_date, TransactionStatus.PENDING
        )
        
        # Saldo
        saldo_periodo = receitas_pagas - despesas_pagas
        saldo_previsto = saldo_periodo + receitas_pendentes - despesas_pendentes
        
        # Saldo total das contas
        saldo_contas = self.account_repo.get_total_balance(user_id)
        
        return {
            "receitas": {
                "pagas": round(receitas_pagas, 2),
                "pendentes": round(receitas_pendentes, 2),
                "total": round(receitas_pagas + receitas_pendentes, 2),
            },
            "despesas": {
                "pagas": round(despesas_pagas, 2),
                "pendentes": round(despesas_pendentes, 2),
                "total": round(despesas_pagas + despesas_pendentes, 2),
            },
            "saldo": {
                "periodo": round(saldo_periodo, 2),
                "previsto": round(saldo_previsto, 2),
                "contas": round(saldo_contas, 2),
            },
            "economia": {
                "valor": round(receitas_pagas - despesas_pagas, 2),
                "percentual": round((receitas_pagas - despesas_pagas) / receitas_pagas * 100, 2) if receitas_pagas > 0 else 0,
            }
        }
    
    def get_category_breakdown(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: date,
        end_date: date,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retorna distribuição por categoria.
        
        Args:
            user_id: ID do usuário
            transaction_type: INCOME ou EXPENSE
            start_date: Data inicial
            end_date: Data final
            limit: Número máximo de categorias
        
        Returns:
            Lista de categorias com totais e percentuais
        """
        categories = self.transaction_repo.get_category_totals(
            user_id, transaction_type, start_date, end_date
        )
        
        # Calcula total para percentuais
        total = sum(cat['total'] for cat in categories)
        
        # Adiciona percentuais
        for cat in categories:
            cat['percentage'] = round(cat['total'] / total * 100, 2) if total > 0 else 0
        
        return categories[:limit]
    
    def get_monthly_evolution(
        self,
        user_id: int,
        months: int = 6,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retorna evolução mensal dos últimos N meses.
        
        Args:
            user_id: ID do usuário
            months: Número de meses
        
        Returns:
            Dict com evolução de receitas e despesas
        """
        today = date.today()
        evolution = {
            "receitas": [],
            "despesas": [],
            "saldo": [],
        }
        
        for i in range(months - 1, -1, -1):
            # Calcula mês
            month_date = add_months(today, -i)
            start_date = month_date.replace(day=1)
            
            # Último dia do mês
            if month_date.month == 12:
                end_date = date(month_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(month_date.year, month_date.month + 1, 1) - timedelta(days=1)
            
            # Busca totais
            receitas = self.transaction_repo.sum_by_type(
                user_id, TransactionType.INCOME, start_date, end_date, TransactionStatus.PAID
            )
            despesas = self.transaction_repo.sum_by_type(
                user_id, TransactionType.EXPENSE, start_date, end_date, TransactionStatus.PAID
            )
            
            month_label = start_date.strftime("%b/%Y")
            
            evolution["receitas"].append({
                "month": month_label,
                "value": round(receitas, 2),
            })
            evolution["despesas"].append({
                "month": month_label,
                "value": round(despesas, 2),
            })
            evolution["saldo"].append({
                "month": month_label,
                "value": round(receitas - despesas, 2),
            })
        
        return evolution
    
    def get_overdue_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Retorna resumo de transações atrasadas.
        
        Args:
            user_id: ID do usuário
        
        Returns:
            Dict com informações de atrasos
        """
        overdue_transactions = self.transaction_repo.get_overdue(user_id)
        
        receitas_atrasadas = sum(
            t.amount for t in overdue_transactions
            if t.transaction_type == TransactionType.INCOME
        )
        despesas_atrasadas = sum(
            t.amount for t in overdue_transactions
            if t.transaction_type == TransactionType.EXPENSE
        )
        
        return {
            "total_count": len(overdue_transactions),
            "receitas": {
                "count": sum(1 for t in overdue_transactions if t.transaction_type == TransactionType.INCOME),
                "total": round(receitas_atrasadas, 2),
            },
            "despesas": {
                "count": sum(1 for t in overdue_transactions if t.transaction_type == TransactionType.EXPENSE),
                "total": round(despesas_atrasadas, 2),
            },
        }
    
    def get_comparison_with_last_month(
        self,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Compara mês atual com mês anterior.
        
        Args:
            user_id: ID do usuário
        
        Returns:
            Dict com comparações e variações
        """
        # Mês atual
        current_start, current_end = get_current_month_range()
        
        # Mês anterior
        last_start, last_end = get_last_month_range()
        
        # Totais mês atual
        current_income = self.transaction_repo.sum_by_type(
            user_id, TransactionType.INCOME, current_start, current_end, TransactionStatus.PAID
        )
        current_expense = self.transaction_repo.sum_by_type(
            user_id, TransactionType.EXPENSE, current_start, current_end, TransactionStatus.PAID
        )
        
        # Totais mês anterior
        last_income = self.transaction_repo.sum_by_type(
            user_id, TransactionType.INCOME, last_start, last_end, TransactionStatus.PAID
        )
        last_expense = self.transaction_repo.sum_by_type(
            user_id, TransactionType.EXPENSE, last_start, last_end, TransactionStatus.PAID
        )
        
        # Calcula variações
        def calc_variation(current, last):
            if last == 0:
                return 0 if current == 0 else 100
            return round((current - last) / last * 100, 2)
        
        return {
            "receitas": {
                "atual": round(current_income, 2),
                "anterior": round(last_income, 2),
                "variacao": calc_variation(current_income, last_income),
            },
            "despesas": {
                "atual": round(current_expense, 2),
                "anterior": round(last_expense, 2),
                "variacao": calc_variation(current_expense, last_expense),
            },
            "saldo": {
                "atual": round(current_income - current_expense, 2),
                "anterior": round(last_income - last_expense, 2),
                "variacao": calc_variation(
                    current_income - current_expense,
                    last_income - last_expense
                ),
            },
        }

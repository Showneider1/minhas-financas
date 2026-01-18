"""
Serviço para geração de relatórios financeiros.
"""
from datetime import date
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from database.repositories.transaction_repo import TransactionRepository
from database.repositories.account_repo import AccountRepository
from schemas.transaction_schema import TransactionFilter
from utils.date_helpers import get_month_range, get_year_range
from config.logging_config import app_logger


class ReportService:
    """
    Serviço de geração de relatórios.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.account_repo = AccountRepository(db)
    
    def generate_monthly_report(
        self,
        user_id: int,
        year: int,
        month: int,
    ) -> Dict[str, Any]:
        """
        Gera relatório mensal completo.
        
        Args:
            user_id: ID do usuário
            year: Ano
            month: Mês
        
        Returns:
            Dict com dados do relatório
        """
        start_date, end_date = get_month_range(year, month)
        
        # Busca todas as transações do mês
        transactions, total = self.transaction_repo.filter_transactions(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=10000,  # Sem paginação para relatório
        )
        
        # Agrupa por categoria
        from database.models.category import TransactionType
        categories_income = self.transaction_repo.get_category_totals(
            user_id, TransactionType.INCOME, start_date, end_date
        )
        categories_expense = self.transaction_repo.get_category_totals(
            user_id, TransactionType.EXPENSE, start_date, end_date
        )
        
        # Calcula totais
        from database.models.transaction import TransactionStatus
        total_income = self.transaction_repo.sum_by_type(
            user_id, TransactionType.INCOME, start_date, end_date, TransactionStatus.PAID
        )
        total_expense = self.transaction_repo.sum_by_type(
            user_id, TransactionType.EXPENSE, start_date, end_date, TransactionStatus.PAID
        )
        
        return {
            "periodo": {
                "mes": month,
                "ano": year,
                "inicio": start_date.isoformat(),
                "fim": end_date.isoformat(),
            },
            "resumo": {
                "total_receitas": round(total_income, 2),
                "total_despesas": round(total_expense, 2),
                "saldo": round(total_income - total_expense, 2),
                "total_transacoes": total,
            },
            "categorias": {
                "receitas": categories_income,
                "despesas": categories_expense,
            },
            "transacoes": [
                {
                    "id": t.id,
                    "data": t.due_date.isoformat(),
                    "descricao": t.description,
                    "categoria": t.category.name,
                    "valor": t.amount,
                    "tipo": t.transaction_type.value,
                    "status": t.status.value,
                }
                for t in transactions
            ],
        }
    
    def generate_annual_report(
        self,
        user_id: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        Gera relatório anual completo.
        
        Args:
            user_id: ID do usuário
            year: Ano
        
        Returns:
            Dict com dados do relatório
        """
        start_date, end_date = get_year_range(year)
        
        # Totais por mês
        monthly_data = []
        for month in range(1, 13):
            month_start, month_end = get_month_range(year, month)
            
            from database.models.category import TransactionType
            from database.models.transaction import TransactionStatus
            
            income = self.transaction_repo.sum_by_type(
                user_id, TransactionType.INCOME, month_start, month_end, TransactionStatus.PAID
            )
            expense = self.transaction_repo.sum_by_type(
                user_id, TransactionType.EXPENSE, month_start, month_end, TransactionStatus.PAID
            )
            
            monthly_data.append({
                "mes": month,
                "receitas": round(income, 2),
                "despesas": round(expense, 2),
                "saldo": round(income - expense, 2),
            })
        
        # Totais anuais
        from database.models.category import TransactionType
        from database.models.transaction import TransactionStatus
        
        total_income = self.transaction_repo.sum_by_type(
            user_id, TransactionType.INCOME, start_date, end_date, TransactionStatus.PAID
        )
        total_expense = self.transaction_repo.sum_by_type(
            user_id, TransactionType.EXPENSE, start_date, end_date, TransactionStatus.PAID
        )
        
        # Categorias do ano
        categories_income = self.transaction_repo.get_category_totals(
            user_id, TransactionType.INCOME, start_date, end_date
        )
        categories_expense = self.transaction_repo.get_category_totals(
            user_id, TransactionType.EXPENSE, start_date, end_date
        )
        
        return {
            "ano": year,
            "resumo": {
                "total_receitas": round(total_income, 2),
                "total_despesas": round(total_expense, 2),
                "saldo": round(total_income - total_expense, 2),
                "media_mensal_receitas": round(total_income / 12, 2),
                "media_mensal_despesas": round(total_expense / 12, 2),
            },
            "evolucao_mensal": monthly_data,
            "categorias": {
                "receitas": categories_income,
                "despesas": categories_expense,
            },
        }
    
    def generate_custom_report(
        self,
        user_id: int,
        filters: TransactionFilter,
    ) -> Dict[str, Any]:
        """
        Gera relatório customizado com filtros.
        
        Args:
            user_id: ID do usuário
            filters: Filtros aplicados
        
        Returns:
            Dict com dados do relatório
        """
        # Busca transações
        transactions, total = self.transaction_repo.filter_transactions(
            user_id=user_id,
            start_date=filters.start_date,
            end_date=filters.end_date,
            transaction_type=filters.transaction_type,
            status=filters.status,
            category_ids=filters.category_ids,
            account_ids=filters.account_ids,
            min_amount=filters.min_amount,
            max_amount=filters.max_amount,
            search=filters.search,
            is_recurring=filters.is_recurring,
            page=1,
            page_size=10000,
        )
        
        # Calcula totais
        from database.models.category import TransactionType
        
        total_income = sum(t.amount for t in transactions if t.transaction_type == TransactionType.INCOME)
        total_expense = sum(t.amount for t in transactions if t.transaction_type == TransactionType.EXPENSE)
        
        return {
            "filtros": filters.model_dump(exclude_none=True),
            "resumo": {
                "total_transacoes": total,
                "total_receitas": round(total_income, 2),
                "total_despesas": round(total_expense, 2),
                "saldo": round(total_income - total_expense, 2),
            },
            "transacoes": [
                {
                    "id": t.id,
                    "data": t.due_date.isoformat(),
                    "descricao": t.description,
                    "categoria": t.category.name,
                    "conta": t.account.name,
                    "valor": t.amount,
                    "tipo": t.transaction_type.value,
                    "status": t.status.value,
                }
                for t in transactions
            ],
        }

"""
Serviço de Investimentos.

Cobre toda a lógica de negócio sobre a carteira de ativos:
- Posição atual (quantidade, preço médio ponderado, P&L)
- Histórico de dividendos/rendimentos
- Relório de ganho de capital para IRPF
- Resumo consolidado da carteira por tipo de ativo

Dependências:
  - database/models/investment.py  (Asset, InvestmentOperation, OperationType, AssetType)
  - Não altera nenhum arquivo existente.

Uso típico:
    service = InvestmentService(db)
    portfolio = service.get_portfolio_position(user_id)
    dividends = service.get_dividend_history(user_id, year=2024)
    irpf      = service.get_irpf_report(user_id, year=2024)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_

from database.models.investment import Asset, InvestmentOperation, AssetType, OperationType
from config.logging_config import app_logger


# ---------------------------------------------------------------------------
# Data-classes de resposta (sem dependência de Pydantic ou ORM)
# ---------------------------------------------------------------------------

@dataclass
class PositionSummary:
    """Posição consolidada de um ativo na carteira."""
    asset_id:        int
    ticker:          str
    name:            str
    asset_type:      str
    sector:          Optional[str]
    quantity:        float          # Quantidade atual (compras - vendas)
    avg_price:       float          # Preço médio ponderado
    total_invested:  float          # quantity * avg_price
    total_fees:      float          # Soma de todas as taxas
    total_dividends: float          # Total recebido em dividendos/JCP


@dataclass
class DividendSummary:
    """Resumo de dividendos/rendimentos de um ativo no período."""
    ticker:     str
    name:       str
    asset_type: str
    total:      float
    events:     List[Dict] = field(default_factory=list)


@dataclass
class IRPFLine:
    """Linha do demonstrativo de ganho de capital (IRPF)."""
    ticker:          str
    name:            str
    asset_type:      str
    quantity_sold:   float
    avg_price:       float          # Preço médio na data da venda
    sale_price:      float          # Preço de venda
    gross_gain:      float          # (sale_price - avg_price) * quantity_sold
    fees:            float
    net_gain:        float          # gross_gain - fees
    sale_date:       date


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class InvestmentService:
    """
    Serviço de lógica de negócio para a carteira de investimentos.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Posição da Carteira
    # ------------------------------------------------------------------

    def get_portfolio_position(self, user_id: int) -> List[PositionSummary]:
        """
        Retorna a posição atual da carteira do usuário.

        Para cada ativo:
          - Soma as compras (BUY) e subtrai as vendas (SELL)
          - Calcula o preço médio ponderado apenas sobre as compras
          - Soma os dividendos/juros recebidos
          - Ignora SPLIT na conta de quantidade comprada
            (registra o SPLIT como ajuste separado de quantity)

        Ativos com posição zero (vendidos totalmente) são excluídos.
        """
        assets = (
            self.db.query(Asset)
            .filter(Asset.user_id == user_id)
            .all()
        )

        positions: List[PositionSummary] = []

        for asset in assets:
            pos = self._calculate_position(asset)
            if pos.quantity > 0:
                positions.append(pos)

        return sorted(positions, key=lambda p: p.ticker)

    def get_portfolio_summary_by_type(self, user_id: int) -> Dict[str, float]:
        """
        Retorna o total investido agrupado por tipo de ativo.
        Útil para o gráfico de diversificação da carteira.

        Returns:
            Dict[asset_type_label, total_invested]
        """
        positions = self.get_portfolio_position(user_id)
        summary: Dict[str, float] = {}
        for p in positions:
            summary[p.asset_type] = round(
                summary.get(p.asset_type, 0.0) + p.total_invested, 2
            )
        return summary

    # ------------------------------------------------------------------
    # Dividendos / Rendimentos
    # ------------------------------------------------------------------

    def get_dividend_history(
        self,
        user_id: int,
        year: Optional[int] = None,
    ) -> List[DividendSummary]:
        """
        Retorna o histórico de dividendos e rendimentos (JCP, INTEREST).
        Se `year` for informado, filtra pelo ano.
        """
        dividend_types = [OperationType.DIVIDEND, OperationType.INTEREST]

        assets = (
            self.db.query(Asset)
            .filter(Asset.user_id == user_id)
            .all()
        )

        summaries: List[DividendSummary] = []

        for asset in assets:
            ops_query = (
                self.db.query(InvestmentOperation)
                .filter(
                    InvestmentOperation.asset_id == asset.id,
                    InvestmentOperation.operation_type.in_(dividend_types),
                )
            )
            if year:
                ops_query = ops_query.filter(
                    extract("year", InvestmentOperation.date) == year
                )

            ops = ops_query.order_by(InvestmentOperation.date).all()

            if not ops:
                continue

            total = sum(op.total_amount for op in ops)
            events = [
                {
                    "date":   op.date.isoformat(),
                    "type":   op.operation_type.value,
                    "amount": op.total_amount,
                }
                for op in ops
            ]

            summaries.append(DividendSummary(
                ticker=asset.ticker,
                name=asset.name,
                asset_type=asset.asset_type.value,
                total=round(total, 2),
                events=events,
            ))

        return sorted(summaries, key=lambda s: s.total, reverse=True)

    # ------------------------------------------------------------------
    # IRPF — Ganho de Capital
    # ------------------------------------------------------------------

    def get_irpf_report(self, user_id: int, year: int) -> List[IRPFLine]:
        """
        Gera o demonstrativo de ganho/perda de capital para declaração
        do Imposto de Renda (IRPF).

        Para cada operação de VENDA no ano:
          - Obtém o preço médio das compras até a data da venda
          - Calcula ganho bruto = (preço_venda - pm) * quantidade
          - Subtrai taxas para obter ganho líquido

        Returns:
            Lista de IRPFLine ordenada por data de venda.
        """
        assets = (
            self.db.query(Asset)
            .filter(Asset.user_id == user_id)
            .all()
        )

        lines: List[IRPFLine] = []

        for asset in assets:
            sells = (
                self.db.query(InvestmentOperation)
                .filter(
                    InvestmentOperation.asset_id == asset.id,
                    InvestmentOperation.operation_type == OperationType.SELL,
                    extract("year", InvestmentOperation.date) == year,
                )
                .order_by(InvestmentOperation.date)
                .all()
            )

            for sell in sells:
                # Preço médio das compras até a data da venda
                avg = self._avg_price_until(
                    asset_id=asset.id,
                    until_date=sell.date,
                )
                gross = (sell.price_per_unit - avg) * sell.quantity
                net   = gross - sell.fees

                lines.append(IRPFLine(
                    ticker=asset.ticker,
                    name=asset.name,
                    asset_type=asset.asset_type.value,
                    quantity_sold=sell.quantity,
                    avg_price=round(avg, 4),
                    sale_price=round(sell.price_per_unit, 4),
                    gross_gain=round(gross, 2),
                    fees=round(sell.fees, 2),
                    net_gain=round(net, 2),
                    sale_date=sell.date,
                ))

        return sorted(lines, key=lambda l: l.sale_date)

    # ------------------------------------------------------------------
    # Privado — Cálculos
    # ------------------------------------------------------------------

    def _calculate_position(self, asset: Asset) -> PositionSummary:
        """Calcula a posição completa de um ativo a partir de suas operações."""
        ops = (
            self.db.query(InvestmentOperation)
            .filter(InvestmentOperation.asset_id == asset.id)
            .order_by(InvestmentOperation.date)
            .all()
        )

        quantity       = 0.0
        total_cost     = 0.0  # para cálculo de PM ponderado
        total_fees     = 0.0
        total_dividends = 0.0

        for op in ops:
            if op.operation_type == OperationType.BUY:
                total_cost += op.quantity * op.price_per_unit
                quantity   += op.quantity
                total_fees += op.fees

            elif op.operation_type == OperationType.SELL:
                if quantity > 0:
                    # Baixa proporcional do custo médio
                    avg = total_cost / quantity
                    total_cost -= avg * op.quantity
                quantity   -= op.quantity
                total_fees += op.fees

            elif op.operation_type == OperationType.SPLIT:
                # Desdobramento: ajusta quantidade sem alterar custo total
                # price_per_unit aqui é o fator (ex: 2.0 = split 2:1)
                quantity *= op.price_per_unit

            elif op.operation_type in (OperationType.DIVIDEND, OperationType.INTEREST):
                total_dividends += op.total_amount

        quantity   = round(max(quantity, 0.0), 6)
        avg_price  = round(total_cost / quantity, 4) if quantity > 0 else 0.0
        total_invested = round(quantity * avg_price, 2)

        return PositionSummary(
            asset_id=asset.id,
            ticker=asset.ticker,
            name=asset.name,
            asset_type=asset.asset_type.value,
            sector=asset.sector,
            quantity=quantity,
            avg_price=avg_price,
            total_invested=total_invested,
            total_fees=round(total_fees, 2),
            total_dividends=round(total_dividends, 2),
        )

    def _avg_price_until(self, asset_id: int, until_date: date) -> float:
        """
        Calcula o preço médio ponderado de compras até uma data específica.
        Usado no cálculo de ganho de capital para o IRPF.
        """
        ops = (
            self.db.query(InvestmentOperation)
            .filter(
                InvestmentOperation.asset_id == asset_id,
                InvestmentOperation.date <= until_date,
            )
            .order_by(InvestmentOperation.date)
            .all()
        )

        quantity   = 0.0
        total_cost = 0.0

        for op in ops:
            if op.operation_type == OperationType.BUY:
                total_cost += op.quantity * op.price_per_unit
                quantity   += op.quantity
            elif op.operation_type == OperationType.SELL:
                if quantity > 0:
                    avg = total_cost / quantity
                    total_cost -= avg * op.quantity
                quantity -= op.quantity
            elif op.operation_type == OperationType.SPLIT:
                quantity *= op.price_per_unit

        return round(total_cost / quantity, 4) if quantity > 0 else 0.0

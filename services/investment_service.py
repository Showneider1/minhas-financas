"""
Serviço de Investimentos — motor matemático rigoroso (P1).

Convenção de ledger (fonte: operações; posição é DERIVADA por replay, sem
tabela própria — evita divergência por escrita dupla):
- BUY:  custo += qty*price + fees;  qty += qty.  PM = custo / qty.
- SELL: exige qty_venda <= qty_atual (oversell → InsufficientPositionError).
        qty -= qty; custo -= PM_venda * qty_vendida (PM NÃO muda).
        P&L realizado = qty*(preço_venda − PM_venda) − taxas_venda.
- DIVIDEND/INTEREST: registra ganho (qty/PM intactos).
- SPLIT f: qty *= f (custo intacto; PM recalculado). f > 0.

Fórmula do PM (taxas no custo de aquisição):
    PM_novo = ((Qtd_ant × PM_ant) + (Qtd_nova × Preço_novo + Taxas)) / (Qtd_ant + Qtd_nova)

Tudo Decimal nativo (utils.money — float/bool rejeitados). Escala: 8 casas
(qty/preço/PM), 2 casas (totais BRL). Posse (user_id) e suficiência validadas.
Sem integração com frontend (P1 backend-only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import extract
from sqlalchemy.orm import Session

from config.logging_config import app_logger
from database.enums import AssetType, OperationType, TransactionType
from database.models.investment import Asset, InvestmentOperation
from utils.money import to_money2, to_qty8


class InsufficientPositionError(ValueError):
    """Venda sem saldo de cotas suficiente (oversell bloqueado)."""


class InsufficientFundsError(ValueError):
    """Compra sem saldo em conta para a liquidação (bloqueio anti-descoberto)."""


class InvestmentValidationError(ValueError):
    """Parâmetros inválidos para operação de investimento."""


Q8 = Decimal("0.00000001")
Q2 = Decimal("0.01")
ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Data-classes de resposta (Decimal; sem dependência de Pydantic ou ORM)
# ---------------------------------------------------------------------------


@dataclass
class InvestmentPosition:
    """Posição derivada de um ativo (replay do ledger)."""

    asset_id: int
    ticker: str
    name: str
    asset_type: str
    sector: str | None
    quantity: Decimal  # 8 casas
    avg_price: Decimal  # PM ponderado, 8 casas
    total_cost: Decimal  # custo carregado (8 casas)
    total_fees: Decimal  # 8 casas
    total_dividends: Decimal  # proventos acumulados (2 casas)
    realized_pnl: Decimal  # P&L realizado em vendas (2 casas)


# Alias de compatibilidade com callers legados (dashboard futuro).
PositionSummary = InvestmentPosition


@dataclass
class DividendSummary:
    """Resumo de dividendos/rendimentos de um ativo no período."""

    ticker: str
    name: str
    asset_type: str
    total: Decimal
    events: list[dict] = field(default_factory=list)


@dataclass
class IRPFLine:
    """Linha do demonstrativo de ganho de capital (IRPF)."""

    ticker: str
    name: str
    asset_type: str
    quantity_sold: Decimal
    avg_price: Decimal
    sale_price: Decimal
    gross_gain: Decimal
    fees: Decimal
    net_gain: Decimal
    sale_date: date


@dataclass
class SellResult:
    """Resultado de uma venda registrada."""

    operation_id: int
    quantity: Decimal
    sale_price: Decimal
    avg_price_at_sale: Decimal
    gross_gain: Decimal
    fees: Decimal
    net_gain: Decimal
    remaining_quantity: Decimal


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class InvestmentService:
    """Motor de carteira: registro validado + posição derivada."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Ativos
    # ------------------------------------------------------------------
    def register_asset(
        self,
        user_id: int,
        ticker: str,
        name: str,
        asset_type: AssetType,
        sector: str | None = None,
    ) -> Asset:
        """Cadastra ativo (idempotente por ticker+usuário)."""
        code = (ticker or "").strip().upper()
        if not code:
            raise InvestmentValidationError("Ticker é obrigatório.")
        if not (name or "").strip():
            raise InvestmentValidationError("Nome do ativo é obrigatório.")
        existing = (
            self.db.query(Asset).filter(Asset.user_id == user_id, Asset.ticker == code).first()
        )
        if existing:
            return existing
        asset = Asset(
            user_id=user_id,
            ticker=code,
            name=name.strip(),
            asset_type=asset_type,
            sector=(sector or "").strip() or None,
        )
        try:
            self.db.add(asset)
            self.db.commit()
            self.db.refresh(asset)
        except Exception:
            self.db.rollback()
            raise
        app_logger.info(f"Ativo cadastrado: {code} (usuário {user_id})")
        return asset

    def _owned_asset(self, asset_id: int, user_id: int) -> Asset:
        asset = self.db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == user_id).first()
        if not asset:
            raise InvestmentValidationError("Ativo não encontrado para este usuário.")
        return asset

    # ------------------------------------------------------------------
    # Operações
    # ------------------------------------------------------------------
    def buy(
        self,
        asset_id: int,
        user_id: int,
        quantity,
        price_per_unit,
        account_id: int,
        operation_date: date | None = None,
        fees=0,
        notes: str | None = None,
    ) -> InvestmentOperation:
        """Registra COMPRA com liquidação atômica no caixa.

        Debita `account_id` em (qty×price + fees). Sem saldo →
        InsufficientFundsError e NADA é persistido (operação + caixa
        no mesmo commit; rollback total em falha).
        """
        asset = self._owned_asset(asset_id, user_id)
        qty = to_qty8(quantity, where="invest.buy.qty")
        price = to_qty8(price_per_unit, where="invest.buy.price")
        fee = to_qty8(fees, where="invest.buy.fees")
        if qty <= 0:
            raise InvestmentValidationError("Quantidade da compra deve ser > 0.")
        if price < 0 or fee < 0:
            raise InvestmentValidationError("Preço/taxas não podem ser negativos.")
        account = self._owned_account(user_id, account_id)
        from services.balance_service import BalanceService

        settlement = to_money2(qty * price + fee, where="invest.buy.settle")
        available = BalanceService(self.db).get_account_balance(account.id, user_id)
        if settlement > available:
            raise InsufficientFundsError(
                f"Saldo insuficiente: liquidação {settlement} > saldo {available}."
            )
        try:
            op = self._build_op(
                asset,
                OperationType.BUY,
                operation_date or date.today(),
                qty,
                price,
                fee,
                (qty * price + fee).quantize(Q8),
                account.id,
                notes,
            )
            self._settle(
                user_id,
                account.id,
                op,
                kind="Compra",
                tx_type=TransactionType.EXPENSE,
                amount=settlement,
                op_date=operation_date or date.today(),
                ticker=asset.ticker,
            )
            self.db.commit()
            self.db.refresh(op)
        except Exception:
            self.db.rollback()
            raise
        return op

    def sell(
        self,
        asset_id: int,
        user_id: int,
        quantity,
        price_per_unit,
        account_id: int,
        operation_date: date | None = None,
        fees=0,
        notes: str | None = None,
    ) -> SellResult:
        """Registra VENDA com liquidação atômica (bloqueia oversell; PM não muda).

        Credita `account_id` em (qty×preço − taxas). Falha em qualquer ponto
        desfaz operação + caixa (rollback total).
        """
        asset = self._owned_asset(asset_id, user_id)
        qty = to_qty8(quantity, where="invest.sell.qty")
        price = to_qty8(price_per_unit, where="invest.sell.price")
        fee = to_qty8(fees, where="invest.sell.fees")
        if qty <= 0:
            raise InvestmentValidationError("Quantidade da venda deve ser > 0.")
        if price < 0 or fee < 0:
            raise InvestmentValidationError("Preço/taxas não podem ser negativos.")
        account = self._owned_account(user_id, account_id)

        pos = self.get_position(asset_id, user_id)
        if qty > pos.quantity:
            raise InsufficientPositionError(
                f"Venda de {qty} sem saldo: posição atual {pos.quantity} de {asset.ticker}."
            )
        gross = (qty * (price - pos.avg_price)).quantize(Q8)
        net = (gross - fee).quantize(Q2)
        settlement = to_money2(qty * price - fee, where="invest.sell.settle")
        try:
            op = self._build_op(
                asset,
                OperationType.SELL,
                operation_date or date.today(),
                qty,
                price,
                fee,
                (qty * price - fee).quantize(Q8),
                account.id,
                notes,
            )
            self._settle(
                user_id,
                account.id,
                op,
                kind="Venda",
                tx_type=TransactionType.INCOME,
                amount=settlement,
                op_date=operation_date or date.today(),
                ticker=asset.ticker,
            )
            self.db.commit()
            self.db.refresh(op)
        except Exception:
            self.db.rollback()
            raise
        app_logger.info(
            f"Venda {asset.ticker}: {qty} @ {price} (PM {pos.avg_price}) "
            f"P&L {net} (usuário {user_id})"
        )
        return SellResult(
            operation_id=op.id,
            quantity=qty,
            sale_price=price,
            avg_price_at_sale=pos.avg_price,
            gross_gain=gross,
            fees=fee,
            net_gain=net,
            remaining_quantity=(pos.quantity - qty).quantize(Q8),
        )

    def record_dividend(
        self,
        asset_id: int,
        user_id: int,
        amount,
        account_id: int,
        operation_date: date | None = None,
        kind: OperationType = OperationType.DIVIDEND,
        notes: str | None = None,
    ) -> InvestmentOperation:
        """Registra PROVENTO com crédito atômico (não altera qty nem PM)."""
        if kind not in (OperationType.DIVIDEND, OperationType.INTEREST):
            raise InvestmentValidationError("Tipo de provento inválido.")
        asset = self._owned_asset(asset_id, user_id)
        value = to_money2(amount, where="invest.dividend")
        if value <= 0:
            raise InvestmentValidationError("Provento deve ser > 0.")
        account = self._owned_account(user_id, account_id)
        try:
            op = self._build_op(
                asset,
                kind,
                operation_date or date.today(),
                ZERO,
                ZERO,
                ZERO,
                value,
                account.id,
                notes,
            )
            self._settle(
                user_id,
                account.id,
                op,
                kind="Dividendo" if kind == OperationType.DIVIDEND else "JCP",
                tx_type=TransactionType.INCOME,
                amount=value,
                op_date=operation_date or date.today(),
                ticker=asset.ticker,
            )
            self.db.commit()
            self.db.refresh(op)
        except Exception:
            self.db.rollback()
            raise
        return op

    def apply_split(
        self,
        asset_id: int,
        user_id: int,
        factor,
        operation_date: date | None = None,
        notes: str | None = None,
    ) -> InvestmentOperation:
        """Aplica DESDOBRAMENTO f:1 (qty ×= f, custo intacto, SEM caixa)."""
        asset = self._owned_asset(asset_id, user_id)
        f = to_qty8(factor, where="invest.split")
        if f <= 0:
            raise InvestmentValidationError("Fator do split deve ser > 0.")
        try:
            op = self._build_op(
                asset,
                OperationType.SPLIT,
                operation_date or date.today(),
                f,
                ZERO,
                ZERO,
                ZERO,
                None,
                notes or f"split {f}:1",
            )
            self.db.commit()
            self.db.refresh(op)
        except Exception:
            self.db.rollback()
            raise
        return op

    def void_operation(self, operation_id: int, user_id: int) -> bool:
        """Estorna operação de investimento + sua liquidação (atômico).

        Remove a operação E a Transaction vinculada, recalcula o saldo.
        Recusa se o replay sem a operação deixar posição negativa.
        """
        op = (
            self.db.query(InvestmentOperation)
            .join(Asset, Asset.id == InvestmentOperation.asset_id)
            .filter(
                InvestmentOperation.id == operation_id,
                Asset.user_id == user_id,
            )
            .first()
        )
        if not op:
            raise InvestmentValidationError("Operação não encontrada para este usuário.")
        try:
            tx_id = op.transaction_id
            account_id = op.account_id
            self.db.delete(op)
            self.db.flush()
            if tx_id:
                from database.models.transaction import Transaction

                tx = (
                    self.db.query(Transaction)
                    .filter(Transaction.id == tx_id, Transaction.user_id == user_id)
                    .first()
                )
                if tx:
                    account_id = account_id or tx.account_id
                    self.db.delete(tx)
                    self.db.flush()
            # Integridade do ledger restante: posição nunca negativa.
            pos = self.get_position(op.asset_id, user_id)
            if pos.quantity < 0:
                raise InvestmentValidationError("Estorno recusado: deixaria a posição negativa.")
            if account_id:
                from services.balance_service import BalanceService

                BalanceService(self.db).recalculate_and_persist(account_id, user_id)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        app_logger.info(f"Operação {operation_id} estornada (usuário {user_id})")
        return True

    # ------------------------------------------------------------------
    # Liquidação (interno — sem commit; o chamador confirma)
    # ------------------------------------------------------------------
    def _build_op(
        self,
        asset: Asset,
        op_type: OperationType,
        op_date: date,
        qty: Decimal,
        price: Decimal,
        fee: Decimal,
        total: Decimal,
        account_id: int | None,
        notes: str | None,
    ) -> InvestmentOperation:
        op = InvestmentOperation(
            asset_id=asset.id,
            account_id=account_id,
            operation_type=op_type,
            date=op_date,
            quantity=qty,
            price_per_unit=price,
            fees=fee,
            total_amount=total,
            notes=(notes or "")[:255] or None,
        )
        self.db.add(op)
        self.db.flush()
        return op

    def _settle(
        self,
        user_id: int,
        account_id: int,
        op: InvestmentOperation,
        kind: str,
        tx_type,
        amount: Decimal,
        op_date: date,
        ticker: str,
    ) -> None:
        """Cria a Transaction PAGA da liquidação e vincula (flush, sem commit)."""
        from database.models.transaction import Transaction, TransactionStatus

        category_id = self._ensure_cash_category(user_id, tx_type)
        tx = Transaction(
            user_id=user_id,
            description=f"{kind} {ticker} {op.quantity} × {op.price_per_unit}".strip()[:255],
            base_amount=amount,
            transaction_type=tx_type,
            account_id=account_id,
            category_id=category_id,
            purchase_date=op_date,
            due_date=op_date,
            paid_date=op_date,
            status=TransactionStatus.PAID,
            notes=f"liquidação investment_operation:{op.id}",
        )
        self.db.add(tx)
        self.db.flush()
        op.transaction_id = tx.id
        self.db.flush()
        from services.balance_service import BalanceService

        BalanceService(self.db).recalculate_and_persist(account_id, user_id)

    def _ensure_cash_category(self, user_id: int, tx_type) -> int:
        """Categoria do dono para liquidações (cria uma vez, idempotente)."""
        from database.models.category import Category

        name = "Investimentos" if tx_type.value == "EXPENSE" else "Proventos"
        cat = (
            self.db.query(Category)
            .filter(
                Category.user_id == user_id,
                Category.name == name,
                Category.transaction_type == tx_type,
            )
            .first()
        )
        if cat:
            return cat.id
        cat = Category(
            user_id=user_id,
            name=name,
            transaction_type=tx_type,
            icon="📈",
            color="#16a085",
            is_system=False,
        )
        self.db.add(cat)
        try:
            self.db.flush()
        except Exception:
            self.db.rollback()
            # Race ou legado: busca novamente (UNIQUE name+user).
            cat = (
                self.db.query(Category)
                .filter(Category.user_id == user_id, Category.name == name)
                .first()
            )
            if not cat:
                raise
        return cat.id

    def _owned_account(self, user_id: int, account_id: int):
        from database.models.account import Account

        if account_id is None:
            raise InvestmentValidationError(
                "Operação de investimento exige account_id (liquidação no caixa)."
            )
        account = (
            self.db.query(Account)
            .filter(Account.id == account_id, Account.user_id == user_id)
            .first()
        )
        if not account:
            raise InvestmentValidationError("Conta não pertence a este usuário.")
        if not account.is_active or getattr(account, "is_deleted", False):
            raise InvestmentValidationError("Conta inativa para liquidação.")
        return account

    # ------------------------------------------------------------------
    # Posição (replay do ledger)
    # ------------------------------------------------------------------
    def get_position(self, asset_id: int, user_id: int) -> InvestmentPosition:
        """Deriva a posição atual replayando as operações em ordem."""
        asset = self._owned_asset(asset_id, user_id)
        ops = (
            self.db.query(InvestmentOperation)
            .filter(InvestmentOperation.asset_id == asset.id)
            .order_by(InvestmentOperation.date.asc(), InvestmentOperation.id.asc())
            .all()
        )
        qty = ZERO
        cost = ZERO
        fees = ZERO
        dividends = ZERO
        realized = ZERO
        for op in ops:
            q = Decimal(str(op.quantity or 0))
            p = Decimal(str(op.price_per_unit or 0))
            f = Decimal(str(op.fees or 0))
            t = Decimal(str(op.total_amount or 0))
            if op.operation_type == OperationType.BUY:
                cost += q * p + f
                qty += q
                fees += f
            elif op.operation_type == OperationType.SELL:
                pm = (cost / qty) if qty > 0 else ZERO
                cost -= pm * q
                qty -= q
                fees += f
                realized += q * (p - pm) - f
            elif op.operation_type == OperationType.SPLIT:
                if q > 0:
                    qty *= q
            elif op.operation_type in (OperationType.DIVIDEND, OperationType.INTEREST):
                dividends += t
        avg = (cost / qty).quantize(Q8) if qty > 0 else ZERO
        return InvestmentPosition(
            asset_id=asset.id,
            ticker=asset.ticker,
            name=asset.name,
            asset_type=asset.asset_type.value,
            sector=asset.sector,
            quantity=qty.quantize(Q8),
            avg_price=avg,
            total_cost=cost.quantize(Q8),
            total_fees=fees.quantize(Q8),
            total_dividends=dividends.quantize(Q2),
            realized_pnl=realized.quantize(Q2),
        )

    def get_portfolio_position(self, user_id: int) -> list[InvestmentPosition]:
        """Posições com saldo (qty > 0), ordenadas por ticker."""
        assets = self.db.query(Asset).filter(Asset.user_id == user_id).all()
        positions = [self.get_position(a.id, user_id) for a in assets]
        return sorted((p for p in positions if p.quantity > 0), key=lambda p: p.ticker)

    def get_portfolio_summary_by_type(self, user_id: int) -> dict[str, Decimal]:
        """Custo carregado por tipo de ativo (NÃO é valor de mercado)."""
        summary: dict[str, Decimal] = {}
        for p in self.get_portfolio_position(user_id):
            summary[p.asset_type] = (summary.get(p.asset_type, ZERO) + p.total_cost).quantize(Q2)
        return summary

    # ------------------------------------------------------------------
    # Dividendos / IRPF
    # ------------------------------------------------------------------
    def get_dividend_history(self, user_id: int, year: int | None = None) -> list[DividendSummary]:
        """Histórico de proventos (Decimal exato)."""
        dividend_types = [OperationType.DIVIDEND, OperationType.INTEREST]
        summaries: list[DividendSummary] = []
        for asset in self.db.query(Asset).filter(Asset.user_id == user_id).all():
            q = self.db.query(InvestmentOperation).filter(
                InvestmentOperation.asset_id == asset.id,
                InvestmentOperation.operation_type.in_(dividend_types),
            )
            if year:
                q = q.filter(extract("year", InvestmentOperation.date) == year)
            ops = q.order_by(InvestmentOperation.date).all()
            if not ops:
                continue
            total = sum((Decimal(str(op.total_amount or 0)) for op in ops), ZERO).quantize(Q2)
            summaries.append(
                DividendSummary(
                    ticker=asset.ticker,
                    name=asset.name,
                    asset_type=asset.asset_type.value,
                    total=total,
                    events=[
                        {
                            "date": op.date.isoformat(),
                            "type": op.operation_type.value,
                            "amount": str(op.total_amount),
                        }
                        for op in ops
                    ],
                )
            )
        return sorted(summaries, key=lambda s: s.total, reverse=True)

    def get_irpf_report(self, user_id: int, year: int) -> list[IRPFLine]:
        """Ganho de capital por venda no ano (PM da data, taxas deduzidas)."""
        lines: list[IRPFLine] = []
        for asset in self.db.query(Asset).filter(Asset.user_id == user_id).all():
            sells = (
                self.db.query(InvestmentOperation)
                .filter(
                    InvestmentOperation.asset_id == asset.id,
                    InvestmentOperation.operation_type == OperationType.SELL,
                    extract("year", InvestmentOperation.date) == year,
                )
                .order_by(InvestmentOperation.date, InvestmentOperation.id)
                .all()
            )
            for sell in sells:
                avg = self._avg_price_until(asset.id, sell.date, sell.id)
                q = Decimal(str(sell.quantity or 0))
                p = Decimal(str(sell.price_per_unit or 0))
                f = Decimal(str(sell.fees or 0))
                gross = (q * (p - avg)).quantize(Q2)
                lines.append(
                    IRPFLine(
                        ticker=asset.ticker,
                        name=asset.name,
                        asset_type=asset.asset_type.value,
                        quantity_sold=q.quantize(Q8),
                        avg_price=avg.quantize(Q8),
                        sale_price=p.quantize(Q8),
                        gross_gain=gross,
                        fees=f.quantize(Q8),
                        net_gain=(gross - f).quantize(Q2),
                        sale_date=sell.date,
                    )
                )
        return sorted(lines, key=lambda l: l.sale_date)

    def _avg_price_until(self, asset_id: int, until_date: date, until_id: int) -> Decimal:
        """PM ponderado com taxas até (data, id) — replay parcial."""
        ops = (
            self.db.query(InvestmentOperation)
            .filter(
                InvestmentOperation.asset_id == asset_id,
                (InvestmentOperation.date < until_date)
                | ((InvestmentOperation.date == until_date) & (InvestmentOperation.id < until_id)),
            )
            .order_by(InvestmentOperation.date, InvestmentOperation.id)
            .all()
        )
        qty = ZERO
        cost = ZERO
        for op in ops:
            q = Decimal(str(op.quantity or 0))
            p = Decimal(str(op.price_per_unit or 0))
            f = Decimal(str(op.fees or 0))
            if op.operation_type == OperationType.BUY:
                cost += q * p + f
                qty += q
            elif op.operation_type == OperationType.SELL:
                if qty > 0:
                    cost -= (cost / qty) * q
                qty -= q
            elif op.operation_type == OperationType.SPLIT and q > 0:
                qty *= q
        return (cost / qty).quantize(Q8) if qty > 0 else ZERO

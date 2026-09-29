"""Serviço de Cartões de Crédito (P1).

Regras de domínio:
- Uma compra no crédito NÃO move saldo de conta corrente na data da compra.
- A compra consome limite do cartão e é alocada em uma fatura futura.
- O ciclo é definido pelo `closing_day`; o vencimento, pelo `due_day`.
- Compras parceladas geram N transações PENDENTES, uma por fatura.
- O somatório das parcelas é sempre igual ao valor original (Decimal).
"""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Iterable
from datetime import date
from decimal import ROUND_DOWN, Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from config.logging_config import app_logger
from database.enums import TransactionStatus, TransactionType
from database.models.account import Account, AccountType
from database.models.category import Category
from database.models.credit_card import CreditCard
from database.models.transaction import Transaction
from schemas.account_schema import AccountCreate
from services.account_service import AccountService
from utils.money import to_money2


class CreditCardError(ValueError):
    """Erro de domínio em operações de cartão de crédito."""


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


class CreditCardService:
    """Motor de cartão de crédito: limite, fatura e parcelamentos."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------
    def create_credit_card(
        self,
        *,
        user_id: int,
        name: str,
        credit_limit,
        closing_day: int,
        due_day: int,
        account_id: int | None = None,
    ) -> CreditCard:
        """Cria um cartão e, se necessário, a conta âncora do tipo CREDIT_CARD."""
        limit = to_money2(credit_limit, where="credit_card.create.limit")
        if limit <= ZERO:
            raise CreditCardError("Limite do cartão deve ser maior que zero.")
        if not (1 <= int(closing_day) <= 31):
            raise CreditCardError("Dia de fechamento deve estar entre 1 e 31.")
        if not (1 <= int(due_day) <= 31):
            raise CreditCardError("Dia de vencimento deve estar entre 1 e 31.")
        if not (name or "").strip():
            raise CreditCardError("Nome do cartão é obrigatório.")

        if account_id is None:
            account = AccountService(self.db).create_account(
                user_id,
                AccountCreate(
                    name=name.strip(),
                    account_type=AccountType.CREDIT_CARD,
                    initial_balance=Decimal("0.00"),
                    color="#e74c3c",
                    icon="bi-credit-card",
                    credit_limit=limit,
                    closing_day=int(closing_day),
                    due_day=int(due_day),
                ),
            )
            account_id = account.id
        else:
            account = self._owned_card_account(user_id, int(account_id))

        card = CreditCard(
            user_id=user_id,
            name=name.strip(),
            account_id=int(account_id),
            credit_limit=limit,
            closing_day=int(closing_day),
            due_day=int(due_day),
            is_active=True,
        )
        try:
            self.db.add(card)
            self.db.commit()
            self.db.refresh(card)
        except Exception:
            self.db.rollback()
            raise

        app_logger.info(
            f"Cartão criado: id={card.id} user_id={user_id} "
            f"limit={limit} closing={closing_day} due={due_day}"
        )
        return card

    # ------------------------------------------------------------------
    # Compras
    # ------------------------------------------------------------------
    def register_purchase(
        self,
        *,
        user_id: int,
        credit_card_id: int,
        amount,
        purchase_date: date,
        description: str,
        category_id: int,
        installments: int = 1,
    ) -> list[Transaction]:
        """Registra compra à vista ou parcelada no cartão.

        - Não altera saldo de contas correntes.
        - Gera uma transação PENDENTE por parcela/fatura.
        """
        card = self._owned_card(user_id, int(credit_card_id))
        if not card.is_active:
            raise CreditCardError("Cartão está inativo.")

        value = to_money2(amount, where="credit_card.purchase.amount")
        if value <= ZERO:
            raise CreditCardError("Valor da compra deve ser maior que zero.")

        if not isinstance(installments, int) or installments < 1:
            raise CreditCardError("Número de parcelas deve ser um inteiro maior ou igual a 1.")
        if installments > 48:
            raise CreditCardError("Máximo de 48 parcelas por compra.")

        if not (description or "").strip():
            raise CreditCardError("Descrição da compra é obrigatória.")

        category = self._owned_category(user_id, int(category_id))
        if category.transaction_type not in (None, TransactionType.EXPENSE):
            raise CreditCardError("Categoria de compra no cartão deve ser do tipo EXPENSE.")

        first_due_date = self._invoice_due_date(card, purchase_date)
        installment_values = self._split_installments(value, installments)

        transactions: list[Transaction] = []
        try:
            for index, installment_value in enumerate(installment_values, start=1):
                due_date = first_due_date + relativedelta(months=index - 1)
                transaction = Transaction(
                    user_id=user_id,
                    description=description.strip(),
                    base_amount=installment_value,
                    transaction_type=TransactionType.EXPENSE,
                    account_id=card.account_id,
                    category_id=category.id,
                    purchase_date=purchase_date,
                    due_date=due_date,
                    paid_date=None,
                    status=TransactionStatus.PENDING,
                    installment_number=index,
                    total_installments=installments,
                    credit_card_id=card.id,
                    notes=None,
                )
                self.db.add(transaction)
                transactions.append(transaction)

            self.db.commit()
            for transaction in transactions:
                self.db.refresh(transaction)
        except Exception:
            self.db.rollback()
            raise

        app_logger.info(
            f"Compra no cartão {card.id}: valor={value} parcelas={installments} "
            f"fatura_base={first_due_date.isoformat()} usuário={user_id}"
        )
        return transactions

    # ------------------------------------------------------------------
    # Limite
    # ------------------------------------------------------------------
    def get_available_limit(self, user_id: int, credit_card_id: int) -> Decimal:
        """Limite disponível = limite total − soma das compras não pagas."""
        card = self._owned_card(user_id, int(credit_card_id))

        used = to_money2(
            sum(
                (
                    Decimal(str(transaction.base_amount or 0))
                    for transaction in self._unpaid_card_transactions(card.id, user_id)
                ),
                ZERO,
            ),
            where="credit_card.limit.used",
        )

        available = to_money2(
            Decimal(str(card.credit_limit or 0)) - used,
            where="credit_card.limit.available",
        )
        if available < ZERO:
            return ZERO
        return available

    def _unpaid_card_transactions(self, credit_card_id: int, user_id: int) -> Iterable[Transaction]:
        return (
            self.db.query(Transaction)
            .filter(
                Transaction.credit_card_id == credit_card_id,
                Transaction.user_id == user_id,
                Transaction.status != TransactionStatus.CANCELLED,
                Transaction.paid_date.is_(None),
            )
            .all()
        )

    # ------------------------------------------------------------------
    # Fatura
    # ------------------------------------------------------------------
    def _invoice_due_date(self, card: CreditCard, purchase_date: date) -> date:
        """Determina a fatura da compra com base no dia de fechamento.

        Regra:
        - Compra ANTES do fechamento → fatura do mês corrente.
        - Compra NO DIA ou APÓS o fechamento → fatura do mês seguinte.
        - O vencimento usa o `due_day` da fatura correspondente.
        """
        if purchase_date.day < card.closing_day:
            closing_year = purchase_date.year
            closing_month = purchase_date.month
        else:
            next_month = purchase_date + relativedelta(months=1)
            closing_year = next_month.year
            closing_month = next_month.month

        closing_date = self._safe_date(closing_year, closing_month, card.closing_day)

        if card.due_day > card.closing_day:
            return self._safe_date(closing_year, closing_month, card.due_day)

        due_month = closing_date + relativedelta(months=1)
        return self._safe_date(due_month.year, due_month.month, card.due_day)

    @staticmethod
    def _safe_date(year: int, month: int, day: int) -> date:
        """Cria uma data válida, ajustando dias acima do último dia do mês."""
        last_day = monthrange(year, month)[1]
        return date(year, month, min(day, last_day))

    @staticmethod
    def _split_installments(total: Decimal, installments: int) -> list[Decimal]:
        """Divide o valor em parcelas com somatório exato.

        Estratégia:
        - Usa ROUND_DOWN para as primeiras N-1 parcelas.
        - A última parcela recebe o resíduo.
        """
        if installments == 1:
            return [to_money2(total, where="credit_card.split.single")]

        base = to_money2(
            (total / Decimal(installments)).quantize(CENT, rounding=ROUND_DOWN),
            where="credit_card.split.base",
        )
        values = [base for _ in range(installments - 1)]
        remainder = to_money2(
            total - (base * (installments - 1)),
            where="credit_card.split.remainder",
        )
        values.append(remainder)
        return values

    # ------------------------------------------------------------------
    # Validações de posse
    # ------------------------------------------------------------------
    def _owned_card(self, user_id: int, credit_card_id: int) -> CreditCard:
        card = (
            self.db.query(CreditCard)
            .filter(
                CreditCard.id == credit_card_id,
                CreditCard.user_id == user_id,
            )
            .first()
        )
        if not card:
            raise CreditCardError("Cartão não encontrado para este usuário.")
        return card

    def _owned_card_account(self, user_id: int, account_id: int) -> Account:
        account = (
            self.db.query(Account)
            .filter(
                Account.id == account_id,
                Account.user_id == user_id,
                Account.account_type == AccountType.CREDIT_CARD,
            )
            .first()
        )
        if not account:
            raise CreditCardError("Conta do cartão não encontrada para este usuário.")
        return account

    def _owned_category(self, user_id: int, category_id: int) -> Category:
        category = (
            self.db.query(Category)
            .filter(
                Category.id == category_id,
            )
            .first()
        )
        if not category or (category.user_id is not None and category.user_id != user_id):
            raise CreditCardError("Categoria não encontrada para este usuário.")
        return category

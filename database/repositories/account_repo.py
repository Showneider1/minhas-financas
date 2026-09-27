"""
Repository de contas — P0 (ADR-002).

- `Account.balance` é cache do BalanceService (único escritor). Este repo
  NÃO atribui saldo à mão; `recalculate_balance`/`get_total_balance` delegam.
- Acesso com dono: get_by_user_and_id / toggle_active_owned (anti-IDOR).
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from database.models.account import Account
from database.repositories.base_repo import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """
    Repository de contas financeiras.
    """

    def __init__(self, db: Session):
        super().__init__(Account, db)

    def get_by_user(
        self,
        user_id: int,
        include_inactive: bool = False,
    ) -> list[Account]:
        """
        Lista contas do usuário.

        Args:
            user_id: ID do usuário
            include_inactive: Se deve incluir contas inativas

        Returns:
            Lista de contas
        """
        query = self.db.query(Account).filter(
            Account.user_id == user_id, Account.is_deleted.is_(False)
        )

        if not include_inactive:
            query = query.filter(Account.is_active.is_(True))

        return query.order_by(Account.name).all()

    def get_by_user_and_id(
        self,
        user_id: int,
        account_id: int,
    ) -> Account | None:
        """
        Busca conta específica do usuário.

        Args:
            user_id: ID do usuário
            account_id: ID da conta

        Returns:
            Account ou None
        """
        return (
            self.db.query(Account)
            .filter(
                Account.id == account_id,
                Account.user_id == user_id,
                Account.is_deleted.is_(False),
            )
            .first()
        )

    def create_account(
        self,
        user_id: int,
        name: str,
        account_type: str,
        initial_balance=0,
        currency: str = "BRL",
    ) -> Account:
        """
        Cria nova conta.

        Args:
            user_id: ID do usuário
            name: Nome da conta
            account_type: Tipo da conta
            initial_balance: Saldo inicial (Decimal/str/int — nunca float)
            currency: Moeda

        Returns:
            Account criada
        """
        from utils.money import to_money2

        initial = to_money2(initial_balance, where="account_repo.create")
        return self.create(
            user_id=user_id,
            name=name,
            account_type=account_type,
            balance=initial,
            initial_balance=initial,
            currency=currency,
            is_active=True,
        )

    def recalculate_balance(self, account_id: int, user_id: int) -> Decimal | None:
        """Recalcula e persiste via BalanceService (único caminho)."""
        from services.balance_service import BalanceService

        try:
            return BalanceService(self.db).recalculate_and_persist(account_id, user_id)
        except LookupError:
            return None

    def get_total_balance(self, user_id: int) -> Decimal:
        """Patrimônio em contas — delega ao BalanceService (regra única)."""
        from services.balance_service import BalanceService

        return BalanceService(self.db).get_total_balance(user_id)

    def toggle_active(self, account_id: int, user_id: int) -> bool:
        """Alterna ativo/inativo apenas se a conta for do usuário (anti-IDOR)."""
        account = self.get_owned(account_id, user_id)
        if not account:
            return False

        account.is_active = not account.is_active
        self.db.flush()
        return True

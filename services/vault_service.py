"""
Serviço de Caixinhas (Virtual Vaults/Envelopes).

Caixinhas são divisões lógicas de reserva do patrimônio.
Elas NÃO geram transações reais - apenas reservam parte do saldo total.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from config.logging_config import app_logger
from database.models.vault import Vault
from services.balance_service import BalanceService
from utils.exceptions import ValidationError, VaultInsufficientFundsError
from utils.money import to_money2

ZERO = Decimal("0.00")


class VaultService:
    def __init__(self, db: Session):
        self.db = db

    def create_vault(
        self,
        user_id: int,
        name: str,
        target_amount: Any = 0,
        deadline=None,
        color: str | None = None,
    ) -> Vault:
        if not name or not name.strip():
            raise ValidationError("Nome da caixinha é obrigatório.")
        target = to_money2(target_amount or 0, where="vault.target")
        vault = Vault(
            user_id=user_id,
            name=name.strip(),
            target_amount=target,
            saved_amount=ZERO,
            deadline=deadline,
            color=color,
        )
        try:
            self.db.add(vault)
            self.db.commit()
            self.db.refresh(vault)
        except Exception:
            self.db.rollback()
            raise
        app_logger.info(f"Caixinha criada: {vault.name} (usuário {user_id})")
        return vault

    def get_vaults(self, user_id: int) -> list[Vault]:
        return (
            self.db.query(Vault)
            .filter(Vault.user_id == user_id)
            .order_by(Vault.created_at.asc(), Vault.id.asc())
            .all()
        )

    def get_total_vaults_balance(self, user_id: int) -> Decimal:
        total = (
            self.db.query(func.sum(Vault.saved_amount))
            .filter(Vault.user_id == user_id)
            .scalar()
        )
        return to_money2(total or 0, where="vault.total")

    def get_free_balance(self, user_id: int) -> Decimal:
        total_balance = BalanceService(self.db).get_total_balance(user_id)
        vaults_balance = self.get_total_vaults_balance(user_id)
        free = (total_balance - vaults_balance).quantize(Decimal("0.01"))
        return free

    def allocate_funds(self, vault_id: int, user_id: int, amount: Any) -> Vault:
        """Aloca dinheiro na caixinha (reserva lógica)."""
        amount_dec = to_money2(amount, where="vault.allocate")
        if amount_dec <= ZERO:
            raise ValidationError("Valor para guardar deve ser maior que zero.")

        vault = (
            self.db.query(Vault)
            .filter(Vault.id == vault_id, Vault.user_id == user_id)
            .first()
        )
        if not vault:
            raise ValidationError("Caixinha não encontrada para este usuário.")

        free_balance = self.get_free_balance(user_id)
        if amount_dec > free_balance:
            raise VaultInsufficientFundsError(
                f"Saldo livre insuficiente. Disponível: R$ {free_balance}"
            )

        vault.saved_amount = to_money2((vault.saved_amount or ZERO) + amount_dec, where="vault.save")
        try:
            self.db.commit()
            self.db.refresh(vault)
        except Exception:
            self.db.rollback()
            raise
        app_logger.info(f"Valor guardado na caixinha {vault.name}: R$ {amount_dec}")
        return vault

    def withdraw_funds(self, vault_id: int, user_id: int, amount: Any) -> Vault:
        """Resgata dinheiro da caixinha (libera reserva lógica)."""
        amount_dec = to_money2(amount, where="vault.withdraw")
        if amount_dec <= ZERO:
            raise ValidationError("Valor para resgatar deve ser maior que zero.")

        vault = (
            self.db.query(Vault)
            .filter(Vault.id == vault_id, Vault.user_id == user_id)
            .first()
        )
        if not vault:
            raise ValidationError("Caixinha não encontrada para este usuário.")

        current_saved = to_money2(vault.saved_amount or ZERO, where="vault.current")
        if amount_dec > current_saved:
            raise VaultInsufficientFundsError(
                f"Não é possível resgatar mais que o valor guardado. "
                f"Disponível na caixinha: R$ {current_saved}"
            )

        vault.saved_amount = to_money2(current_saved - amount_dec, where="vault.withdraw.save")
        try:
            self.db.commit()
            self.db.refresh(vault)
        except Exception:
            self.db.rollback()
            raise
        app_logger.info(f"Valor resgatado da caixinha {vault.name}: R$ {amount_dec}")
        return vault

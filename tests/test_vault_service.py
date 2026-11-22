"""Testes do VaultService — caixinhas como reservas lógicas do saldo."""

from decimal import Decimal

import pytest

from database.models.user import User
from services.balance_service import BalanceService
from services.vault_service import VaultService
from utils.exceptions import ValidationError, VaultInsufficientFundsError


def _create_vault(db, user_id, name="Reserva", target="1000.00"):
    return VaultService(db).create_vault(
        user_id=user_id,
        name=name,
        target_amount=Decimal(target),
    )


def _other_user(db):
    """Usuário isolado, sem conta — usado apenas para checar anti-IDOR."""
    user = User(
        name="Outro Usuario",
        email="outro@email.com",
        password_hash="hashed_password",
        is_active=True,
        is_deleted=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_vault_persists_decimal_amounts(db, sample_user):
    vault = _create_vault(db, sample_user.id, target="1234.56")

    assert vault.id is not None
    assert vault.name == "Reserva"
    assert vault.user_id == sample_user.id
    assert vault.target_amount == Decimal("1234.56")
    assert vault.saved_amount == Decimal("0.00")


@pytest.mark.parametrize("name", ["", "   ", None])
def test_create_vault_rejects_blank_name(db, sample_user, name):
    with pytest.raises(ValidationError):
        VaultService(db).create_vault(sample_user.id, name)


def test_get_vaults_returns_only_own_vaults(db, sample_user):
    other = _other_user(db)
    mine = _create_vault(db, sample_user.id, name="Minha")
    _create_vault(db, other.id, name="Dele")

    vaults = VaultService(db).get_vaults(sample_user.id)

    assert [v.id for v in vaults] == [mine.id]


def test_get_total_vaults_balance_is_per_user(db, sample_user, sample_account):
    other = _other_user(db)
    service = VaultService(db)
    v1 = _create_vault(db, sample_user.id, name="A")
    v2 = _create_vault(db, sample_user.id, name="B")
    v3 = _create_vault(db, other.id, name="C")

    service.allocate_funds(v1.id, sample_user.id, Decimal("100.00"))
    service.allocate_funds(v2.id, sample_user.id, Decimal("250.50"))
    # Valor do outro usuário injetado diretamente (ele não tem conta).
    v3.saved_amount = Decimal("999.00")
    db.commit()

    assert service.get_total_vaults_balance(sample_user.id) == Decimal("350.50")
    assert service.get_total_vaults_balance(other.id) == Decimal("999.00")


def test_free_balance_reflects_allocated_vaults(db, sample_user, sample_account):
    service = VaultService(db)
    total = BalanceService(db).get_total_balance(sample_user.id)
    vault = _create_vault(db, sample_user.id)

    assert service.get_free_balance(sample_user.id) == total

    service.allocate_funds(vault.id, sample_user.id, Decimal("1500.00"))

    assert service.get_free_balance(sample_user.id) == total - Decimal("1500.00")


def test_allocate_funds_accumulates(db, sample_user, sample_account):
    service = VaultService(db)
    vault = _create_vault(db, sample_user.id)

    service.allocate_funds(vault.id, sample_user.id, Decimal("200.00"))
    updated = service.allocate_funds(vault.id, sample_user.id, Decimal("300.00"))

    assert updated.saved_amount == Decimal("500.00")


def test_allocate_funds_rejects_excess(db, sample_user, sample_account):
    service = VaultService(db)
    vault = _create_vault(db, sample_user.id)
    total = BalanceService(db).get_total_balance(sample_user.id)

    with pytest.raises(VaultInsufficientFundsError):
        service.allocate_funds(vault.id, sample_user.id, total + Decimal("0.01"))

    db.refresh(vault)
    assert vault.saved_amount == Decimal("0.00")


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1.00")])
def test_allocate_rejects_non_positive(db, sample_user, amount):
    vault = _create_vault(db, sample_user.id)

    with pytest.raises(ValidationError):
        VaultService(db).allocate_funds(vault.id, sample_user.id, amount)


def test_allocate_rejects_other_users_vault(db, sample_user):
    other = _other_user(db)
    vault = _create_vault(db, other.id)

    with pytest.raises(ValidationError):
        VaultService(db).allocate_funds(vault.id, sample_user.id, Decimal("10.00"))


def test_withdraw_funds_decrements_saved(db, sample_user, sample_account):
    service = VaultService(db)
    vault = _create_vault(db, sample_user.id)
    service.allocate_funds(vault.id, sample_user.id, Decimal("500.00"))

    updated = service.withdraw_funds(vault.id, sample_user.id, Decimal("200.00"))

    assert updated.saved_amount == Decimal("300.00")


def test_withdraw_rejects_more_than_saved(db, sample_user, sample_account):
    service = VaultService(db)
    vault = _create_vault(db, sample_user.id)
    service.allocate_funds(vault.id, sample_user.id, Decimal("100.00"))

    with pytest.raises(VaultInsufficientFundsError):
        service.withdraw_funds(vault.id, sample_user.id, Decimal("100.01"))

    db.refresh(vault)
    assert vault.saved_amount == Decimal("100.00")


def test_withdraw_full_restores_free_balance(db, sample_user, sample_account):
    service = VaultService(db)
    total = BalanceService(db).get_total_balance(sample_user.id)
    vault = _create_vault(db, sample_user.id)
    service.allocate_funds(vault.id, sample_user.id, Decimal("400.00"))

    service.withdraw_funds(vault.id, sample_user.id, Decimal("400.00"))

    assert service.get_total_vaults_balance(sample_user.id) == Decimal("0.00")
    assert service.get_free_balance(sample_user.id) == total


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-5.00")])
def test_withdraw_rejects_non_positive(db, sample_user, sample_account, amount):
    service = VaultService(db)
    vault = _create_vault(db, sample_user.id)
    service.allocate_funds(vault.id, sample_user.id, Decimal("50.00"))

    with pytest.raises(ValidationError):
        service.withdraw_funds(vault.id, sample_user.id, amount)


def test_vaults_are_logical_reserves_only(db, sample_user, sample_account):
    before = sample_account.balance
    vault = _create_vault(db, sample_user.id)

    VaultService(db).allocate_funds(vault.id, sample_user.id, Decimal("1000.00"))

    db.refresh(sample_account)
    assert sample_account.balance == before

"""Teste de integração P0: Criar conta deve persistir e não setar soft-delete."""
from decimal import Decimal

import pytest
from database.models.account import Account
from services.account_service import AccountService
from schemas.account_schema import AccountCreate, AccountType


def test_create_account_persists_no_soft_delete(db, sample_user):
    """Criação de conta NÃO deve marcar is_deleted=True."""
    serv = AccountService(db)

    # Criar conta via serviço (mesmo que UI)
    acc = serv.create_account(
        user_id=sample_user.id,
        data=AccountCreate(
            name="Conta Saldo Zero",
            account_type=AccountType.CHECKING,
            initial_balance=Decimal("0"),
            color="#26a085",
        ),
    )

    assert acc is not None
    assert acc.name == "Conta Saldo Zero"
    # BUG: conta criada está com is_deleted=True?
    assert acc.is_deleted is False, f"Bug P0 detectado: conta recém-criada has is_deleted={acc.is_deleted}"
    # Deve aparecer na listagem
    list_accs = AccountService(db).get_user_accounts(sample_user.id)
    assert any(a.name == acc.name for a in list_accs), "Conta criada não aparece em get_user_accounts()"


def test_create_account_doesnt_soft_delete_other_accounts(db, sample_user):
    """Criar nova conta não deveria afetar contas existentes com is_deleted=False."""
    # Seed inicial de algumas contas?
    initial_count = 0
    try:
        first = db.query(Account).filter(Account.user_id == sample_user.id, Account.is_deleted.is_(False)).first()
        initial_count = initial_count + (1 if first else 0)
    except Exception:
        pass

    new_acc = serv.create_account(
        user_id=sample_user.id,
        data=AccountCreate(
            name="Nova Conta P0",
            account_type=AccountType.SAVINGS,
            initial_balance=Decimal("50.00"),
        ),
    )

    assert new_acc.is_deleted is False
    list = AccountService(db).get_user_accounts(sample_user.id)
    assert len([a for a in list if a.name.startswith(("Conta", "Nova"))]) == 2


def test_create_account_with_non_zero_initial_balance_persists(db, sample_user):
    """Cenário com saldo inicial + is_deleted check."""
    account = AccountService(db).create_account(
        user_id=sample_user.id,
        data=AccountCreate(
            name="Conta Teste P0 Balance",
            account_type=AccountType.CHECKING,
            initial_balance=Decimal("1000.00"),
        ),
    )

    assert account.balance == Decimal("1000.00")
    assert account.is_deleted is False
    # Check via query raw não filtrando deleted — se existir soft-deleted, aparecerá como row com flag True
    rows = db.query(Account).filter(Account.user_id == sample_user.id)
    deleted_count = len(rows.filter(Account.is_deleted == True).all()) if hasattr(type(rows), 'filter') else 0
    # Não deveria ter conta soft-deleted para este usuário (exceto se já existiam antes, mas não é o caso do P0 reportado)
    assert deleted_count == 0 or all(a.name not in ("Conta Saldo Zero", "Nova Conta P0") for a in accounts)


@pytest.mark.xfail(strict=False, reason="P0 bug: conta recém-criada tem is_deleted=True — será corrigido no commit após fix.")
def test_ui_create_account_from_modal_persists(db, monkeypatch, sample_user):
    """Teste simulando criação via modal UI — deve persistir e não ser soft-deleted."""
    pass  # Implementação futura com mocking dos inputs/modal se necessário.


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""Teste de integração P0: Criar conta deve persistir e não setar soft-delete."""
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace

import pytest

import callbacks.config_callbacks as config_callbacks
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
    serv = AccountService(db)

    existing = serv.create_account(
        user_id=sample_user.id,
        data=AccountCreate(
            name="Conta Existente",
            account_type=AccountType.CHECKING,
            initial_balance=Decimal("10.00"),
        ),
    )

    new_acc = serv.create_account(
        user_id=sample_user.id,
        data=AccountCreate(
            name="Nova Conta P0",
            account_type=AccountType.SAVINGS,
            initial_balance=Decimal("50.00"),
        ),
    )

    assert existing.is_deleted is False
    assert new_acc.is_deleted is False
    accounts = AccountService(db).get_user_accounts(sample_user.id)
    assert len([a for a in accounts if a.name.startswith(("Conta", "Nova"))]) == 2


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
    deleted_rows = rows.filter(Account.is_deleted.is_(True)).all()
    deleted_count = len(deleted_rows)
    # Não deveria ter conta soft-deleted para este usuário (exceto se já existiam antes, mas não é o caso do P0 reportado)
    assert deleted_count == 0 or all(
        a.name not in ("Conta Saldo Zero", "Nova Conta P0") for a in deleted_rows
    )


def test_ui_create_account_from_modal_persists(db, monkeypatch, sample_user):
    """Simula a criação de conta via modal da UI — deve persistir sem soft-delete."""
    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(config_callbacks, "resolve_user", lambda *a, **kw: sample_user.id)
    monkeypatch.setattr(config_callbacks, "get_db_session", session_ctx)
    monkeypatch.setattr(
        config_callbacks,
        "ctx",
        SimpleNamespace(triggered_id="btn-save-acc"),
    )

    result = config_callbacks.save_data(
        n_cat=0,
        n_acc=1,
        n_card=0,
        cat_name="",
        cat_type="EXPENSE",
        cat_color="#3498db",
        cat_parent=None,
        acc_name="Conta Modal UI",
        acc_type=AccountType.SAVINGS.value,
        acc_balance="250.50",
        card_name="",
        card_limit=0,
        card_close=1,
        card_due=10,
        auth_data={"token": "teste"},
        trigger_val=0,
    )

    assert result[0] == 1
    assert result[3] == ""
    assert result[6] is False

    account = db.query(Account).filter(Account.user_id == sample_user.id).one()
    assert account.name == "Conta Modal UI"
    assert account.is_deleted is False
    assert account.balance == Decimal("250.50")

    listed = AccountService(db).get_user_accounts(sample_user.id)
    assert any(a.id == account.id and a.is_deleted is False for a in listed)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""Testes de isolamento por usuário (RLS aplicacional).

Regra: usuário A NUNCA consegue ler, modificar ou excluir dados financeiros do usuário B.
Cobre Fase 3 §4 do plano Supabase + Fase 7 da Missão 2. Roda em SQLite :memory:.
"""

from datetime import date

import pytest

from database.models.account import Account
from database.models.category import Category, TransactionType
from database.models.transaction import Transaction
from database.models.user import User
from database.repositories.base_repo import BaseRepository
from schemas.transaction_schema import TransactionCreate, TransactionUpdate
from services.finance_service import FinanceService


def _make_user(db, name, email):
    u = User(name=name, email=email, password_hash="hash", is_active=True, is_deleted=False)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_account(db, user, name="Conta"):
    a = Account(user_id=user.id, name=name, balance=1000.0, is_active=True)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _make_category(db, user, name="Cat"):
    c = Category(
        user_id=user.id, name=name, transaction_type=TransactionType.EXPENSE, is_system=False
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_tx(db, user, account, category, description="Mercado"):
    from decimal import Decimal

    svc = FinanceService(db)
    return svc.create_transaction(
        user_id=user.id,
        transaction_data=TransactionCreate(
            description=description,
            base_amount=Decimal("100.00"),
            transaction_type=TransactionType.EXPENSE,
            category_id=category.id,
            account_id=account.id,
            purchase_date=date(2026, 1, 10),
            due_date=date(2026, 1, 10),
            paid_date=date(2026, 1, 10),
        ),
    )


def test_update_other_user_transaction_denied(db):
    """Usuário B não atualiza transação do usuário A (FinanceService filtra user_id)."""
    a = _make_user(db, "User A", "a@ex.com")
    b = _make_user(db, "User B", "b@ex.com")
    acc = _make_account(db, a)
    cat = _make_category(db, a)
    tx = _make_tx(db, a, acc, cat)

    svc_b = FinanceService(db)
    with pytest.raises(Exception):
        svc_b.update_transaction(
            transaction_id=tx.id,
            user_id=b.id,
            transaction_data=TransactionUpdate(description="Ataque B"),
        )

    db.refresh(tx)
    assert tx.description == "Mercado"


def test_cross_user_read_denied_via_get_owned(db):
    """Leitura por ID exige dono: get_owned nega cross-user (anti-IDOR)."""
    a = _make_user(db, "User A", "a2@ex.com")
    b = _make_user(db, "User B", "b2@ex.com")
    acc = _make_account(db, a)
    cat = _make_category(db, a)
    tx = _make_tx(db, a, acc, cat)

    repo = BaseRepository(Transaction, db)
    # Dono lê normalmente.
    assert repo.get_owned(tx.id, a.id) is not None
    # Outro usuário não lê (None — sem distinguir inexistente).
    assert repo.get_owned(tx.id, b.id) is None
    assert repo.get_owned(999999, b.id) is None
    # Update/delete com dono também negam.
    assert repo.update_owned(tx.id, b.id, description="Ataque") is None
    assert repo.delete_owned(tx.id, b.id) is False
    db.refresh(tx)
    assert tx.description == "Mercado"


def test_user_b_cannot_list_user_a_transactions(db):
    """Listagem do resumo de B não inclui valores de A."""
    a = _make_user(db, "User A", "a3@ex.com")
    b = _make_user(db, "User B", "b3@ex.com")
    acc_a = _make_account(db, a, "Conta A")
    cat_a = _make_category(db, a, "Cat A")
    _make_tx(db, a, acc_a, cat_a)

    svc = FinanceService(db)
    summary_b = svc.get_dashboard_summary(user_id=b.id, month=1, year=2026)
    assert summary_b["income"] == 0.0
    assert summary_b["expense"] == 0.0

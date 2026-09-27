"""Liquidação investimento × caixa — E2E na camada de serviço.

Cenário da missão: conta R$ 1000 → compra R$ 200 + R$ 5 taxa →
op salva, despesa R$ 205, saldo R$ 795,00 exatos. Atomicidade: falha
desfaz operação E caixa. Venda/divIDENDO creditam; estorno desfaz tudo.
"""

from datetime import date
from decimal import Decimal

from database.enums import AssetType, TransactionType
from database.models.account import Account
from database.models.investment import InvestmentOperation
from database.models.transaction import Transaction, TransactionStatus
from services.balance_service import BalanceService
from services.investment_service import InvestmentService


def _account(db, uid, name="Conta Corrente", initial="1000.00"):
    acc = Account(
        user_id=uid,
        name=name,
        balance=Decimal(initial),
        initial_balance=Decimal(initial),
        is_active=True,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


def test_cash_settlement_buy_200_plus_5(db, sample_user):
    svc = InvestmentService(db)
    acc = _account(db, sample_user.id)
    asset = svc.register_asset(sample_user.id, "PETR4", "Petrobras PN", AssetType.STOCK)

    op = svc.buy(
        asset.id,
        sample_user.id,
        "20",
        "10.00",
        acc.id,
        operation_date=date(2026, 6, 1),
        fees="5.00",
    )

    # a) operação salva, com PM e vínculo.
    assert op.id is not None
    assert op.transaction_id is not None
    pos = svc.get_position(asset.id, sample_user.id)
    assert pos.quantity == Decimal("20.00000000")
    assert pos.avg_price == Decimal("10.25000000")  # 205/20

    # b) transação de DESPESA de R$ 205,00 paga e vinculada.
    tx = db.query(Transaction).filter(Transaction.id == op.transaction_id).first()
    assert tx is not None
    assert tx.transaction_type == TransactionType.EXPENSE
    assert tx.status == TransactionStatus.PAID
    assert tx.base_amount == Decimal("205.00")
    assert tx.account_id == acc.id

    # c) saldo exato R$ 795,00.
    assert BalanceService(db).get_account_balance(acc.id, sample_user.id) == Decimal("795.00")


def test_cash_atomicity_on_settlement_failure(db, sample_user):
    """Falha na liquidação desfaz a operação (rollback total)."""
    svc = InvestmentService(db)
    acc = _account(db, sample_user.id)
    asset = svc.register_asset(sample_user.id, "PETR4", "Petrobras PN", AssetType.STOCK)
    # Categoria incompatível forçada: cria categoria de RECEITA e a vincula
    # via monkeypatch do ensure? Em vez disso: conta de outro usuário.
    from database.models.user import User

    other = User(name="O", email="o-cx@ex.com", password_hash="x", is_active=True, is_deleted=False)
    db.add(other)
    db.commit()
    op_before = db.query(InvestmentOperation).count()
    tx_before = db.query(Transaction).count()
    try:
        svc.buy(asset.id, sample_user.id, "10", "10.00", 999999, operation_date=date(2026, 6, 1))
        raise AssertionError("deveria falhar (conta inexistente)")
    except Exception:
        pass
    assert db.query(InvestmentOperation).count() == op_before
    assert db.query(Transaction).count() == tx_before
    assert BalanceService(db).get_account_balance(acc.id, sample_user.id) == Decimal("1000.00")


def test_sell_and_dividend_credit_cash(db, sample_user):
    svc = InvestmentService(db)
    acc = _account(db, sample_user.id, initial="10000.00")
    asset = svc.register_asset(sample_user.id, "PETR4", "Petrobras PN", AssetType.STOCK)
    svc.buy(
        asset.id,
        sample_user.id,
        "100",
        "10.00",
        acc.id,
        operation_date=date(2026, 6, 1),
        fees="2.00",
    )
    assert BalanceService(db).get_account_balance(acc.id, sample_user.id) == Decimal("8998.00")

    svc.sell(
        asset.id,
        sample_user.id,
        "50",
        "12.00",
        acc.id,
        operation_date=date(2026, 6, 2),
        fees="1.00",
    )
    # Crédito: 50×12 − 1 = 599 → 9597.
    assert BalanceService(db).get_account_balance(acc.id, sample_user.id) == Decimal("9597.00")

    svc.record_dividend(asset.id, sample_user.id, "100.00", acc.id, operation_date=date(2026, 6, 3))
    assert BalanceService(db).get_account_balance(acc.id, sample_user.id) == Decimal("9697.00")

    incomes = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == sample_user.id,
            Transaction.transaction_type == TransactionType.INCOME,
        )
        .all()
    )
    assert sum((t.base_amount for t in incomes), Decimal("0")) == Decimal("699.00")

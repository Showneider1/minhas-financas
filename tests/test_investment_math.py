"""Motor de investimentos — matemática rigorosa + liquidação no caixa.

Cenário obrigatório + bordas: PM ponderado com taxas, venda sem mover PM,
P&L realizado, oversell e saldo-insuficiente bloqueados, dividendos, split,
frações cripto, isolamento, estorno. Tudo Decimal nativo.

Toda operação (exceto SPLIT) exige `account_id` e liquida atomicamente:
operação + Transaction no mesmo commit; falha desfaz tudo.
"""
from datetime import date
from decimal import Decimal

import pytest

from database.enums import AssetType
from database.models.account import Account
from services.balance_service import BalanceService
from services.investment_service import (
    InsufficientFundsError,
    InsufficientPositionError,
    InvestmentService,
    InvestmentValidationError,
)


@pytest.fixture
def petr(db, sample_user):
    return InvestmentService(db).register_asset(
        user_id=sample_user.id, ticker="PETR4", name="Petrobras PN",
        asset_type=AssetType.STOCK, sector="Energia",
    )


@pytest.fixture
def broker(db, sample_user):
    acc = Account(user_id=sample_user.id, name="Corretora",
                  balance=Decimal("100000.00"),
                  initial_balance=Decimal("100000.00"), is_active=True)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


def _balance(db, uid, acc_id):
    return BalanceService(db).get_account_balance(acc_id, uid)


def test_mandatory_scenario_pm_with_fees(db, sample_user, petr, broker):
    """100×10,00+2,00 → PM 10,02; +50×12,00+1,00 → PM 1603/150."""
    svc = InvestmentService(db)
    svc.buy(petr.id, sample_user.id, "100", "10.00", broker.id,
            operation_date=date(2026, 1, 10), fees="2.00")
    pos = svc.get_position(petr.id, sample_user.id)
    assert pos.quantity == Decimal("100.00000000")
    assert pos.total_cost == Decimal("1002.00000000")
    assert pos.avg_price == Decimal("10.02000000")

    svc.buy(petr.id, sample_user.id, "50", "12.00", broker.id,
            operation_date=date(2026, 2, 10), fees="1.00")
    pos = svc.get_position(petr.id, sample_user.id)
    assert pos.quantity == Decimal("150.00000000")
    assert pos.total_cost == Decimal("1603.00000000")
    # Matemática exata: 1603/150 = 10.68666… → Q8.
    assert pos.avg_price == (Decimal("1603") / Decimal("150")).quantize(
        Decimal("0.00000001"))
    assert pos.avg_price == Decimal("10.68666667")
    # Caixa: 100000 − 1002 − 601.
    assert _balance(db, sample_user.id, broker.id) == Decimal("98397.00")


def test_sell_keeps_pm_reduces_qty_returns_pnl(db, sample_user, petr, broker):
    svc = InvestmentService(db)
    svc.buy(petr.id, sample_user.id, "100", "10.00", broker.id,
            operation_date=date(2026, 1, 10), fees="2.00")
    svc.buy(petr.id, sample_user.id, "50", "12.00", broker.id,
            operation_date=date(2026, 2, 10), fees="1.00")

    result = svc.sell(petr.id, sample_user.id, "50", "15.00", broker.id,
                      operation_date=date(2026, 3, 10), fees="0.50")
    assert result.remaining_quantity == Decimal("100.00000000")
    assert result.avg_price_at_sale == Decimal("10.68666667")
    # Bruto = 50 × (15 − 10.68666667) = 215.66666650; líquido −0.50 → 215.17.
    assert result.gross_gain == Decimal("215.66666650")
    assert result.net_gain == Decimal("215.17")

    pos = svc.get_position(petr.id, sample_user.id)
    assert pos.quantity == Decimal("100.00000000")
    assert pos.avg_price == Decimal("10.68666667")  # PM NÃO muda na venda
    assert pos.realized_pnl == Decimal("215.17")
    # Caixa: 98397 + (750 − 0.50).
    assert _balance(db, sample_user.id, broker.id) == Decimal("99146.50")


def test_oversell_blocked(db, sample_user, petr, broker):
    svc = InvestmentService(db)
    svc.buy(petr.id, sample_user.id, "100", "10.00", broker.id,
            operation_date=date(2026, 1, 10), fees="2.00")
    svc.sell(petr.id, sample_user.id, "50", "15.00", broker.id,
             operation_date=date(2026, 3, 10))
    with pytest.raises(InsufficientPositionError):
        svc.sell(petr.id, sample_user.id, "150", "15.00", broker.id,
                 operation_date=date(2026, 4, 10))
    # Posição intacta após tentativa bloqueada.
    assert svc.get_position(petr.id, sample_user.id).quantity == Decimal("50.00000000")


def test_short_sell_empty_position_blocked(db, sample_user, petr, broker):
    with pytest.raises(InsufficientPositionError):
        InvestmentService(db).sell(
            petr.id, sample_user.id, "1", "10.00", broker.id,
            operation_date=date(2026, 1, 10))


def test_insufficient_funds_blocked_nothing_persisted(
    db, sample_user, petr, sample_account
):
    """Compra acima do saldo: erro claro, sem ativo-operação e sem caixa."""
    from database.models.investment import InvestmentOperation
    from database.models.transaction import Transaction

    svc = InvestmentService(db)
    before = _balance(db, sample_user.id, sample_account.id)
    with pytest.raises(InsufficientFundsError):
        svc.buy(petr.id, sample_user.id, "1000", "10.00", sample_account.id,
                operation_date=date(2026, 1, 10), fees="2.00")
    assert db.query(InvestmentOperation).count() == 0
    assert db.query(Transaction).filter(
        Transaction.user_id == sample_user.id).count() == 0
    assert _balance(db, sample_user.id, sample_account.id) == before


def test_dividend_records_gain_only(db, sample_user, petr, broker):
    svc = InvestmentService(db)
    svc.buy(petr.id, sample_user.id, "100", "10.00", broker.id,
            operation_date=date(2026, 1, 10), fees="2.00")
    svc.record_dividend(petr.id, sample_user.id, "250.00", broker.id,
                        operation_date=date(2026, 4, 1))
    pos = svc.get_position(petr.id, sample_user.id)
    assert pos.quantity == Decimal("100.00000000")
    assert pos.avg_price == Decimal("10.02000000")
    assert pos.total_dividends == Decimal("250.00")
    assert pos.realized_pnl == Decimal("0.00")
    # Caixa: 100000 − 1002 + 250.
    assert _balance(db, sample_user.id, broker.id) == Decimal("99248.00")


def test_split_preserves_cost_halves_pm_no_cash(db, sample_user, petr, broker):
    svc = InvestmentService(db)
    op = svc.buy(petr.id, sample_user.id, "100", "10.00", broker.id,
                 operation_date=date(2026, 1, 10), fees="2.00")
    before = _balance(db, sample_user.id, broker.id)
    split = svc.apply_split(petr.id, sample_user.id, "2",
                            operation_date=date(2026, 5, 1))
    assert split.transaction_id is None  # split não liquida
    pos = svc.get_position(petr.id, sample_user.id)
    assert pos.quantity == Decimal("200.00000000")
    assert pos.total_cost == Decimal("1002.00000000")
    assert pos.avg_price == Decimal("5.01000000")
    assert _balance(db, sample_user.id, broker.id) == before
    assert op.transaction_id is not None  # a compra liquidou
    with pytest.raises(InvestmentValidationError):
        svc.apply_split(petr.id, sample_user.id, "0")


def test_void_reverses_operation_and_cash(db, sample_user, petr, broker):
    svc = InvestmentService(db)
    op = svc.buy(petr.id, sample_user.id, "100", "10.00", broker.id,
                 operation_date=date(2026, 1, 10), fees="2.00")
    assert svc.void_operation(op.id, sample_user.id) is True
    from database.models.investment import InvestmentOperation
    from database.models.transaction import Transaction

    assert db.query(InvestmentOperation).count() == 0
    assert db.query(Transaction).filter(
        Transaction.user_id == sample_user.id).count() == 0
    assert _balance(db, sample_user.id, broker.id) == Decimal("100000.00")
    assert svc.get_position(petr.id, sample_user.id).quantity == Decimal("0E-8")


def test_crypto_fractions_8dp(db, sample_user, broker):
    svc = InvestmentService(db)
    btc = svc.register_asset(user_id=sample_user.id, ticker="BTC",
                             name="Bitcoin", asset_type=AssetType.CRYPTO)
    svc.buy(btc.id, sample_user.id, "0.12345678", "300000.00", broker.id,
            operation_date=date(2026, 1, 10), fees="10.00")
    pos = svc.get_position(btc.id, sample_user.id)
    assert pos.quantity == Decimal("0.12345678")
    expected_cost = (Decimal("0.12345678") * Decimal("300000.00") + Decimal("10.00"))
    assert pos.total_cost == expected_cost.quantize(Decimal("0.00000001"))
    assert pos.avg_price == (expected_cost / Decimal("0.12345678")).quantize(
        Decimal("0.00000001"))


def test_float_rejected_and_validations(db, sample_user, petr, broker):
    svc = InvestmentService(db)
    with pytest.raises(TypeError):
        svc.buy(petr.id, sample_user.id, 100.0, "10.00", broker.id)
    with pytest.raises(InvestmentValidationError):
        svc.buy(petr.id, sample_user.id, "0", "10.00", broker.id)
    with pytest.raises(InvestmentValidationError):
        svc.buy(petr.id, sample_user.id, "-5", "10.00", broker.id)
    with pytest.raises(InvestmentValidationError):
        svc.record_dividend(petr.id, sample_user.id, "0.00", broker.id)
    with pytest.raises(InvestmentValidationError):
        svc.buy(petr.id, sample_user.id, "10", "10.00", None)


def test_cross_user_asset_denied(db, sample_user, petr, broker):
    from database.models.user import User

    other = User(name="Outro", email="outro-i@ex.com", password_hash="x",
                 is_active=True, is_deleted=False)
    db.add(other)
    db.commit()
    svc = InvestmentService(db)
    with pytest.raises(InvestmentValidationError):
        svc.buy(petr.id, other.id, "10", "10.00", broker.id)
    with pytest.raises(InvestmentValidationError):
        svc.get_position(petr.id, other.id)


def test_irpf_report_uses_pm_at_sale(db, sample_user, petr, broker):
    svc = InvestmentService(db)
    svc.buy(petr.id, sample_user.id, "100", "10.00", broker.id,
            operation_date=date(2026, 1, 10), fees="2.00")
    svc.sell(petr.id, sample_user.id, "50", "15.00", broker.id,
             operation_date=date(2026, 3, 10), fees="0.50")
    lines = svc.get_irpf_report(sample_user.id, 2026)
    assert len(lines) == 1
    assert lines[0].avg_price == Decimal("10.02000000")
    assert lines[0].gross_gain == Decimal("249.00")  # 50×(15−10.02)
    assert lines[0].net_gain == Decimal("248.50")


def test_register_asset_idempotent_and_owned(db, sample_user):
    svc = InvestmentService(db)
    a1 = svc.register_asset(sample_user.id, "petr4", "Petrobras PN", AssetType.STOCK)
    a2 = svc.register_asset(sample_user.id, "PETR4", "Outro Nome", AssetType.STOCK)
    assert a1.id == a2.id
    assert a1.ticker == "PETR4"

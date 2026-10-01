"""
Testes do motor de Rebalanceamento Buy & Hold.

O MarketDataService é SEMPRE mockado (rede nunca é tocada) — os preços vêm de
um dicionário local controlado por teste, garantindo reprodutibilidade da
matemática.
"""

from contextlib import contextmanager
from decimal import Decimal

import dash_bootstrap_components as dbc
import pytest

import callbacks.investimentos_callbacks as rebalance_callbacks
from database.enums import AssetType
from database.models.investment import Asset
from services.investment_rebalance_service import (
    InvestmentRebalanceService,
    RebalanceValidationError,
)
from services.investment_service import (
    InvestmentService,
    InvestmentValidationError,
)


class FakeMarketDataService:
    """Dublê determinístico do MarketDataService (sem rede)."""

    def __init__(self, prices: dict[str, str]):
        self.prices = {ticker: Decimal(price) for ticker, price in prices.items()}
        self.calls: list[str] = []

    def get_current_price(self, ticker: str, fallback_price=None):
        self.calls.append(ticker)
        return self.prices.get(ticker)


@pytest.fixture
def market():
    return FakeMarketDataService({})


def _register(db, user_id, ticker, target_pct):
    asset = InvestmentService(db).register_asset(
        user_id=user_id,
        ticker=ticker,
        name=f"Ativo {ticker}",
        asset_type=AssetType.STOCK,
    )
    if target_pct is not None:
        InvestmentService(db).set_target_allocation(user_id, asset.id, target_pct)
    return asset


def _buy(db, user_id, account_id, asset, qty, price):
    """Registra compra via serviço (possuí as mesmas liquidações do app real)."""
    return InvestmentService(db).buy(
        asset_id=asset.id,
        user_id=user_id,
        quantity=qty,
        price_per_unit=price,
        account_id=account_id,
        fees=0,
    )


# ─── Cenário fechado da missão ────────────────────────────────────────────────
def test_rebalance_plan_closed_scenario(db, sample_user, sample_account):
    """A: alvo 50%, preco 10, qtd 100 (1000). B: alvo 50%, preco 20, qtd 25 (500).
    Aporte 500 -> comprar 0 de A e 25 de B (custo 500), fechando 1000/1000.
    """
    asset_a = _register(db, sample_user.id, "ATIVOA", "50")
    asset_b = _register(db, sample_user.id, "ATIVOB", "50")

    _buy(db, sample_user.id, sample_account.id, asset_a, 100, "10")
    _buy(db, sample_user.id, sample_account.id, asset_b, 25, "20")

    market = FakeMarketDataService({"ATIVOA": "10", "ATIVOB": "20"})
    rebalance = InvestmentRebalanceService(db)

    plan = rebalance.calculate_rebalance_plan(
        sample_user.id,
        Decimal("500.00"),
        market_data_service=market,
    )
    by_ticker = {item["ticker"]: item for item in plan}

    # Ativo A ja esta no alvo: nenhuma compra (NO SELL RULE).
    assert by_ticker["ATIVOA"]["current_value"] == Decimal("1000.00")
    assert by_ticker["ATIVOA"]["current_pct"] == pytest.approx(66.67, abs=0.01)
    assert by_ticker["ATIVOA"]["deficit"] == Decimal("0.00")
    assert by_ticker["ATIVOA"]["recommended_buy_qty"] == 0
    assert by_ticker["ATIVOA"]["estimated_cost"] == Decimal("0.00")
    assert by_ticker["ATIVOA"]["action"] == "HOLD"

    # Ativo B recebe exatamente o aporte.
    assert by_ticker["ATIVOB"]["current_value"] == Decimal("500.00")
    assert by_ticker["ATIVOB"]["current_pct"] == pytest.approx(33.33, abs=0.01)
    assert by_ticker["ATIVOB"]["deficit"] == Decimal("500.00")
    assert by_ticker["ATIVOB"]["recommended_buy_qty"] == 25
    assert by_ticker["ATIVOB"]["estimated_cost"] == Decimal("500.00")
    assert by_ticker["ATIVOB"]["action"] == "BUY"

    # Resultado final: 1000 / 1000 exatos.
    final_a = by_ticker["ATIVOA"]["current_value"] + by_ticker["ATIVOA"]["estimated_cost"]
    final_b = by_ticker["ATIVOB"]["current_value"] + by_ticker["ATIVOB"]["estimated_cost"]
    assert final_a == Decimal("1000.00")
    assert final_b == Decimal("1000.00")

    summary = rebalance.get_plan_summary(plan, Decimal("500.00"))
    assert summary["total_estimated_cost"] == Decimal("500.00")
    assert summary["leftover_amount"] == Decimal("0.00")
    assert summary["assets_to_buy"] == 1


# ─── NO SELL RULE ─────────────────────────────────────────────────────────────
def test_overallocated_asset_never_gets_negative_quantity(db, sample_user, sample_account):
    """Ativo muito acima da meta recebe 0, nunca venda (quantidade negativa)."""
    _register(db, sample_user.id, "SUPERA", "10")
    _register(db, sample_user.id, "DEFICIT", "90")

    service = InvestmentService(db)
    superalloc = service.db.query(Asset).filter(Asset.ticker == "SUPERA").first()
    deficit = service.db.query(Asset).filter(Asset.ticker == "DEFICIT").first()

    _buy(db, sample_user.id, sample_account.id, superalloc, 200, "10")  # 2000
    _buy(db, sample_user.id, sample_account.id, deficit, 10, "10")  # 100

    market = FakeMarketDataService({"SUPERA": "10", "DEFICIT": "10"})
    plan = InvestmentRebalanceService(db).calculate_rebalance_plan(
        sample_user.id,
        Decimal("0.00"),
        market_data_service=market,
    )
    by_ticker = {item["ticker"]: item for item in plan}

    assert by_ticker["SUPERA"]["deficit"] == Decimal("0.00")
    assert by_ticker["SUPERA"]["recommended_buy_qty"] == 0
    assert by_ticker["SUPERA"]["action"] == "HOLD"
    assert all(item["recommended_buy_qty"] >= 0 for item in plan)
    assert all(item["action"] != "SELL" for item in plan)


def test_plan_is_read_only(db, sample_user, sample_account, market):
    """Calcular o plano não cria nem altera operações/ativos."""
    asset = _register(db, sample_user.id, "LEITURA", "50")
    _buy(db, sample_user.id, sample_account.id, asset, 10, "10")
    service = InvestmentService(db)
    before_ops = len(service.db.query(type(asset)).all())
    before_target = Decimal(asset.target_allocation_pct or 0)

    InvestmentRebalanceService(db).calculate_rebalance_plan(
        sample_user.id,
        Decimal("100.00"),
        market_data_service=market,
    )

    assert len(service.db.query(type(asset)).all()) == before_ops
    assert Decimal(asset.target_allocation_pct or 0) == before_target


# ─── Arredondamento conservador ───────────────────────────────────────────────
def test_quantity_is_floored_so_contribution_is_never_exceeded(db, sample_user, sample_account):
    """math.floor: aporte de 100 a preco 33 -> 3 cotas (99), sobra de 1."""
    _register(db, sample_user.id, "CARO", "100")
    asset = InvestmentService(db).db.query(Asset).filter(Asset.ticker == "CARO").first()
    _buy(db, sample_user.id, sample_account.id, asset, 1, "33")

    market = FakeMarketDataService({"CARO": "33"})
    rebalance = InvestmentRebalanceService(db)
    plan = rebalance.calculate_rebalance_plan(
        sample_user.id,
        Decimal("100.00"),
        market_data_service=market,
    )
    row = plan[0]

    # valor atual 33, novo patrimonio 133, alvo 133, deficit 100 -> floor(100/33) = 3
    assert row["deficit"] == Decimal("100.00")
    assert row["recommended_buy_qty"] == 3
    assert row["estimated_cost"] == Decimal("99.00")

    summary = rebalance.get_plan_summary(plan, Decimal("100.00"))
    assert summary["total_estimated_cost"] <= Decimal("100.00")
    assert summary["leftover_amount"] == Decimal("1.00")


def test_insufficient_contribution_leaves_money_unallocated(db, sample_user, sample_account):
    """Aporte nao compra o deficit inteiro: floor devolve a sobra ao investidor."""
    _register(db, sample_user.id, "ALVO", "100")
    asset = InvestmentService(db).db.query(Asset).filter(Asset.ticker == "ALVO").first()
    _buy(db, sample_user.id, sample_account.id, asset, 1, "10")  # 10 a mercado

    market = FakeMarketDataService({"ALVO": "10"})
    rebalance = InvestmentRebalanceService(db)
    # novo patrimonio 25 -> alvo 25 -> deficit 15; 15/10 = 1,5 -> floor = 1 cota.
    plan = rebalance.calculate_rebalance_plan(
        sample_user.id,
        Decimal("15.00"),
        market_data_service=market,
    )

    assert plan[0]["deficit"] == Decimal("15.00")
    assert plan[0]["recommended_buy_qty"] == 1
    assert plan[0]["estimated_cost"] == Decimal("10.00")

    summary = rebalance.get_plan_summary(plan, Decimal("15.00"))
    assert summary["total_estimated_cost"] == Decimal("10.00")
    assert summary["leftover_amount"] == Decimal("5.00")


# ─── Metas e limites ──────────────────────────────────────────────────────────
def test_asset_without_target_is_excluded(db, sample_user, sample_account):
    """Ativo com meta 0 e sem posição não aparece no plano."""
    _register(db, sample_user.id, "SEMMETA", "0")
    _register(db, sample_user.id, "COMMETA", "100")
    asset = InvestmentService(db).db.query(Asset).filter(Asset.ticker == "COMMETA").first()
    _buy(db, sample_user.id, sample_account.id, asset, 10, "10")

    market = FakeMarketDataService({"COMMETA": "10"})
    plan = InvestmentRebalanceService(db).calculate_rebalance_plan(
        sample_user.id,
        Decimal("0.00"),
        market_data_service=market,
    )
    tickers = [item["ticker"] for item in plan]
    assert "SEMMETA" not in tickers
    assert tickers == ["COMMETA"]


def test_target_with_zero_position_is_recommended_from_scratch(db, sample_user, sample_account):
    """Ativo com meta e sem posição entra no plano como compra do aporte."""
    _register(db, sample_user.id, "EXISTE", "50")
    _register(db, sample_user.id, "NOVO", "50")
    asset = InvestmentService(db).db.query(Asset).filter(Asset.ticker == "EXISTE").first()
    _buy(db, sample_user.id, sample_account.id, asset, 100, "10")  # 1000

    market = FakeMarketDataService({"EXISTE": "10", "NOVO": "20"})
    plan = InvestmentRebalanceService(db).calculate_rebalance_plan(
        sample_user.id,
        Decimal("1000.00"),
        market_data_service=market,
    )
    by_ticker = {item["ticker"]: item for item in plan}

    assert by_ticker["NOVO"]["current_value"] == Decimal("0.00")
    assert by_ticker["NOVO"]["quantity"] == Decimal("0")
    # novo patrimonio 2000, alvo do NOVO 1000, preco 20 -> 50 cotas
    assert by_ticker["NOVO"]["deficit"] == Decimal("1000.00")
    assert by_ticker["NOVO"]["recommended_buy_qty"] == 50
    assert by_ticker["NOVO"]["estimated_cost"] == Decimal("1000.00")


def test_total_recommended_cost_never_exceeds_contribution(db, sample_user, sample_account):
    """Metas somando menos de 100% nao geram compra acima do aporte."""
    a = _register(db, sample_user.id, "AAA", "30")
    b = _register(db, sample_user.id, "BBB", "30")
    _buy(db, sample_user.id, sample_account.id, a, 10, "10")
    _buy(db, sample_user.id, sample_account.id, b, 10, "10")

    market = FakeMarketDataService({"AAA": "10", "BBB": "10"})
    rebalance = InvestmentRebalanceService(db)
    for contribution in ("0.00", "13.00", "99.99", "1000.00"):
        plan = rebalance.calculate_rebalance_plan(
            sample_user.id,
            Decimal(contribution),
            market_data_service=market,
        )
        summary = rebalance.get_plan_summary(plan, Decimal(contribution))
        assert summary["total_estimated_cost"] <= Decimal(contribution)


def test_negative_contribution_is_rejected(db, sample_user, market):
    with pytest.raises(RebalanceValidationError):
        InvestmentRebalanceService(db).calculate_rebalance_plan(
            sample_user.id,
            Decimal("-1.00"),
            market_data_service=market,
        )


def test_empty_portfolio_returns_empty_plan(db, sample_user, market):
    plan = InvestmentRebalanceService(db).calculate_rebalance_plan(
        sample_user.id,
        Decimal("1000.00"),
        market_data_service=market,
    )
    assert plan == []


def test_price_lookups_use_market_data_service(db, sample_user, sample_account):
    """A valoração do plano consulta o MarketDataService para cada ativo."""
    _register(db, sample_user.id, "MKT", "100")
    asset = InvestmentService(db).db.query(Asset).filter(Asset.ticker == "MKT").first()
    _buy(db, sample_user.id, sample_account.id, asset, 10, "10")  # custo 100 a PM 10

    market = FakeMarketDataService({"MKT": "25"})  # appreciation de 150%
    plan = InvestmentRebalanceService(db).calculate_rebalance_plan(
        sample_user.id,
        Decimal("0.00"),
        market_data_service=market,
    )

    assert "MKT" in market.calls
    assert plan[0]["current_price"] == Decimal("25.00000000")
    assert plan[0]["current_value"] == Decimal("250.00")
    assert plan[0]["recommended_buy_qty"] == 0


# ─── Callbacks da UI (sem browser) ────────────────────────────────────────────
def _patch_rebalance_ui(monkeypatch, db, user_id, prices):
    """Substitui sessão, auth, rate limit e mercado nos callbacks de UI."""
    monkeypatch.setattr(rebalance_callbacks, "hit", lambda *a, **k: (True, None))
    monkeypatch.setattr(rebalance_callbacks, "client_ip", lambda: "127.0.0.1")

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(rebalance_callbacks, "get_db_session", session_ctx)
    monkeypatch.setattr(
        rebalance_callbacks,
        "resolve_user",
        lambda *a, **k: user_id,
    )
    monkeypatch.setattr(
        rebalance_callbacks,
        "MarketDataService",
        lambda _db: FakeMarketDataService(prices),
    )


def test_ui_plan_table_is_rendered_from_contribution(db, monkeypatch, sample_user, sample_account):
    """A digitação do aporte devolve a tabela de compras com o total."""
    asset_a = _register(db, sample_user.id, "UIA", "50")
    asset_b = _register(db, sample_user.id, "UIB", "50")
    _buy(db, sample_user.id, sample_account.id, asset_a, 100, "10")
    _buy(db, sample_user.id, sample_account.id, asset_b, 25, "20")

    _patch_rebalance_ui(monkeypatch, db, sample_user.id, {"UIA": "10", "UIB": "20"})

    table = rebalance_callbacks.recalc_rebalance_plan("500", {"token": "x"})

    assert isinstance(table, dbc.Table)
    flat = str(table)
    assert "UIB" in flat
    assert "R$ 500,00" in flat
    assert "Sobra" in flat


def test_ui_strategy_alert_warns_when_targets_incomplete(db, monkeypatch, sample_user):
    """Carteira com metas < 100% mostra alerta de estratégia incompleta."""
    _register(db, sample_user.id, "UIC", "40")
    _patch_rebalance_ui(monkeypatch, db, sample_user.id, {})

    alert, targets, _plan = rebalance_callbacks.load_rebalance_tab(
        {"token": "x"},
        None,
        "rebalance-tab",
        {"token": "x"},
    )

    assert isinstance(alert, dbc.Alert)
    assert alert.color == "warning"
    assert "faltam" in str(alert)
    assert "rebalance-target" in str(targets)


def test_ui_strategy_alert_succeeds_when_targets_total_100(db, monkeypatch, sample_user):
    _register(db, sample_user.id, "UID", "60")
    _register(db, sample_user.id, "UIE", "40")
    _patch_rebalance_ui(monkeypatch, db, sample_user.id, {})

    alert, _targets, _plan = rebalance_callbacks.load_rebalance_tab(
        {"token": "x"},
        None,
        "rebalance-tab",
        {"token": "x"},
    )

    assert alert.color == "success"
    assert "100,00%" in str(alert)


def test_ui_save_strategy_persists_targets_and_reports_total(db, monkeypatch, sample_user):
    asset_a = _register(db, sample_user.id, "UIF", None)
    asset_b = _register(db, sample_user.id, "UIG", None)
    _patch_rebalance_ui(monkeypatch, db, sample_user.id, {})

    feedback = rebalance_callbacks.save_rebalance_strategy(
        1,
        [
            {"id": {"type": "rebalance-target", "asset_id": asset_a.id}, "value": 60},
            {"id": {"type": "rebalance-target", "asset_id": asset_b.id}, "value": 40},
        ],
        {"token": "x"},
    )

    assert feedback.color == "success"
    db.expire_all()
    allocations = InvestmentService(db).get_target_allocations(sample_user.id)
    assert allocations["total_target_pct"] == Decimal("100.00")
    assert allocations["is_complete"] is True


def test_ui_save_strategy_rejects_sum_above_100(db, monkeypatch, sample_user):
    asset_a = _register(db, sample_user.id, "UIH", "70")
    asset_b = _register(db, sample_user.id, "UII", None)
    _patch_rebalance_ui(monkeypatch, db, sample_user.id, {})

    feedback = rebalance_callbacks.save_rebalance_strategy(
        1,
        [
            {"id": {"type": "rebalance-target", "asset_id": asset_a.id}, "value": 70},
            {"id": {"type": "rebalance-target", "asset_id": asset_b.id}, "value": 40},
        ],
        {"token": "x"},
    )

    assert feedback.color == "warning"
    db.expire_all()
    allocations = InvestmentService(db).get_target_allocations(sample_user.id)
    assert allocations["total_target_pct"] == Decimal("70.00")


def test_ui_recalc_rejects_negative_contribution(db, monkeypatch, sample_user):
    _patch_rebalance_ui(monkeypatch, db, sample_user.id, {})

    result = rebalance_callbacks.recalc_rebalance_plan("-10", {"token": "x"})

    assert isinstance(result, dbc.Alert)
    assert result.color == "warning"


# ─── Validação das metas (soma <= 100%) ───────────────────────────────────────
def test_target_sum_cannot_exceed_100(db, sample_user):
    service = InvestmentService(db)
    a = _register(db, sample_user.id, "A1", "60")
    _register(db, sample_user.id, "B1", "40")

    asset_b = service.db.query(Asset).filter(Asset.ticker == "B1").first()
    with pytest.raises(InvestmentValidationError):
        service.set_target_allocation(sample_user.id, asset_b.id, "50")
    with pytest.raises(InvestmentValidationError):
        service.set_target_allocation(sample_user.id, asset_b.id, "45")
    with pytest.raises(InvestmentValidationError):
        service.set_target_allocation(sample_user.id, a.id, "101")

    # Estado preservado após as recusas.
    assert Decimal(a.target_allocation_pct) == Decimal("60.00")
    assert Decimal(asset_b.target_allocation_pct) == Decimal("40.00")


def test_target_sum_replaces_own_value_on_edit(db, sample_user):
    """Editar o mesmo ativo duas vezes nao acumula (substitui, nao soma)."""
    service = InvestmentService(db)
    a = _register(db, sample_user.id, "A1", "40")
    b = _register(db, sample_user.id, "B1", "40")

    service.set_target_allocation(sample_user.id, a.id, "55")
    assert Decimal(a.target_allocation_pct) == Decimal("55.00")

    with pytest.raises(InvestmentValidationError):
        service.set_target_allocation(sample_user.id, b.id, "50")

    service.set_target_allocation(sample_user.id, b.id, "45")
    allocations = service.get_target_allocations(sample_user.id)
    assert allocations["total_target_pct"] == Decimal("100.00")
    assert allocations["is_complete"] is True


def test_negative_target_is_rejected(db, sample_user):
    asset = _register(db, sample_user.id, "NEG", "10")
    with pytest.raises(InvestmentValidationError):
        InvestmentService(db).set_target_allocation(sample_user.id, asset.id, "-1")


def test_overview_reports_incomplete_strategy(db, sample_user, sample_account):
    """Carteira com metas < 100% é sinalizada como estratégia incompleta."""
    _register(db, sample_user.id, "PARCIAL", "40")
    _register(db, sample_user.id, "ZERADO", "0")
    asset = InvestmentService(db).db.query(Asset).filter(Asset.ticker == "PARCIAL").first()
    _buy(db, sample_user.id, sample_account.id, asset, 10, "10")

    market = FakeMarketDataService({"PARCIAL": "10"})
    overview = InvestmentRebalanceService(db).get_rebalance_overview(
        sample_user.id,
        market_data_service=market,
    )

    assert overview["total_target_pct"] == Decimal("40.00")
    assert overview["is_complete"] is False
    assert overview["remaining_pct"] == Decimal("60.00")
    assert overview["total_current_value"] == Decimal("100.00")
    assert overview["position_count"] == 1

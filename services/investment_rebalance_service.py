"""
Serviço de Rebalanceamento Inteligente de Carteira (Buy & Hold).

REGRA RÍGIDA — NO SELL RULE:
    O rebalanceamento ocorre APENAS por novas compras. Um ativo superalocado
    (posição acima da meta) NUNCA gera quantidade negativa nem recomendação de
    venda: seu déficit é truncado em zero e o dinheiro que ele-curaria fica
    disponível para os ativos deficitários.

MATEMÁTICA:
    novo_patrimonio = valor_atual_a_mercado + aporte
    valor_alvo      = novo_patrimonio * (target_pct / 100)
    deficit         = valor_alvo - valor_atual_do_ativo
    qty_recomendada = math.floor(deficit / cotacao_atual)   # só se deficit > 0

O `math.floor` é deliberado: garante que a soma das recomendações nunca ultrapasse
o aporte disponível (arredondar para cima estouraria o caixa). O excedente fica
reportado em `leftover_amount` — investidor não precisa decidir sozinho o que
fazer com ele.

Fechamento do aporte: as recomendações são construídas por ordem de deficit
decrescente (maior necessidade primeiro) e cada uma só é aceita se couber no
saldo de aporte restante. Assim o total recommendations <= aporte sempre, mesmo
com metas que somam menos de 100%.

Read-only: nenhum dado é persistido. Decimal em todo o caminho monetário
(utils.money — float rejeitado na entrada).
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from config.logging_config import app_logger
from services.investment_service import InvestmentService
from utils.money import to_money2, to_qty8

ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")
Q2 = Decimal("0.01")


class RebalanceValidationError(ValueError):
    """Entrada inválida para o cálculo do plano de rebalanceamento."""


class InvestmentRebalanceService:
    """Calcula o plano de compras que reequilibra a carteira via aporte."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Plano principal
    # ------------------------------------------------------------------
    def calculate_rebalance_plan(
        self,
        user_id: int,
        contribution_amount,
        market_data_service=None,
    ) -> list[dict[str, Any]]:
        """Plano de compras do aporte, respeitando a No Sell Rule.

        Retorna lista de dicts ordenada por ticker:
            [{ticker, name, current_pct, target_pct, target_value,
              current_value, deficit, current_price, recommended_buy_qty,
              estimated_cost, action}, ...]

        `action` é "BUY" quando há compra sugerida e "HOLD" quando o ativo está
        no alvo ou superalocado (nunca "SELL").
        """
        contribution = to_money2(contribution_amount, where="rebalance.contribution")
        if contribution < ZERO:
            raise RebalanceValidationError("Aporte não pode ser negativo.")

        investments = InvestmentService(self.db)
        summary = investments.get_position_summary(
            user_id,
            market_data_service=market_data_service,
        )
        allocations = investments.get_target_allocations(user_id)

        positions_by_ticker = {p["ticker"]: p for p in summary["positions"]}
        current_total = to_money2(summary["total_current_value"], where="rebalance.current_total")

        # Ativos com metadefined entram mesmo sem posição (ainda não comprados).
        rows: list[dict[str, Any]] = []
        for item in allocations["items"]:
            position = positions_by_ticker.get(item["ticker"])
            target_pct = item["target_pct"]
            if target_pct <= ZERO and position is None:
                # Ativo sem meta e sem posição: irrelevante para o plano.
                continue
            rows.append(
                {
                    "ticker": item["ticker"],
                    "name": item["name"],
                    "target_pct": target_pct,
                    "current_value": (position["current_market_value"] if position else ZERO),
                    # Sem posição, a cotação vem direto do mercado: o plano
                    # precisa do preço para converter déficit em quantidade.
                    "current_price": (
                        position["current_price"]
                        if position
                        else self._price_for(market_data_service, item["ticker"])
                    ),
                    "quantity": position["quantity"] if position else ZERO,
                }
            )

        if not rows:
            return []

        new_total = (current_total + contribution).quantize(Q2)

        # 1) Calcula alvo e déficit por ativo (sem clamp de aporte ainda).
        for row in rows:
            row["current_pct"] = self._pct(row["current_value"], current_total)
            row["target_value"] = (new_total * row["target_pct"] / HUNDRED).quantize(Q2)
            row["deficit"] = (row["target_value"] - row["current_value"]).quantize(Q2)

        # 2) NO SELL RULE: déficit negativo (superalocado) -> 0, nunca venda.
        for row in rows:
            if row["deficit"] < ZERO:
                row["deficit"] = ZERO

        # 3) Fecha o aporte: maior deficit primeiro, respeitando o saldo
        #    restante. Garante Σ custo <= aporte mesmo com metas < 100%.
        buyable = [r for r in rows if r["deficit"] > ZERO and r["current_price"] > ZERO]
        remaining = contribution
        accepted: set[str] = set()
        for row in sorted(buyable, key=lambda r: (-r["deficit"], r["ticker"])):
            if row["deficit"] > remaining:
                continue
            qty = self._floor_quantity(row["deficit"], row["current_price"])
            cost = (Decimal(qty) * row["current_price"]).quantize(Q2)
            if qty <= 0 or cost > remaining:
                continue
            remaining -= cost
            row["recommended_buy_qty"] = qty
            row["estimated_cost"] = cost
            accepted.add(row["ticker"])

        plan: list[dict[str, Any]] = []
        for row in sorted(rows, key=lambda r: r["ticker"]):
            if row["ticker"] in accepted:
                qty = row["recommended_buy_qty"]
                cost = row["estimated_cost"]
                action = "BUY"
            else:
                qty = 0
                cost = ZERO
                action = "HOLD"
            plan.append(
                {
                    "ticker": row["ticker"],
                    "name": row["name"],
                    "current_pct": row["current_pct"],
                    "target_pct": row["target_pct"],
                    "target_value": row["target_value"],
                    "current_value": row["current_value"],
                    "deficit": row["deficit"],
                    "current_price": row["current_price"],
                    "quantity": row["quantity"],
                    "recommended_buy_qty": qty,
                    "estimated_cost": cost,
                    "action": action,
                }
            )
        return plan

    # ------------------------------------------------------------------
    # Resumo para a UI
    # ------------------------------------------------------------------
    def get_rebalance_overview(
        self,
        user_id: int,
        market_data_service=None,
    ) -> dict[str, Any]:
        """Contexto da estratégia: alvos, soma e totais de mercado."""
        investments = InvestmentService(self.db)
        allocations = investments.get_target_allocations(user_id)
        summary = investments.get_position_summary(
            user_id,
            market_data_service=market_data_service,
        )
        return {
            "total_target_pct": allocations["total_target_pct"],
            "is_complete": allocations["is_complete"],
            "remaining_pct": allocations["remaining_pct"],
            "targets": allocations["items"],
            "total_current_value": to_money2(
                summary["total_current_value"], where="rebalance.overview.total"
            ),
            "total_cost": to_money2(summary["total_cost"], where="rebalance.overview.cost"),
            "position_count": len(summary["positions"]),
        }

    def get_plan_summary(
        self,
        plan: list[dict[str, Any]],
        contribution_amount,
    ) -> dict[str, Any]:
        """Totais do plano: custo recomendado e sobra do aporte."""
        contribution = to_money2(contribution_amount, where="rebalance.summary.contribution")
        total_cost = to_money2(
            sum((Decimal(item["estimated_cost"]) for item in plan), ZERO),
            where="rebalance.summary.cost",
        )
        buys = [item for item in plan if item["action"] == "BUY"]
        return {
            "contribution": contribution,
            "total_estimated_cost": total_cost,
            "leftover_amount": (contribution - total_cost).quantize(Q2),
            "assets_to_buy": len(buys),
            "assets_on_target_or_over": len(plan) - len(buys),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _price_for(market_data_service, ticker: str) -> Decimal:
        """Cotação de um ativo sem posição (ZERO se indisponível).

        Sem preço não há conversão déficit -> quantidade, então o ativo fica
        fora das recomendações (visível na UI como "cotação indisponível").
        """
        if market_data_service is None:
            return ZERO
        try:
            price = market_data_service.get_current_price(ticker, fallback_price=None)
        except Exception as exc:  # noqa: BLE001
            app_logger.warning(f"Rebalance: cotação indisponível para {ticker}: {exc}")
            return ZERO
        if price is None:
            return ZERO
        return to_money2(price, where="rebalance.price.empty_position")

    @staticmethod
    def _pct(value: Decimal, total: Decimal) -> float:
        """Percentual que o ativo representa do total (float só na exibição)."""
        if total <= ZERO:
            return 0.0
        return float((value / total * HUNDRED).quantize(Q2))

    @staticmethod
    def _floor_quantity(deficit: Decimal, price: Decimal) -> int:
        """math.floor(deficit / preço) — arredondamento conservador.

        Garante qty * price <= deficit, então a compra nunca estoura o aporte.
        Sem cotação disponível (price <= 0) não há quantidade a calcular.
        """
        if price <= ZERO or deficit <= ZERO:
            return 0
        return int(math.floor(deficit / to_qty8(price, where="rebalance.price")))

    def log_plan(self, user_id: int, plan: list[dict[str, Any]]) -> None:
        """Log estruturado do plano gerado (diagnóstico)."""
        buys = [item["ticker"] for item in plan if item["action"] == "BUY"]
        resumo = ", ".join(buys) if buys else "nenhuma"
        app_logger.info(
            f"Plano de rebalanceamento (usuário {user_id}): {len(buys)} compra(s) — {resumo}"
        )

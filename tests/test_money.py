"""Precisão monetária — utils/money (Missão 2 Fase 3).

Regras: sem float, sem arredondamento intermediário, escala explícita,
soma/subtração/multiplicação/divisão e rateio exatos.
"""
from decimal import Decimal

import pytest

from utils.money import to_money2, to_qty4, split_money, money_sum, avg_price


def test_to_money2_quantizes_half_up():
    assert to_money2("10.005") == Decimal("10.01")
    assert to_money2("10.004") == Decimal("10.00")
    assert to_money2(10) == Decimal("10.00")
    assert to_money2(Decimal("0.1") + Decimal("0.2")) == Decimal("0.30")


def test_to_money2_rejects_float():
    with pytest.raises(TypeError):
        to_money2(0.1)
    with pytest.raises(TypeError):
        to_money2(100.0)


def test_float_classic_error_does_not_exist_in_decimal():
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
    assert to_money2(Decimal("0.1") + Decimal("0.2")) == Decimal("0.30")


def test_to_qty4_scale():
    assert to_qty4("1.23456") == Decimal("1.2346")
    with pytest.raises(TypeError):
        to_qty4(1.5)


def test_split_money_exact_cases():
    assert split_money("100.00", 3) == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    assert split_money("1200.00", 6) == [Decimal("200.00")] * 6
    assert split_money("10.00", 3) == [Decimal("3.34"), Decimal("3.33"), Decimal("3.33")]
    assert split_money("0.05", 2) == [Decimal("0.03"), Decimal("0.02")]


def test_split_money_sum_invariant_many():
    for total, n in [("1.00", 3), ("9999999.99", 7), ("0.01", 2), ("100.00", 1)]:
        parts = split_money(total, n)
        assert len(parts) == n
        assert sum(parts, Decimal("0.00")) == Decimal(total)


def test_split_money_rejects_invalid():
    with pytest.raises(ValueError):
        split_money("10.00", 0)
    with pytest.raises(ValueError):
        split_money("10.00", -2)
    with pytest.raises(TypeError):
        split_money(10.00, 2)


def test_money_sum_exact():
    assert money_sum([Decimal("0.10"), Decimal("0.20")]) == Decimal("0.30")
    assert money_sum([]) == Decimal("0.00")
    assert money_sum(["1.10", 2, Decimal("3.00")]) == Decimal("6.10")


def test_avg_price_weighted_and_guards():
    assert avg_price("1000.00", "10") == Decimal("100.0000")
    with pytest.raises(ValueError):
        avg_price("100.00", "0")
    with pytest.raises(ValueError):
        avg_price("100.00", "-5")

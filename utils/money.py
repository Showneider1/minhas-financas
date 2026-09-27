"""
Camada centralizada de operações monetárias (P0 — ADR-002).

Regras duras:
- Valores monetários são `Decimal`, nunca `float`, em todo caminho financeiro.
- Nenhuma conversão Decimal -> float durante cálculos.
- Sem arredondamentos intermediários: quantize apenas na borda (persistência/exibição).
- Escala explícita: Q2 (centavos, BRL) para dinheiro; Q4 para quantidades/preços.
- `float` é rejeitado na entrada (TypeError) para não reintroduzir erro binário
  silencioso — converta na borda com `Decimal(str(x))` se inevitável.

Compatibilidade SQLite/Postgres:
- Models usam `Numeric(12,2)` / `Numeric(14,4)` (mapeiam para NUMERIC no Postgres
  e NUMERIC affinity no SQLite; SQLAlchemy devolve Decimal nos dois).
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import List, Union

Q2 = Decimal("0.01")
Q4 = Decimal("0.0001")

MoneyLike = Union[Decimal, int, str]


def _coerce(value: MoneyLike, where: str) -> Decimal:
    """Converte entrada válida para Decimal. Rejeita float e bool explicitamente."""
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(
            f"{where}: float/bool não são aceitos em caminho monetário "
            f"(use Decimal/str/int). Valor recebido: {value!r}"
        )
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        clean = value.strip()
        if not clean:
            raise ValueError(f"{where}: valor monetário vazio")
        has_dot = "." in clean
        has_comma = "," in clean
        negative = clean.startswith("-")
        body = clean[1:] if negative else clean
        if has_dot and has_comma:
            # Só aceita milhar BR inequívoco: 1.234,56
            import re as _re

            if not _re.fullmatch(r"\d{1,3}(\.\d{3})+,\d{2}", body):
                raise ValueError(
                    f"{where}: formato ambíguo (use 1234.56 ou 1.234,56): {value!r}"
                )
            clean = body.replace(".", "").replace(",", ".")
        elif has_comma:
            clean = body.replace(",", ".")
        else:
            clean = body
        if negative:
            clean = "-" + clean
        try:
            return Decimal(clean)
        except InvalidOperation:
            raise ValueError(f"{where}: valor monetário inválido: {value!r}")
    raise TypeError(f"{where}: tipo não suportado: {type(value).__name__}")


def to_money2(value: MoneyLike, *, where: str = "to_money2") -> Decimal:
    """Normaliza para Decimal com 2 casas (ROUND_HALF_UP)."""
    return _coerce(value, where).quantize(Q2, rounding=ROUND_HALF_UP)


def to_qty4(value: MoneyLike, *, where: str = "to_qty4") -> Decimal:
    """Normaliza quantidade/preço para Decimal com 4 casas."""
    return _coerce(value, where).quantize(Q4, rounding=ROUND_HALF_UP)


def split_money(total: MoneyLike, n: int) -> List[Decimal]:
    """Rateia `total` em `n` parcelas Decimal somando exatamente o original.

    O resto de centavos vai para as PRIMEIRAS parcelas:
    R$ 100,00 / 3 -> [33.34, 33.33, 33.33].
    Levanta ValueError para n < 1.
    """
    if n < 1:
        raise ValueError("número de parcelas deve ser >= 1")
    total_d = to_money2(total, where="split_money")
    total_cents = int((total_d * 100).to_integral_value(rounding=ROUND_HALF_UP))
    sign = -1 if total_cents < 0 else 1
    total_cents = abs(total_cents)
    base, rem = divmod(total_cents, n)
    parts = [base + (1 if i < rem else 0) for i in range(n)]
    return [Decimal(sign * c) / 100 for c in parts]


def money_sum(values) -> Decimal:
    """Soma exata de valores (aceita Decimal/int/str; nunca float)."""
    total = Decimal("0.00")
    for v in values:
        total += _coerce(v, "money_sum") if not isinstance(v, Decimal) else v
    return total.quantize(Q2, rounding=ROUND_HALF_UP)


def avg_price(total_cost: MoneyLike, quantity: MoneyLike) -> Decimal:
    """Preço médio ponderado (4 casas). Levanta em quantidade <= 0 (sem mascarar oversell)."""
    cost = _coerce(total_cost, "avg_price")
    qty = _coerce(quantity, "avg_price")
    if qty <= 0:
        raise ValueError("quantidade deve ser > 0 para preço médio")
    return (cost / qty).quantize(Q4, rounding=ROUND_HALF_UP)

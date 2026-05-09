"""
Formatadores de dados para exibição.
"""
from datetime import date, datetime
from typing import Optional
import locale

# Tenta configurar locale brasileiro
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass  # Mantém locale padrão


def format_currency(
    value: float,
    currency: str = "BRL",
    show_symbol: bool = True,
) -> str:
    """
    Formata valor monetário para padrão brasileiro.
    
    Args:
        value: Valor numérico
        currency: Código da moeda (ISO 4217)
        show_symbol: Se deve mostrar símbolo da moeda
    
    Returns:
        String formatada (ex: "R$ 1.234,56")
    
    Examples:
        >>> format_currency(1234.56)
        'R$ 1.234,56'
        >>> format_currency(1234.56, show_symbol=False)
        '1.234,56'
    """
    if value is None:
        return "R$ 0,00" if show_symbol else "0,00"
    
    # Formata número
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    if show_symbol:
        symbols = {
            "BRL": "R$",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
        }
        symbol = symbols.get(currency, currency)
        return f"{symbol} {formatted}"
    
    return formatted


def format_percentage(
    value: float,
    decimals: int = 2,
    show_sign: bool = True,
) -> str:
    """
    Formata valor como percentual.
    
    Args:
        value: Valor numérico (ex: 0.1523 para 15.23%)
        decimals: Número de casas decimais
        show_sign: Se deve mostrar sinal de %
    
    Returns:
        String formatada (ex: "15,23%")
    
    Examples:
        >>> format_percentage(0.1523)
        '15,23%'
        >>> format_percentage(0.1523, decimals=1)
        '15,2%'
    """
    if value is None:
        return "0,00%"
    
    percent = value * 100
    formatted = f"{percent:.{decimals}f}".replace(".", ",")
    
    return f"{formatted}%" if show_sign else formatted


def format_date(
    value: Optional[date],
    format_str: str = "%d/%m/%Y",
) -> str:
    """
    Formata data para string.
    
    Args:
        value: Objeto date ou datetime
        format_str: Formato de saída
    
    Returns:
        String formatada ou "-" se None
    
    Examples:
        >>> format_date(date(2024, 1, 15))
        '15/01/2024'
    """
    if value is None:
        return "-"
    
    if isinstance(value, datetime):
        value = value.date()
    
    return value.strftime(format_str)


def format_datetime(
    value: Optional[datetime],
    format_str: str = "%d/%m/%Y %H:%M",
) -> str:
    """
    Formata datetime para string.
    
    Args:
        value: Objeto datetime
        format_str: Formato de saída
    
    Returns:
        String formatada ou "-" se None
    """
    if value is None:
        return "-"
    
    return value.strftime(format_str)


def format_number(
    value: float,
    decimals: int = 2,
) -> str:
    """
    Formata número com separadores brasileiros.
    
    Args:
        value: Valor numérico
        decimals: Casas decimais
    
    Returns:
        String formatada (ex: "1.234,56")
    """
    if value is None:
        return "0"
    
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Trunca texto longo adicionando reticências.
    
    Args:
        text: Texto a truncar
        max_length: Tamanho máximo
        suffix: Sufixo a adicionar
    
    Returns:
        Texto truncado
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

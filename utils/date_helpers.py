"""
Helpers para manipulação de datas e períodos.
"""
from datetime import date, datetime, timedelta
from typing import Tuple, Optional
from calendar import monthrange


def get_month_range(year: int, month: int) -> Tuple[date, date]:
    """
    Retorna primeiro e último dia do mês.
    
    Args:
        year: Ano
        month: Mês (1-12)
    
    Returns:
        Tupla (primeiro_dia, ultimo_dia)
    
    Examples:
        >>> get_month_range(2024, 1)
        (date(2024, 1, 1), date(2024, 1, 31))
    """
    first_day = date(year, month, 1)
    last_day_num = monthrange(year, month)[1]
    last_day = date(year, month, last_day_num)
    return first_day, last_day


def get_current_month_range() -> Tuple[date, date]:
    """
    Retorna primeiro e último dia do mês atual.
    
    Returns:
        Tupla (primeiro_dia, ultimo_dia)
    """
    today = date.today()
    return get_month_range(today.year, today.month)


def get_last_month_range() -> Tuple[date, date]:
    """
    Retorna primeiro e último dia do mês passado.
    
    Returns:
        Tupla (primeiro_dia, ultimo_dia)
    """
    today = date.today()
    first_day = (today.replace(day=1) - timedelta(days=1))
    return get_month_range(first_day.year, first_day.month)


def get_year_range(year: int) -> Tuple[date, date]:
    """
    Retorna primeiro e último dia do ano.
    
    Args:
        year: Ano
    
    Returns:
        Tupla (primeiro_dia, ultimo_dia)
    """
    return date(year, 1, 1), date(year, 12, 31)


def get_current_year_range() -> Tuple[date, date]:
    """
    Retorna primeiro e último dia do ano atual.
    
    Returns:
        Tupla (primeiro_dia, ultimo_dia)
    """
    today = date.today()
    return get_year_range(today.year)


def get_last_n_days(n: int, include_today: bool = True) -> Tuple[date, date]:
    """
    Retorna range dos últimos N dias.
    
    Args:
        n: Número de dias
        include_today: Se deve incluir hoje
    
    Returns:
        Tupla (data_inicial, data_final)
    
    Examples:
        >>> get_last_n_days(7)  # Últimos 7 dias incluindo hoje
        >>> get_last_n_days(30, include_today=False)  # Últimos 30 dias sem hoje
    """
    end_date = date.today()
    if not include_today:
        end_date = end_date - timedelta(days=1)
    
    start_date = end_date - timedelta(days=n - 1)
    return start_date, end_date


def parse_date_filter(filter_type: str) -> Tuple[date, date]:
    """
    Converte filtro textual em range de datas.
    
    Args:
        filter_type: Tipo de filtro (current_month, last_month, current_year, etc)
    
    Returns:
        Tupla (data_inicial, data_final)
    
    Examples:
        >>> parse_date_filter("current_month")
        >>> parse_date_filter("last_7_days")
    """
    filters = {
        "today": lambda: (date.today(), date.today()),
        "yesterday": lambda: (date.today() - timedelta(days=1), date.today() - timedelta(days=1)),
        "last_7_days": lambda: get_last_n_days(7),
        "last_15_days": lambda: get_last_n_days(15),
        "last_30_days": lambda: get_last_n_days(30),
        "current_month": get_current_month_range,
        "last_month": get_last_month_range,
        "current_year": get_current_year_range,
    }
    
    func = filters.get(filter_type)
    if not func:
        # Default: mês atual
        return get_current_month_range()
    
    return func()


def days_between(start: date, end: date) -> int:
    """
    Calcula número de dias entre duas datas.
    
    Args:
        start: Data inicial
        end: Data final
    
    Returns:
        Número de dias
    """
    return (end - start).days


def is_overdue(due_date: date, paid_date: Optional[date] = None) -> bool:
    """
    Verifica se uma data está atrasada.
    
    Args:
        due_date: Data de vencimento
        paid_date: Data de pagamento (None = não pago)
    
    Returns:
        True se atrasado, False caso contrário
    """
    if paid_date:
        return False  # Já foi pago
    
    return due_date < date.today()


def add_months(source_date: date, months: int) -> date:
    """
    Adiciona meses a uma data.
    
    Args:
        source_date: Data de origem
        months: Número de meses a adicionar (pode ser negativo)
    
    Returns:
        Nova data
    """
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, monthrange(year, month)[1])
    return date(year, month, day)

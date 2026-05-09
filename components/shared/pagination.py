"""
Componente de paginação reutilizável.
"""
import dash_bootstrap_components as dbc
from dash import html


def pagination_component(
    current_page: int,
    total_pages: int,
    component_id: str = "pagination",
    max_displayed: int = 5,
):
    """
    Componente de paginação com navegação.
    
    Args:
        current_page: Página atual (1-indexed)
        total_pages: Total de páginas
        component_id: ID do componente
        max_displayed: Máximo de páginas exibidas
    
    Returns:
        Component Dash
    """
    if total_pages <= 1:
        return html.Div()
    
    items = []
    
    # Botão anterior
    items.append(
        dbc.PaginationItem(
            "‹",
            id=f"{component_id}-prev",
            disabled=current_page == 1,
        )
    )
    
    # Calcula range de páginas a exibir
    start_page = max(1, current_page - max_displayed // 2)
    end_page = min(total_pages, start_page + max_displayed - 1)
    
    # Ajusta start se end estiver no limite
    if end_page == total_pages:
        start_page = max(1, end_page - max_displayed + 1)
    
    # Primeira página se não estiver no range
    if start_page > 1:
        items.append(
            dbc.PaginationItem(
                "1",
                id=f"{component_id}-page-1",
                active=False,
            )
        )
        if start_page > 2:
            items.append(dbc.PaginationItem("...", disabled=True))
    
    # Páginas do range
    for page in range(start_page, end_page + 1):
        items.append(
            dbc.PaginationItem(
                str(page),
                id=f"{component_id}-page-{page}",
                active=page == current_page,
            )
        )
    
    # Última página se não estiver no range
    if end_page < total_pages:
        if end_page < total_pages - 1:
            items.append(dbc.PaginationItem("...", disabled=True))
        items.append(
            dbc.PaginationItem(
                str(total_pages),
                id=f"{component_id}-page-{total_pages}",
                active=False,
            )
        )
    
    # Botão próximo
    items.append(
        dbc.PaginationItem(
            "›",
            id=f"{component_id}-next",
            disabled=current_page == total_pages,
        )
    )
    
    return dbc.Pagination(
        items,
        className="justify-content-center mt-4",
    )


def items_per_page_selector(
    component_id: str = "items-per-page",
    options: list = None,
    default: int = 50,
):
    """
    Seletor de itens por página.
    
    Args:
        component_id: ID do componente
        options: Lista de opções (default: [25, 50, 100])
        default: Valor padrão
    
    Returns:
        Component Dash
    """
    if options is None:
        options = [25, 50, 100, 200]
    
    return dbc.Row(
        [
            dbc.Col(
                html.Label("Itens por página:", className="me-2 mb-0"),
                width="auto",
                className="d-flex align-items-center",
            ),
            dbc.Col(
                dbc.Select(
                    id=component_id,
                    options=[{"label": str(opt), "value": opt} for opt in options],
                    value=default,
                    className="w-auto",
                ),
                width="auto",
            ),
        ],
        className="align-items-center",
    )

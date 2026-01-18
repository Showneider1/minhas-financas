"""
Exporta componentes compartilhados.
"""
from components.shared.cards import kpi_card
from components.shared.loading import (
    loading_spinner,
    skeleton_card,
    skeleton_table,
    skeleton_kpi,
    loading_overlay,
    empty_state,
)
from components.shared.error import (
    error_alert,
    success_toast,
    error_page_404,
    error_boundary,
    validation_feedback,
)
from components.shared.pagination import (
    pagination_component,
    items_per_page_selector,
)
from components.shared.charts import (
    line_chart,
    bar_chart,
    pie_chart,
    multi_line_chart,
    gauge_chart,
)

__all__ = [
    # Cards
    "kpi_card",
    # Loading
    "loading_spinner",
    "skeleton_card",
    "skeleton_table",
    "skeleton_kpi",
    "loading_overlay",
    "empty_state",
    # Error
    "error_alert",
    "success_toast",
    "error_page_404",
    "error_boundary",
    "validation_feedback",
    # Pagination
    "pagination_component",
    "items_per_page_selector",
    # Charts
    "line_chart",
    "bar_chart",
    "pie_chart",
    "multi_line_chart",
    "gauge_chart",
]

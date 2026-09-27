"""
Exporta componentes compartilhados.
"""

from components.shared.cards import kpi_card
from components.shared.charts import (
    bar_chart,
    gauge_chart,
    line_chart,
    multi_line_chart,
    pie_chart,
)
from components.shared.error import (
    error_alert,
    error_boundary,
    error_page_404,
    success_toast,
    validation_feedback,
)
from components.shared.loading import (
    empty_state,
    loading_overlay,
    loading_spinner,
    skeleton_card,
    skeleton_kpi,
    skeleton_table,
)
from components.shared.pagination import (
    items_per_page_selector,
    pagination_component,
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

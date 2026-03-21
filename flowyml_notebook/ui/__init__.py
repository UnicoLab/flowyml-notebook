"""Interactive widgets for FlowyML Notebook.

Provides reactive UI widgets (sliders, dropdowns, tables, charts)
that can be displayed in the notebook and trigger downstream
cell re-execution when their values change.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class WidgetType(str, Enum):
    """Available widget types."""

    SLIDER = "slider"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    TEXT_INPUT = "text_input"
    NUMBER_INPUT = "number_input"
    DATE_PICKER = "date_picker"
    FILE_UPLOAD = "file_upload"
    BUTTON = "button"
    TABLE = "table"
    CHART = "chart"
    DATAFRAME = "dataframe"
    JSON_VIEW = "json_view"
    IMAGE = "image"
    HTML = "html"
    PROGRESS = "progress"
    TABS = "tabs"


@dataclass
class Widget:
    """Base interactive widget.

    Widgets are reactive: when their value changes (e.g., user moves a slider),
    the change propagates through the reactive dependency graph, triggering
    re-execution of downstream cells.
    """

    widget_id: str = field(default_factory=lambda: f"w_{uuid.uuid4().hex[:8]}")
    widget_type: WidgetType = WidgetType.TEXT_INPUT
    label: str = ""
    value: Any = None
    config: dict[str, Any] = field(default_factory=dict)
    _on_change: Callable | None = field(default=None, repr=False)

    def set_value(self, new_value: Any) -> None:
        """Update the widget value and trigger change callback."""
        old_value = self.value
        self.value = new_value
        if self._on_change and old_value != new_value:
            self._on_change(new_value)

    def on_change(self, callback: Callable) -> Widget:
        """Register a callback for value changes."""
        self._on_change = callback
        return self

    def to_dict(self) -> dict:
        """Serialize for GUI rendering."""
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type.value,
            "label": self.label,
            "value": self.value,
            "config": self.config,
        }

    def _repr_html_(self) -> str:
        """IPython HTML representation for notebook rendering."""
        return f'<div class="fml-widget" data-widget=\'{json.dumps(self.to_dict())}\'></div>'

    def __repr__(self) -> str:
        return f"{self.widget_type.value}({self.label!r}, value={self.value!r})"


# --- Widget Factory Functions ---

def slider(
    min_val: float = 0,
    max_val: float = 100,
    value: float = 50,
    step: float = 1,
    label: str = "",
) -> Widget:
    """Create an interactive slider widget.

    Args:
        min_val: Minimum value.
        max_val: Maximum value.
        value: Initial value.
        step: Step increment.
        label: Display label.

    Returns:
        Widget bound to the slider value.
    """
    return Widget(
        widget_type=WidgetType.SLIDER,
        label=label,
        value=value,
        config={"min": min_val, "max": max_val, "step": step},
    )


def dropdown(
    options: list[str] | dict[str, Any],
    value: str | None = None,
    label: str = "",
    multi: bool = False,
) -> Widget:
    """Create a dropdown selector widget.

    Args:
        options: List of options or dict of {label: value}.
        value: Initial selected value.
        label: Display label.
        multi: Allow multiple selections.
    """
    opts = options if isinstance(options, dict) else {o: o for o in options}
    return Widget(
        widget_type=WidgetType.DROPDOWN,
        label=label,
        value=value or (list(opts.values())[0] if opts else None),
        config={"options": opts, "multi": multi},
    )


def checkbox(value: bool = False, label: str = "") -> Widget:
    """Create a checkbox widget."""
    return Widget(widget_type=WidgetType.CHECKBOX, label=label, value=value)


def text_input(value: str = "", label: str = "", placeholder: str = "") -> Widget:
    """Create a text input widget."""
    return Widget(
        widget_type=WidgetType.TEXT_INPUT,
        label=label,
        value=value,
        config={"placeholder": placeholder},
    )


def number_input(
    value: float = 0,
    min_val: float | None = None,
    max_val: float | None = None,
    step: float = 1,
    label: str = "",
) -> Widget:
    """Create a number input widget."""
    config: dict[str, Any] = {"step": step}
    if min_val is not None:
        config["min"] = min_val
    if max_val is not None:
        config["max"] = max_val
    return Widget(
        widget_type=WidgetType.NUMBER_INPUT, label=label, value=value, config=config
    )


def button(label: str = "Run", variant: str = "primary") -> Widget:
    """Create a button widget."""
    return Widget(
        widget_type=WidgetType.BUTTON,
        label=label,
        value=False,
        config={"variant": variant},
    )


def table(
    data: Any,
    columns: list[str] | None = None,
    page_size: int = 25,
    sortable: bool = True,
    filterable: bool = True,
    label: str = "",
) -> Widget:
    """Create an interactive data table widget.

    Args:
        data: DataFrame, list of dicts, or dict.
        columns: Column names to display.
        page_size: Rows per page.
        sortable: Enable column sorting.
        filterable: Enable column filtering.
    """
    # Convert data to serializable format
    rows = _normalize_table_data(data)
    cols = columns or (list(rows[0].keys()) if rows else [])

    return Widget(
        widget_type=WidgetType.TABLE,
        label=label,
        value={"rows": rows, "columns": cols},
        config={
            "page_size": page_size,
            "sortable": sortable,
            "filterable": filterable,
        },
    )


def chart(
    data: Any,
    x: str | None = None,
    y: str | list[str] | None = None,
    kind: str = "line",
    title: str = "",
    label: str = "",
) -> Widget:
    """Create a chart widget.

    Args:
        data: DataFrame or list of dicts.
        x: X-axis column.
        y: Y-axis column(s).
        kind: Chart type ('line', 'bar', 'scatter', 'area', 'pie', 'heatmap').
        title: Chart title.
    """
    rows = _normalize_table_data(data)
    y_cols = [y] if isinstance(y, str) else (y or [])

    return Widget(
        widget_type=WidgetType.CHART,
        label=label or title,
        value={"rows": rows, "x": x, "y": y_cols},
        config={"kind": kind, "title": title},
    )


def dataframe(data: Any, label: str = "") -> Widget:
    """Create an interactive DataFrame display widget."""
    rows = _normalize_table_data(data)
    columns = list(rows[0].keys()) if rows else []
    return Widget(
        widget_type=WidgetType.DATAFRAME,
        label=label,
        value={"rows": rows[:1000], "columns": columns, "total_rows": len(rows)},
    )


def json_view(data: Any, label: str = "", expanded: bool = True) -> Widget:
    """Create a JSON tree viewer widget."""
    return Widget(
        widget_type=WidgetType.JSON_VIEW,
        label=label,
        value=data,
        config={"expanded": expanded},
    )


def progress(value: float = 0, total: float = 100, label: str = "") -> Widget:
    """Create a progress bar widget."""
    return Widget(
        widget_type=WidgetType.PROGRESS,
        label=label,
        value=value,
        config={"total": total},
    )


def tabs(items: dict[str, Any], label: str = "") -> Widget:
    """Create a tabs widget for organized content."""
    return Widget(
        widget_type=WidgetType.TABS,
        label=label,
        value=items,
        config={"active_tab": list(items.keys())[0] if items else None},
    )


def _normalize_table_data(data: Any) -> list[dict]:
    """Convert various data formats to list of dicts."""
    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            return data
        return [{"value": item} for item in data]

    if isinstance(data, dict):
        return [{"key": k, "value": v} for k, v in data.items()]

    # Try pandas DataFrame
    try:
        import pandas as pd

        if isinstance(data, pd.DataFrame):
            return data.head(10000).to_dict("records")
    except ImportError:
        pass

    # Try numpy array
    try:
        import numpy as np

        if isinstance(data, np.ndarray):
            if data.ndim == 1:
                return [{"index": i, "value": float(v)} for i, v in enumerate(data)]
            elif data.ndim == 2:
                return [
                    {f"col_{j}": float(data[i, j]) for j in range(data.shape[1])}
                    for i in range(min(data.shape[0], 10000))
                ]
    except ImportError:
        pass

    return [{"value": str(data)}]

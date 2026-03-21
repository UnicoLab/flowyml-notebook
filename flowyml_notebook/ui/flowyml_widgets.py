"""FlowyML-specific widgets for ML pipeline visualization.

Specialized widgets that leverage FlowyML's data structures to provide
rich, interactive ML-specific visualizations directly in the notebook.
"""

from __future__ import annotations

from typing import Any

from flowyml_notebook.ui import Widget, WidgetType


class FlowyMLWidgetType(WidgetType):
    """Extended widget types specific to FlowyML."""

    PIPELINE_DAG = "pipeline_dag"
    METRICS_DASHBOARD = "metrics_dashboard"
    DRIFT_MONITOR = "drift_monitor"
    LEADERBOARD = "leaderboard"
    ASSET_BROWSER = "asset_browser"
    RUN_TIMELINE = "run_timeline"
    EXPERIMENT_COMPARE = "experiment_compare"
    MODEL_CARD = "model_card"
    CONFUSION_MATRIX = "confusion_matrix"
    FEATURE_IMPORTANCE = "feature_importance"


def pipeline_dag(pipeline: Any = None, run_id: str | None = None, label: str = "Pipeline DAG") -> Widget:
    """Create an interactive pipeline DAG visualization.

    Shows the pipeline step graph with status colors, execution times,
    and click-to-inspect for each step.

    Args:
        pipeline: FlowyML Pipeline object or pipeline data dict.
        run_id: Optional run ID to show execution status.
        label: Display label.
    """
    dag_data = _extract_dag_data(pipeline) if pipeline else {}

    return Widget(
        widget_type=WidgetType("pipeline_dag"),
        label=label,
        value=dag_data,
        config={"run_id": run_id, "interactive": True, "layout": "dagre"},
    )


def metrics_dashboard(
    metrics: dict[str, Any] | list[dict] | None = None,
    run_ids: list[str] | None = None,
    label: str = "Metrics",
) -> Widget:
    """Create a metrics dashboard with charts and KPI cards.

    Shows training/evaluation metrics with line charts, loss curves,
    accuracy/F1/precision/recall, and comparison across runs.

    Args:
        metrics: Dict of metric_name → values or list of metric records.
        run_ids: Run IDs to fetch metrics from server.
        label: Display label.
    """
    data = _normalize_metrics(metrics) if metrics else {}

    return Widget(
        widget_type=WidgetType("metrics_dashboard"),
        label=label,
        value=data,
        config={"run_ids": run_ids or [], "auto_refresh": True},
    )


def drift_monitor(
    reference_data: Any = None,
    current_data: Any = None,
    features: list[str] | None = None,
    label: str = "Data Drift",
) -> Widget:
    """Create a data drift monitoring visualization.

    Compares feature distributions between reference and current data,
    showing drift scores and distribution plots.

    Args:
        reference_data: Reference dataset (DataFrame or dict).
        current_data: Current dataset to check for drift.
        features: Feature columns to monitor.
        label: Display label.
    """
    drift_data = {}
    if reference_data is not None and current_data is not None:
        drift_data = _compute_drift_summary(reference_data, current_data, features)

    return Widget(
        widget_type=WidgetType("drift_monitor"),
        label=label,
        value=drift_data,
        config={"features": features or [], "threshold": 0.05},
    )


def leaderboard(
    experiments: list[dict] | None = None,
    metric_columns: list[str] | None = None,
    sort_by: str | None = None,
    label: str = "Model Leaderboard",
) -> Widget:
    """Create a model comparison leaderboard.

    Sortable table comparing model performance across experiments/runs
    with metric columns and highlighting for best values.

    Args:
        experiments: List of experiment result dicts.
        metric_columns: Columns to display.
        sort_by: Default sort column.
        label: Display label.
    """
    return Widget(
        widget_type=WidgetType("leaderboard"),
        label=label,
        value={"experiments": experiments or [], "columns": metric_columns or []},
        config={"sort_by": sort_by, "highlight_best": True},
    )


def asset_browser(
    assets: list[dict] | None = None,
    asset_type: str | None = None,
    label: str = "Asset Catalog",
) -> Widget:
    """Create an asset catalog browser with lineage graph.

    Browse datasets, models, metrics with version history
    and lineage relationships.

    Args:
        assets: List of asset data dicts.
        asset_type: Filter by type (dataset, model, metrics).
        label: Display label.
    """
    return Widget(
        widget_type=WidgetType("asset_browser"),
        label=label,
        value={"assets": assets or []},
        config={"asset_type": asset_type, "show_lineage": True},
    )


def run_timeline(
    runs: list[dict] | None = None,
    pipeline_name: str | None = None,
    label: str = "Run History",
) -> Widget:
    """Create a pipeline run timeline visualization.

    Shows execution history as a timeline with status colors,
    durations, and click-to-inspect for each run.

    Args:
        runs: List of run data dicts.
        pipeline_name: Filter runs by pipeline name.
        label: Display label.
    """
    return Widget(
        widget_type=WidgetType("run_timeline"),
        label=label,
        value={"runs": runs or []},
        config={"pipeline_name": pipeline_name, "max_runs": 100},
    )


def experiment_compare(
    experiments: list[dict] | None = None,
    metrics: list[str] | None = None,
    label: str = "Experiment Comparison",
) -> Widget:
    """Create side-by-side experiment comparison.

    Compare parameters, metrics, and artifacts across experiment runs
    with parallel coordinate plots and diff visualization.

    Args:
        experiments: Experiment data to compare.
        metrics: Metrics to highlight.
        label: Display label.
    """
    return Widget(
        widget_type=WidgetType("experiment_compare"),
        label=label,
        value={"experiments": experiments or [], "metrics": metrics or []},
        config={"show_params_diff": True, "chart_type": "parallel_coordinates"},
    )


def confusion_matrix(
    y_true: Any,
    y_pred: Any,
    labels: list[str] | None = None,
    label: str = "Confusion Matrix",
) -> Widget:
    """Create confusion matrix heatmap visualization.

    Args:
        y_true: True labels.
        y_pred: Predicted labels.
        labels: Class names.
        label: Display label.
    """
    matrix_data = _compute_confusion_matrix(y_true, y_pred, labels)
    return Widget(
        widget_type=WidgetType("confusion_matrix"),
        label=label,
        value=matrix_data,
        config={"normalize": True, "color_scale": "blues"},
    )


def feature_importance(
    features: list[str],
    importances: list[float],
    label: str = "Feature Importance",
) -> Widget:
    """Create feature importance bar chart.

    Args:
        features: Feature names.
        importances: Importance scores.
        label: Display label.
    """
    data = [
        {"feature": f, "importance": imp}
        for f, imp in sorted(zip(features, importances), key=lambda x: -x[1])
    ]
    return Widget(
        widget_type=WidgetType("feature_importance"),
        label=label,
        value=data,
        config={"top_k": 20, "horizontal": True},
    )


# --- Helper functions ---

def _extract_dag_data(pipeline: Any) -> dict:
    """Extract DAG data from a FlowyML Pipeline object."""
    try:
        if hasattr(pipeline, "steps"):
            nodes = []
            edges = []
            for step in pipeline.steps:
                name = getattr(step, "name", str(step))
                nodes.append({
                    "id": name,
                    "label": name,
                    "status": getattr(step, "status", "idle"),
                })
                for dep in getattr(step, "dependencies", []):
                    edges.append({"source": dep, "target": name})
            return {"nodes": nodes, "edges": edges}
    except Exception:
        pass
    return {"nodes": [], "edges": []}


def _normalize_metrics(metrics: dict | list) -> dict:
    """Normalize metrics into a standard format for visualization."""
    if isinstance(metrics, dict):
        return {
            "series": [
                {"name": k, "values": v if isinstance(v, list) else [v]}
                for k, v in metrics.items()
            ]
        }
    if isinstance(metrics, list):
        return {"records": metrics}
    return {}


def _compute_drift_summary(
    reference: Any, current: Any, features: list[str] | None
) -> dict:
    """Compute basic drift summary between datasets."""
    summary = {"features": [], "overall_drift": 0.0}
    try:
        import pandas as pd
        import numpy as np

        if isinstance(reference, pd.DataFrame) and isinstance(current, pd.DataFrame):
            cols = features or list(set(reference.columns) & set(current.columns))
            for col in cols[:50]:  # limit to 50 features
                if reference[col].dtype in [np.float64, np.int64, float, int]:
                    ref_mean = float(reference[col].mean())
                    cur_mean = float(current[col].mean())
                    ref_std = float(reference[col].std()) or 1.0
                    drift_score = abs(cur_mean - ref_mean) / ref_std
                    summary["features"].append({
                        "name": col,
                        "drift_score": round(drift_score, 4),
                        "ref_mean": round(ref_mean, 4),
                        "cur_mean": round(cur_mean, 4),
                        "drifted": drift_score > 0.5,
                    })
            if summary["features"]:
                summary["overall_drift"] = round(
                    sum(f["drift_score"] for f in summary["features"]) / len(summary["features"]), 4
                )
    except Exception:
        pass
    return summary


def _compute_confusion_matrix(y_true: Any, y_pred: Any, labels: list[str] | None) -> dict:
    """Compute confusion matrix data."""
    try:
        from collections import Counter

        # Get unique labels
        all_labels = labels or sorted(set(list(y_true) + list(y_pred)))
        label_to_idx = {label: i for i, label in enumerate(all_labels)}
        n = len(all_labels)
        matrix = [[0] * n for _ in range(n)]

        for t, p in zip(y_true, y_pred):
            if t in label_to_idx and p in label_to_idx:
                matrix[label_to_idx[t]][label_to_idx[p]] += 1

        return {
            "matrix": matrix,
            "labels": [str(l) for l in all_labels],
            "total": sum(sum(row) for row in matrix),
        }
    except Exception:
        return {"matrix": [], "labels": [], "total": 0}

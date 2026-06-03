"""Smart data validation and quality checks for notebook DataFrames.

Provides automatic data quality scoring, anomaly detection,
and validation rules that run transparently after each cell execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from flowyml_notebook.cells import CellOutput

logger = logging.getLogger(__name__)


@dataclass
class ColumnQuality:
    """Quality metrics for a single DataFrame column."""
    column: str
    dtype: str
    null_count: int = 0
    null_pct: float = 0.0
    unique_count: int = 0
    unique_pct: float = 0.0
    outlier_count: int = 0
    has_mixed_types: bool = False
    has_infinite: bool = False
    issues: list[str] = field(default_factory=list)
    score: float = 100.0  # 0-100 quality score

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "dtype": self.dtype,
            "null_count": self.null_count,
            "null_pct": round(self.null_pct, 2),
            "unique_count": self.unique_count,
            "unique_pct": round(self.unique_pct, 2),
            "outlier_count": self.outlier_count,
            "has_mixed_types": self.has_mixed_types,
            "has_infinite": self.has_infinite,
            "issues": self.issues,
            "score": round(self.score, 1),
        }


@dataclass
class DataQualityReport:
    """Complete data quality report for a DataFrame."""
    var_name: str
    cell_id: str
    shape: tuple[int, int] = (0, 0)
    overall_score: float = 100.0
    columns: list[ColumnQuality] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicate_rows: int = 0
    memory_mb: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "var_name": self.var_name,
            "cell_id": self.cell_id,
            "shape": list(self.shape),
            "overall_score": round(self.overall_score, 1),
            "columns": [c.to_dict() for c in self.columns],
            "warnings": self.warnings,
            "duplicate_rows": self.duplicate_rows,
            "memory_mb": round(self.memory_mb, 2),
            "timestamp": self.timestamp,
        }


class DataValidator:
    """Automatic data quality validation for DataFrames.

    Runs quality checks on DataFrames in the notebook namespace
    and generates reports with issues and quality scores.
    """

    def __init__(self):
        self._reports: dict[str, list[DataQualityReport]] = {}

    def validate(self, var_name: str, cell_id: str, df: Any) -> DataQualityReport:
        """Run quality checks on a DataFrame.

        Args:
            var_name: Variable name.
            cell_id: Cell that produced/modified the DataFrame.
            df: The DataFrame to validate.

        Returns:
            DataQualityReport with per-column scores and issues.
        """
        report = DataQualityReport(
            var_name=var_name,
            cell_id=cell_id,
        )

        try:
            report.shape = (int(df.shape[0]), int(df.shape[1]))
            report.memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

            # Check for duplicate rows
            try:
                report.duplicate_rows = int(df.duplicated().sum())
                if report.duplicate_rows > 0:
                    dup_pct = (report.duplicate_rows / max(1, len(df))) * 100
                    report.warnings.append(
                        f"{report.duplicate_rows} duplicate rows ({dup_pct:.1f}%)"
                    )
            except Exception:
                pass

            # Column-level quality
            import pandas as pd
            total_score = 0.0
            for col in df.columns:
                col_quality = self._validate_column(df, col)
                report.columns.append(col_quality)
                total_score += col_quality.score

            report.overall_score = total_score / max(1, len(report.columns))

            # Row count warnings
            if len(df) == 0:
                report.warnings.append("⚠ DataFrame is empty (0 rows)")
                report.overall_score = min(report.overall_score, 50.0)
            elif len(df) < 10:
                report.warnings.append(f"⚠ Very small dataset ({len(df)} rows)")

            # High memory usage warning
            if report.memory_mb > 500:
                report.warnings.append(
                    f"🔴 Very high memory: {report.memory_mb:.1f} MB — consider downcasting"
                )
            elif report.memory_mb > 100:
                report.warnings.append(
                    f"⚠ High memory usage: {report.memory_mb:.1f} MB"
                )

        except Exception as e:
            logger.debug(f"Data validation failed for {var_name}: {e}")
            report.warnings.append(f"Validation error: {e}")

        # Store report
        if var_name not in self._reports:
            self._reports[var_name] = []
        self._reports[var_name].append(report)

        return report

    def _validate_column(self, df: Any, col: str) -> ColumnQuality:
        """Validate a single column."""
        import pandas as pd

        series = df[col]
        quality = ColumnQuality(
            column=str(col),
            dtype=str(series.dtype),
        )

        total_rows = len(series)
        if total_rows == 0:
            return quality

        # Null analysis
        quality.null_count = int(series.isnull().sum())
        quality.null_pct = (quality.null_count / total_rows) * 100

        # Score deductions for nulls
        if quality.null_pct > 50:
            quality.score -= 40
            quality.issues.append(f"{quality.null_pct:.0f}% null — column mostly empty")
        elif quality.null_pct > 20:
            quality.score -= 20
            quality.issues.append(f"{quality.null_pct:.0f}% null — significant missing data")
        elif quality.null_pct > 5:
            quality.score -= 10
            quality.issues.append(f"{quality.null_pct:.0f}% null")

        # Uniqueness analysis
        try:
            quality.unique_count = int(series.nunique())
            quality.unique_pct = (quality.unique_count / total_rows) * 100

            if quality.unique_count == 1 and total_rows > 1:
                quality.score -= 15
                quality.issues.append("Constant column — only 1 unique value")
            elif quality.unique_count == total_rows and pd.api.types.is_object_dtype(series):
                quality.issues.append("All unique — possible ID column")
        except Exception:
            pass

        # Numeric column checks
        if pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()
            if len(non_null) > 0:
                # Infinite values
                try:
                    import numpy as np
                    inf_count = int(np.isinf(non_null).sum())
                    if inf_count > 0:
                        quality.has_infinite = True
                        quality.score -= 25
                        quality.issues.append(f"{inf_count} infinite values")
                except (ImportError, TypeError):
                    pass

                # Outlier detection using IQR
                try:
                    q1 = float(non_null.quantile(0.25))
                    q3 = float(non_null.quantile(0.75))
                    iqr = q3 - q1
                    if iqr > 0:
                        lower = q1 - 3.0 * iqr
                        upper = q3 + 3.0 * iqr
                        outliers = int(((non_null < lower) | (non_null > upper)).sum())
                        quality.outlier_count = outliers
                        if outliers > 0:
                            outlier_pct = (outliers / len(non_null)) * 100
                            if outlier_pct > 10:
                                quality.score -= 15
                                quality.issues.append(f"{outlier_pct:.1f}% outliers (IQR×3)")
                            elif outlier_pct > 1:
                                quality.score -= 5
                                quality.issues.append(f"{outlier_pct:.1f}% outliers")
                except Exception:
                    pass

        # Object/string column checks
        elif pd.api.types.is_object_dtype(series):
            # Check for mixed types
            try:
                non_null = series.dropna()
                if len(non_null) > 0:
                    types = non_null.apply(type).nunique()
                    if types > 1:
                        quality.has_mixed_types = True
                        quality.score -= 20
                        quality.issues.append("Mixed types in column")
            except Exception:
                pass

            # Check for leading/trailing whitespace
            try:
                str_vals = series.dropna().astype(str)
                whitespace = (str_vals != str_vals.str.strip()).sum()
                if whitespace > 0:
                    quality.score -= 5
                    quality.issues.append(f"{whitespace} values with leading/trailing whitespace")
            except Exception:
                pass

        quality.score = max(0.0, quality.score)
        return quality

    def validate_namespace(self, cell_id: str, namespace: dict) -> list[DataQualityReport]:
        """Validate all DataFrames in the namespace.

        Args:
            cell_id: The cell that was just executed.
            namespace: The execution namespace.

        Returns:
            List of quality reports for each DataFrame found.
        """
        reports = []
        for name, value in namespace.items():
            if name.startswith("_"):
                continue
            if type(value).__name__ == "DataFrame" and hasattr(value, "columns"):
                try:
                    report = self.validate(name, cell_id, value)
                    reports.append(report)
                except Exception as e:
                    logger.debug(f"Failed to validate {name}: {e}")
        return reports

    def get_reports(self, var_name: str) -> list[dict]:
        """Get all quality reports for a variable."""
        return [r.to_dict() for r in self._reports.get(var_name, [])]

    def get_latest_report(self, var_name: str) -> dict | None:
        """Get the most recent quality report for a variable."""
        reports = self._reports.get(var_name, [])
        return reports[-1].to_dict() if reports else None

    def clear(self) -> None:
        """Clear all stored reports."""
        self._reports.clear()


def format_quality_output(report: DataQualityReport) -> CellOutput:
    """Format a data quality report as rich HTML for the GUI."""
    # Score color
    if report.overall_score >= 80:
        score_color = "#22c55e"
        score_emoji = "✅"
    elif report.overall_score >= 60:
        score_color = "#eab308"
        score_emoji = "⚠️"
    else:
        score_color = "#ef4444"
        score_emoji = "🔴"

    # Score bar width
    bar_width = max(0, min(100, int(report.overall_score)))

    html_parts = [
        f'<div style="font-family:monospace;font-size:0.8rem;padding:12px;'
        f'background:#1e293b;border-radius:8px;border:1px solid rgba(255,255,255,0.06)">',
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">',
        f'<span style="color:#94a3b8;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.05em">'
        f'{score_emoji} Data Quality — {report.var_name} ({report.shape[0]:,}×{report.shape[1]})</span>',
        f'<span style="color:{score_color};font-weight:700;font-size:1.1rem">'
        f'{report.overall_score:.0f}/100</span></div>',
        # Score bar
        f'<div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px;margin-bottom:12px">',
        f'<div style="height:100%;width:{bar_width}%;background:{score_color};border-radius:2px"></div></div>',
    ]

    # Warnings
    if report.warnings:
        for w in report.warnings:
            html_parts.append(
                f'<div style="color:#fbbf24;font-size:0.75rem;margin-bottom:4px">{w}</div>'
            )
        html_parts.append('<div style="margin-bottom:8px"></div>')

    # Column issues (only show columns with issues)
    issue_cols = [c for c in report.columns if c.issues]
    if issue_cols:
        html_parts.append(
            '<table style="width:100%;border-collapse:collapse;font-size:0.75rem">'
            '<tr style="color:#94a3b8;border-bottom:1px solid rgba(255,255,255,0.06)">'
            '<th style="text-align:left;padding:4px">Column</th>'
            '<th style="text-align:center;padding:4px">Score</th>'
            '<th style="text-align:left;padding:4px">Issues</th></tr>'
        )
        for col in issue_cols[:10]:
            col_color = "#22c55e" if col.score >= 80 else "#eab308" if col.score >= 60 else "#ef4444"
            issues_str = "; ".join(col.issues[:3])
            html_parts.append(
                f'<tr style="border-bottom:1px solid rgba(255,255,255,0.03)">'
                f'<td style="padding:3px 4px;color:#e2e8f0">{col.column}</td>'
                f'<td style="text-align:center;padding:3px 4px;color:{col_color}">{col.score:.0f}</td>'
                f'<td style="padding:3px 4px;color:#94a3b8">{issues_str}</td></tr>'
            )
        html_parts.append('</table>')

    html_parts.append('</div>')

    return CellOutput(
        output_type="html",
        data="".join(html_parts),
        metadata={"data_quality": report.to_dict()},
    )

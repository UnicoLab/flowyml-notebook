"""FastAPI server for the FlowyML Notebook GUI.

Serves the browser-based notebook interface and provides:
- REST API for notebook CRUD and management
- WebSocket endpoint for real-time kernel communication
- Static file serving for the frontend build
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from flowyml_notebook.core import Notebook
from flowyml_notebook.kernel import NotebookKernel
from flowyml_notebook.cells import CellType
from flowyml_notebook.notebook_manager import NotebookManager
from flowyml_notebook.github_sync import GitHubSync
from flowyml_notebook.recipes_store import RecipeStore

logger = logging.getLogger(__name__)


# --- Pydantic Models ---

class CellCreate(BaseModel):
    source: str = ""
    cell_type: str = "code"
    name: str = ""
    index: int | None = None


class CellUpdate(BaseModel):
    source: str


class NotebookCreate(BaseModel):
    name: str = "untitled"
    server: str = ""


class ScheduleCreate(BaseModel):
    cron: str | None = None
    interval_hours: int | None = None
    pipeline_name: str | None = None


class ExportRequest(BaseModel):
    format: str = "pipeline"  # "pipeline", "html", "pdf", "docker"
    include_code: bool = False


class ReportRequest(BaseModel):
    title: str = ""
    format: str = "html"  # "html" or "pdf"
    include_code: bool = False


class AppPublishRequest(BaseModel):
    title: str = ""
    layout: str = "linear"  # linear, grid, tabs, sidebar, dashboard
    theme: str = "dark"
    show_code: bool = False
    grid_columns: int = 2
    cell_visibility: dict = {}  # cell_id → bool


class WidgetUpdate(BaseModel):
    widget_id: str
    value: Any = None


# --- Server ---

class NotebookServer:
    """Main server for the FlowyML Notebook GUI."""

    def __init__(self, notebook: Notebook | None = None, port: int = 8888):
        self.notebook = notebook or Notebook()
        self.kernel = NotebookKernel(self.notebook)
        self.port = port
        self.nb_manager = NotebookManager()
        self.github_sync = GitHubSync()
        self.recipe_store = RecipeStore()
        self.current_nb_id: str | None = None  # Track currently loaded notebook
        self._connection_config: dict = {}  # FlowyML connection config
        self._ai_config: dict = self._load_ai_config()  # AI provider config
        self._comments: list[dict] = []  # In-memory comments store
        self._reviews: list[dict] = []  # In-memory reviews store
        self.app = self._create_app()

    @staticmethod
    def _load_ai_config() -> dict:
        """Load AI provider config from disk."""
        config_file = Path.home() / ".flowyml" / "ai_config.json"
        if config_file.exists():
            try:
                return json.loads(config_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "provider": "openai",
            "model": "",
            "api_key": "",
            "base_url": "",
            "temperature": 0.3,
        }

    def _save_ai_config(self) -> None:
        """Persist AI provider config to disk."""
        config_file = Path.home() / ".flowyml" / "ai_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(self._ai_config, indent=2), encoding="utf-8")

    def _create_app(self) -> FastAPI:
        """Create the FastAPI application."""
        app = FastAPI(
            title="FlowyML Notebook",
            version="1.1.0",
            description="Production-grade reactive notebook for ML pipelines",
        )

        # CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # --- REST API Routes ---

        @app.get("/api/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "ok",
                "version": "0.9.0",
                "kernel": "active",
            }

        @app.post("/api/config/connection")
        async def save_connection_config(config: dict):
            """Save FlowyML connection config."""
            # Store in session for later use
            self._connection_config = config
            return {"saved": True}

        @app.get("/api/state")
        async def get_state():
            """Get complete notebook state."""
            return self.notebook.get_state()

        @app.get("/api/cells")
        async def list_cells():
            """List all cells."""
            return [c.to_dict() for c in self.notebook.cells]

        @app.post("/api/cells")
        async def add_cell(cell: CellCreate):
            """Add a new cell."""
            new_cell = self.notebook.cell(
                source=cell.source,
                cell_type=CellType(cell.cell_type),
                name=cell.name,
            )
            if cell.index is not None:
                self.notebook.notebook.move_cell(new_cell.id, cell.index)
            return new_cell.to_dict()

        @app.put("/api/cells/{cell_id}")
        async def update_cell(cell_id: str, cell: CellUpdate):
            """Update cell source."""
            stale = self.notebook.update_cell(cell_id, cell.source)
            return {
                "cell_id": cell_id,
                "stale_cells": list(stale),
                "graph": self.notebook.graph.to_dict(),
            }

        @app.delete("/api/cells/{cell_id}")
        async def delete_cell(cell_id: str):
            """Delete a cell."""
            stale = self.notebook.graph.remove_cell(cell_id)
            self.notebook.notebook.remove_cell(cell_id)
            return {"deleted": cell_id, "stale_cells": list(stale)}

        @app.post("/api/cells/{cell_id}/move")
        async def move_cell(cell_id: str, index: int):
            """Move a cell to a new position."""
            self.notebook.notebook.move_cell(cell_id, index)
            return {"moved": cell_id, "index": index}

        @app.post("/api/cells/{cell_id}/execute")
        async def execute_cell(cell_id: str, reactive: bool = True):
            """Execute a cell (with optional reactive propagation)."""
            if reactive:
                results = self.notebook.execute_cell_reactive(cell_id)
            else:
                result = self.notebook.execute_cell(cell_id)
                results = [result]
            return {
                "results": [r.to_dict() for r in results],
                "graph": self.notebook.graph.to_dict(),
                "variables": self.notebook.session.get_variables(),
            }

        @app.post("/api/execute-all")
        async def execute_all():
            """Execute all cells."""
            results = self.notebook.run()
            return {
                "results": [r.to_dict() for r in results],
                "graph": self.notebook.graph.to_dict(),
                "variables": self.notebook.session.get_variables(),
            }

        @app.get("/api/variables")
        async def get_variables():
            """Get variable inspector data."""
            return self.notebook.session.get_variables()

        @app.post("/api/upload-csv")
        async def upload_csv(file: UploadFile):
            """Upload a CSV file and load it as a DataFrame."""
            import io

            try:
                import pandas as pd
            except ImportError:
                return {"error": "pandas is required. Install with: pip install pandas"}

            contents = await file.read()
            var_name = file.filename.rsplit(".", 1)[0].replace("-", "_").replace(" ", "_").lower()
            # Sanitize variable name
            var_name = "".join(c if c.isalnum() or c == "_" else "_" for c in var_name)
            if var_name[0].isdigit():
                var_name = "df_" + var_name

            try:
                df = pd.read_csv(io.BytesIO(contents))
            except Exception as e:
                return {"error": f"Failed to parse CSV: {str(e)}"}

            # Store in kernel namespace
            self.notebook.session._ensure_kernel()
            self.notebook.session._namespace[var_name] = df

            # Create a code cell that references the loaded data
            cell_source = f"# Loaded from: {file.filename}\\n{var_name}"
            new_cell = self.notebook.cell(
                source=cell_source,
                cell_type=CellType(CellType.CODE),
                name=f"load_{var_name}",
            )

            # Execute the cell to produce the DataFrame output
            result = self.notebook.execute_cell(new_cell.id)

            return {
                "variable_name": var_name,
                "cell_id": new_cell.id,
                "rows": len(df),
                "columns": list(df.columns),
                "result": result.to_dict() if hasattr(result, "to_dict") else None,
                "variables": self.notebook.session.get_variables(),
            }

        @app.get("/api/explore/{var_name}")
        async def explore_dataframe(var_name: str):
            """Get comprehensive profiling data for a DataFrame variable."""
            try:
                import pandas as pd
                import numpy as np
            except ImportError:
                raise HTTPException(400, "pandas and numpy are required")

            self.notebook.session._ensure_kernel()
            ns = self.notebook.session._namespace
            if var_name not in ns:
                raise HTTPException(404, f"Variable '{var_name}' not found")

            obj = ns[var_name]
            type_name = type(obj).__name__
            if type_name != "DataFrame":
                raise HTTPException(400, f"'{var_name}' is a {type_name}, not a DataFrame")

            df = obj
            result: dict = {
                "name": var_name,
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "memory_bytes": int(df.memory_usage(deep=True).sum()),
                "null_counts": {col: int(df[col].isnull().sum()) for col in df.columns},
                "stats": {},
                "histograms": {},
                "correlations": None,
                "data_quality": {},
                "ml_insights": {},
                "sample": [],
            }

            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

            # Per-column stats (enhanced with ML-relevant metrics)
            for col in df.columns:
                s = df[col]
                col_stat: dict = {"count": int(s.count()), "null_count": int(s.isnull().sum())}

                if pd.api.types.is_numeric_dtype(s):
                    desc = s.describe()
                    clean = s.dropna()
                    q1 = float(desc.get("25%", 0))
                    q3 = float(desc.get("75%", 0))
                    iqr = q3 - q1
                    mean_val = float(desc.get("mean", 0))
                    std_val = float(desc.get("std", 0))
                    skew_val = float(s.skew()) if len(clean) > 2 else 0.0
                    kurt_val = float(s.kurtosis()) if len(clean) > 3 else 0.0

                    # Outlier detection (IQR method)
                    lower_fence = q1 - 1.5 * iqr
                    upper_fence = q3 + 1.5 * iqr
                    outlier_count = int(((clean < lower_fence) | (clean > upper_fence)).sum()) if len(clean) > 0 else 0

                    # Distribution shape classification
                    if abs(skew_val) < 0.5:
                        shape = "symmetric"
                    elif skew_val > 0:
                        shape = "right-skewed"
                    else:
                        shape = "left-skewed"

                    # Coefficient of variation
                    cv = abs(std_val / mean_val) if mean_val != 0 else float("inf")

                    col_stat.update({
                        "type": "numeric",
                        "mean": round(mean_val, 4),
                        "std": round(std_val, 4),
                        "min": round(float(desc.get("min", 0)), 4),
                        "q25": round(q1, 4),
                        "median": round(float(desc.get("50%", 0)), 4),
                        "q75": round(q3, 4),
                        "max": round(float(desc.get("max", 0)), 4),
                        "skew": round(skew_val, 4),
                        "kurtosis": round(kurt_val, 4),
                        "zeros": int((s == 0).sum()),
                        "negative": int((s < 0).sum()),
                        # ML-specific
                        "outliers": outlier_count,
                        "outlier_pct": round(outlier_count / len(clean) * 100, 1) if len(clean) > 0 else 0,
                        "lower_fence": round(lower_fence, 4),
                        "upper_fence": round(upper_fence, 4),
                        "iqr": round(iqr, 4),
                        "cv": round(cv, 4) if cv != float("inf") else None,
                        "shape": shape,
                        "is_integer": bool(clean.apply(lambda x: float(x).is_integer()).all()) if len(clean) > 0 else False,
                        "range": round(float(desc.get("max", 0)) - float(desc.get("min", 0)), 4),
                        "variance": round(float(s.var()), 4) if len(clean) > 1 else 0,
                    })

                    # Histogram
                    try:
                        if len(clean) > 0:
                            counts, edges = np.histogram(clean, bins=min(20, max(5, len(clean) // 5)))
                            result["histograms"][col] = {
                                "counts": counts.tolist(),
                                "bin_edges": [round(float(e), 4) for e in edges],
                            }
                    except Exception:
                        pass

                    # Box plot data
                    try:
                        if len(clean) > 0:
                            col_stat["boxplot"] = {
                                "min": round(float(clean.min()), 4),
                                "q1": round(q1, 4),
                                "median": round(float(clean.median()), 4),
                                "q3": round(q3, 4),
                                "max": round(float(clean.max()), 4),
                                "lower_fence": round(max(float(clean.min()), lower_fence), 4),
                                "upper_fence": round(min(float(clean.max()), upper_fence), 4),
                                "outlier_values": sorted([round(float(v), 2) for v in clean[(clean < lower_fence) | (clean > upper_fence)].head(20)]),
                            }
                    except Exception:
                        pass
                else:
                    vc = s.value_counts()
                    n_unique = int(s.nunique())
                    col_stat.update({
                        "type": "categorical",
                        "unique": n_unique,
                        "top_values": {str(k): int(v) for k, v in vc.head(10).items()},
                        "most_common": str(vc.index[0]) if len(vc) > 0 else None,
                        "most_common_pct": round(float(vc.iloc[0] / len(s) * 100), 1) if len(vc) > 0 else 0,
                        # ML-specific
                        "cardinality_ratio": round(n_unique / max(len(s), 1), 4),
                        "is_binary": n_unique == 2,
                        "is_potential_target": n_unique <= 20 and n_unique >= 2,
                        "entropy": round(float(-(vc / len(s) * np.log2(vc / len(s))).sum()), 4) if len(vc) > 0 else 0,
                    })

                    # Class balance for potential targets
                    if n_unique <= 20 and n_unique >= 2:
                        balance = {str(k): int(v) for k, v in vc.items()}
                        max_class = max(balance.values())
                        min_class = min(balance.values())
                        col_stat["class_balance"] = {
                            "classes": balance,
                            "imbalance_ratio": round(max_class / max(min_class, 1), 2),
                            "is_balanced": max_class / max(min_class, 1) < 3,
                        }

                result["stats"][col] = col_stat

            # Correlation matrix for numeric columns
            if len(numeric_cols) >= 2:
                try:
                    corr = df[numeric_cols].corr()
                    result["correlations"] = {
                        "columns": numeric_cols,
                        "matrix": [[round(float(corr.iloc[i, j]), 4)
                                     for j in range(len(numeric_cols))]
                                    for i in range(len(numeric_cols))],
                    }
                except Exception:
                    pass

            # Data quality summary
            total = len(df)
            result["data_quality"] = {
                "completeness": round(float(1 - df.isnull().sum().sum() / (total * len(df.columns))) * 100, 1) if total > 0 else 100,
                "duplicate_rows": int(df.duplicated().sum()),
                "duplicate_pct": round(float(df.duplicated().sum() / total * 100), 1) if total > 0 else 0,
                "total_nulls": int(df.isnull().sum().sum()),
                "columns_with_nulls": int((df.isnull().sum() > 0).sum()),
                "constant_columns": [col for col in df.columns if df[col].nunique() <= 1],
                "high_cardinality": [col for col in df.select_dtypes(include=["object"]).columns if df[col].nunique() > 50],
            }

            # === ML Insights ===
            ml = {}

            # Feature importance by variance (for numeric)
            if numeric_cols:
                variances = {col: round(float(df[col].var()), 4) for col in numeric_cols if df[col].var() == df[col].var()}
                if variances:
                    max_var = max(variances.values()) or 1
                    ml["feature_variance"] = {col: {"variance": v, "normalized": round(v / max_var, 4)} for col, v in sorted(variances.items(), key=lambda x: -x[1])}

            # Scaling recommendations
            scaling_recs = {}
            for col in numeric_cols:
                s = df[col]
                clean = s.dropna()
                if len(clean) == 0:
                    continue
                mn, mx = float(clean.min()), float(clean.max())
                mean_v = float(clean.mean())
                std_v = float(clean.std())
                skew_v = float(clean.skew()) if len(clean) > 2 else 0

                if abs(skew_v) > 1:
                    scaling_recs[col] = {"method": "log_transform", "reason": f"High skewness ({skew_v:.2f}) — log/power transform recommended"}
                elif mx - mn > 100 * std_v:
                    scaling_recs[col] = {"method": "robust_scaler", "reason": "Large range relative to std — use RobustScaler"}
                elif mn >= 0 and mx <= 1:
                    scaling_recs[col] = {"method": "none", "reason": "Already in [0, 1] range"}
                elif abs(mean_v) < 1 and std_v < 2:
                    scaling_recs[col] = {"method": "none", "reason": "Already near-standard scale"}
                else:
                    scaling_recs[col] = {"method": "standard_scaler", "reason": "StandardScaler (zero mean, unit variance)"}
            ml["scaling"] = scaling_recs

            # Target variable detection
            potential_targets = []
            for col in df.columns:
                s = df[col]
                n_unique = int(s.nunique())
                if col.lower() in ("target", "label", "class", "y", "outcome", "status", "category"):
                    potential_targets.append({"column": col, "reason": "Name suggests target variable", "n_classes": n_unique, "type": "classification" if n_unique <= 20 else "regression"})
                elif pd.api.types.is_numeric_dtype(s) and n_unique == 2:
                    potential_targets.append({"column": col, "reason": "Binary numeric column", "n_classes": 2, "type": "classification"})
                elif not pd.api.types.is_numeric_dtype(s) and 2 <= n_unique <= 10:
                    potential_targets.append({"column": col, "reason": f"Low-cardinality categorical ({n_unique} classes)", "n_classes": n_unique, "type": "classification"})
            ml["potential_targets"] = potential_targets

            # Algorithm suggestions
            suggestions = []
            n_rows = len(df)
            n_features = len(numeric_cols)
            has_categorical = len(categorical_cols) > 0

            if n_rows < 100:
                suggestions.append({"algo": "Simple models (Logistic Regression, KNN)", "reason": "Small dataset — avoid complex models that may overfit", "icon": "caution"})
            elif n_rows < 10000:
                suggestions.append({"algo": "Random Forest / Gradient Boosting", "reason": f"Medium dataset ({n_rows} rows) — tree-based models work well", "icon": "recommended"})
                suggestions.append({"algo": "SVM", "reason": "Good for medium datasets with clear margins", "icon": "alternative"})
            else:
                suggestions.append({"algo": "XGBoost / LightGBM / CatBoost", "reason": f"Large dataset ({n_rows:,} rows) — gradient boosting excels", "icon": "recommended"})
                suggestions.append({"algo": "Neural Network", "reason": "Consider deep learning for very large datasets", "icon": "alternative"})

            if has_categorical:
                suggestions.append({"algo": "CatBoost", "reason": "Handles categorical features natively", "icon": "recommended"})

            if n_features > 50:
                suggestions.append({"algo": "PCA / Feature Selection", "reason": f"High dimensionality ({n_features} features) — consider dimensionality reduction", "icon": "preprocessing"})

            # Check for multicollinearity
            if result["correlations"]:
                highly_corr = []
                cols = result["correlations"]["columns"]
                matrix = result["correlations"]["matrix"]
                for i in range(len(cols)):
                    for j in range(i + 1, len(cols)):
                        if abs(matrix[i][j]) > 0.9:
                            highly_corr.append({"a": cols[i], "b": cols[j], "corr": matrix[i][j]})
                if highly_corr:
                    suggestions.append({"algo": "Remove multicollinear features", "reason": f"{len(highly_corr)} feature pair(s) with |r| > 0.9", "icon": "warning", "pairs": highly_corr})
            ml["suggestions"] = suggestions

            # Feature type classification
            feature_types = {}
            for col in df.columns:
                s = df[col]
                n_unique = int(s.nunique())
                if pd.api.types.is_numeric_dtype(s):
                    if n_unique == 2:
                        feature_types[col] = "binary"
                    elif n_unique <= 10 and s.apply(lambda x: float(x).is_integer() if pd.notna(x) else True).all():
                        feature_types[col] = "ordinal"
                    else:
                        feature_types[col] = "continuous"
                elif pd.api.types.is_datetime64_any_dtype(s):
                    feature_types[col] = "temporal"
                else:
                    if n_unique == 2:
                        feature_types[col] = "binary"
                    elif n_unique <= 20:
                        feature_types[col] = "nominal"
                    else:
                        feature_types[col] = "high_cardinality"
            ml["feature_types"] = feature_types

            # Dataset summary for ML
            ml["summary"] = {
                "n_samples": n_rows,
                "n_features": len(df.columns),
                "n_numeric": len(numeric_cols),
                "n_categorical": len(categorical_cols),
                "has_nulls": bool(df.isnull().any().any()),
                "has_duplicates": bool(df.duplicated().any()),
                "memory_mb": round(int(df.memory_usage(deep=True).sum()) / 1024 / 1024, 2),
                "samples_per_feature": round(n_rows / max(len(df.columns), 1), 1),
            }

            result["ml_insights"] = ml

            # Sample rows (first 5)
            try:
                result["sample"] = df.head(5).to_dict(orient="records")
            except Exception:
                result["sample"] = []

            return result

        @app.get("/api/explore/{var_name}/correlation")
        async def get_correlation(var_name: str, method: str = "pearson"):
            """Get correlation matrix for a DataFrame."""
            try:
                import pandas as pd
                import numpy as np
            except ImportError:
                raise HTTPException(400, "pandas and numpy required")

            self.notebook.session._ensure_kernel()
            ns = self.notebook.session._namespace
            if var_name not in ns:
                raise HTTPException(404, f"Variable '{var_name}' not found")

            df = ns[var_name]
            if type(df).__name__ != "DataFrame":
                raise HTTPException(400, "Not a DataFrame")

            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) < 2:
                return {"columns": numeric_cols, "matrix": [], "method": method}

            corr = df[numeric_cols].corr(method=method)
            return {
                "columns": numeric_cols,
                "matrix": [[round(float(corr.iloc[i, j]), 4)
                             for j in range(len(numeric_cols))]
                            for i in range(len(numeric_cols))],
                "method": method,
            }

        @app.get("/api/graph")
        async def get_graph():
            """Get reactive dependency graph."""
            return self.notebook.graph.to_dict()

        @app.post("/api/save")
        async def save_notebook(path: str | None = None):
            """Save notebook to file."""
            saved_path = self.notebook.save(path)
            # Also update notebook manager index
            if self.current_nb_id:
                cells_data = [c.to_dict() for c in self.notebook.cells]
                self.nb_manager.save_notebook_data(
                    self.current_nb_id,
                    cells_data,
                    {"name": self.notebook.notebook.metadata.name},
                )
            return {"path": saved_path}

        @app.post("/api/load")
        async def load_notebook(path: str):
            """Load notebook from file."""
            self.notebook.load(path)
            return self.notebook.get_state()

        # ===== Workspace Files Explorer =====
        @app.get("/api/files")
        async def list_workspace_files():
            """List files in the current workspace directory."""
            import os

            cwd = os.getcwd()
            ignore = {
                "__pycache__", ".git", "node_modules", ".venv", "venv",
                ".mypy_cache", ".pytest_cache", ".tox", "dist", "build",
                ".egg-info", ".eggs",
            }

            def build_tree(path: str, name: str) -> dict:
                node: dict = {
                    "name": name,
                    "path": os.path.relpath(path, cwd),
                    "is_dir": os.path.isdir(path),
                }
                if os.path.isdir(path):
                    try:
                        children = []
                        for item in sorted(os.listdir(path)):
                            if item.startswith(".") and item not in (".env",):
                                continue
                            if item in ignore:
                                continue
                            child_path = os.path.join(path, item)
                            children.append(build_tree(child_path, item))
                        # Sort: dirs first, then files
                        children.sort(
                            key=lambda x: (0 if x["is_dir"] else 1, x["name"].lower())
                        )
                        node["children"] = children
                    except PermissionError:
                        node["children"] = []
                else:
                    try:
                        node["size"] = os.path.getsize(path)
                    except OSError:
                        node["size"] = 0
                return node

            return build_tree(cwd, os.path.basename(cwd))

        # ===== Version Control (Snapshot-based) =====
        @app.get("/api/version/history")
        async def get_version_history():
            """Get notebook snapshot history."""
            import os
            import json as json_mod
            from pathlib import Path

            history_dir = Path.home() / ".flowyml" / "history"
            history_dir.mkdir(parents=True, exist_ok=True)

            commits = []
            for f in sorted(history_dir.glob("*.json"), reverse=True):
                try:
                    meta = json_mod.loads(f.read_text())
                    commits.append({
                        "id": f.stem,
                        "message": meta.get("message", "Snapshot"),
                        "timestamp": meta.get("timestamp"),
                        "cell_count": meta.get("cell_count", 0),
                        "additions": meta.get("additions", 0),
                        "deletions": meta.get("deletions", 0),
                    })
                except Exception:
                    continue

            return {"commits": commits[:50]}

        @app.post("/api/version/snapshot")
        async def create_snapshot():
            """Create a snapshot of the current notebook state."""
            import json as json_mod
            from pathlib import Path
            from datetime import datetime
            import hashlib

            history_dir = Path.home() / ".flowyml" / "history"
            history_dir.mkdir(parents=True, exist_ok=True)

            state = self.notebook.get_state()
            cells_data = state.get("notebook", {}).get("cells", [])

            # Compute changes vs last snapshot
            additions = 0
            deletions = 0
            snapshots = sorted(history_dir.glob("*.json"), reverse=True)
            if snapshots:
                try:
                    prev = json_mod.loads(snapshots[0].read_text())
                    prev_cells = {c["id"]: c.get("source", "") for c in prev.get("cells", [])}
                    curr_cells = {c["id"]: c.get("source", "") for c in cells_data}

                    for cid in curr_cells:
                        if cid not in prev_cells:
                            additions += len(curr_cells[cid].split("\n"))
                        elif curr_cells[cid] != prev_cells[cid]:
                            old_lines = set(prev_cells[cid].split("\n"))
                            new_lines = set(curr_cells[cid].split("\n"))
                            additions += len(new_lines - old_lines)
                            deletions += len(old_lines - new_lines)
                    for cid in prev_cells:
                        if cid not in curr_cells:
                            deletions += len(prev_cells[cid].split("\n"))
                except Exception:
                    pass

            ts = datetime.now().isoformat()
            snapshot_id = hashlib.sha256(ts.encode()).hexdigest()[:12]

            snapshot = {
                "id": snapshot_id,
                "message": f"Snapshot at {datetime.now().strftime('%H:%M:%S')}",
                "timestamp": ts,
                "cell_count": len(cells_data),
                "additions": additions,
                "deletions": deletions,
                "cells": [
                    {
                        "id": c.get("id", ""),
                        "name": c.get("name", ""),
                        "cell_type": c.get("cell_type", "code"),
                        "source": c.get("source", ""),
                    }
                    for c in cells_data
                ],
            }

            (history_dir / f"{snapshot_id}.json").write_text(
                json_mod.dumps(snapshot, indent=2)
            )

            return {"id": snapshot_id, "message": snapshot["message"]}

        @app.get("/api/version/diff/{commit_id}")
        async def get_version_diff(commit_id: str):
            """Get diff between a snapshot and the current state."""
            import json as json_mod
            from pathlib import Path

            history_dir = Path.home() / ".flowyml" / "history"
            snapshot_file = history_dir / f"{commit_id}.json"

            if not snapshot_file.exists():
                raise HTTPException(404, "Snapshot not found")

            snap = json_mod.loads(snapshot_file.read_text())
            snap_cells = {c["id"]: c for c in snap.get("cells", [])}

            state = self.notebook.get_state()
            curr_cells = {
                c["id"]: c
                for c in state.get("notebook", {}).get("cells", [])
            }

            changes = []
            # Changed and added cells
            for cid, cell in curr_cells.items():
                if cid not in snap_cells:
                    changes.append({
                        "cell_id": cid,
                        "cell_name": cell.get("name", ""),
                        "type": "added",
                        "lines": [
                            {"type": "add", "content": line}
                            for line in (cell.get("source", "")).split("\n")
                        ],
                    })
                elif cell.get("source", "") != snap_cells[cid].get("source", ""):
                    old_lines = snap_cells[cid].get("source", "").split("\n")
                    new_lines = cell.get("source", "").split("\n")
                    diff_lines = _compute_diff_lines(old_lines, new_lines)
                    changes.append({
                        "cell_id": cid,
                        "cell_name": cell.get("name", ""),
                        "type": "modified",
                        "lines": diff_lines,
                    })

            # Deleted cells
            for cid, cell in snap_cells.items():
                if cid not in curr_cells:
                    changes.append({
                        "cell_id": cid,
                        "cell_name": cell.get("name", ""),
                        "type": "deleted",
                        "lines": [
                            {"type": "remove", "content": line}
                            for line in cell.get("source", "").split("\n")
                        ],
                    })

            return {"changes": changes}

        @app.post("/api/version/restore/{commit_id}")
        async def restore_version(commit_id: str):
            """Restore notebook to a specific snapshot."""
            import json as json_mod
            from pathlib import Path

            history_dir = Path.home() / ".flowyml" / "history"
            snapshot_file = history_dir / f"{commit_id}.json"

            if not snapshot_file.exists():
                raise HTTPException(404, "Snapshot not found")

            # First, save current state as a backup snapshot
            await create_snapshot()

            snap = json_mod.loads(snapshot_file.read_text())
            # Clear current cells and restore from snapshot
            self.notebook.cells.clear()
            for cell_data in snap.get("cells", []):
                cell = self.notebook.cell(
                    source=cell_data.get("source", ""),
                    cell_type=CellType(cell_data.get("cell_type", "code")),
                    name=cell_data.get("name", ""),
                )

            return {"restored": True, "cell_count": len(self.notebook.cells)}

        @app.post("/api/schedule")
        async def schedule(schedule: ScheduleCreate):
            """Schedule notebook as a pipeline."""
            result = self.notebook.schedule(
                cron=schedule.cron,
                interval_hours=schedule.interval_hours,
            )
            return result

        @app.post("/api/export")
        async def export_notebook(req: ExportRequest):
            """Export notebook to various formats."""
            if req.format == "pipeline":
                from flowyml_notebook.deployer import promote_to_pipeline
                path = promote_to_pipeline(self.notebook.notebook)
                return {"format": "pipeline", "path": path}
            elif req.format in ("html", "pdf"):
                from flowyml_notebook.reporting import generate_report
                path = generate_report(
                    self.notebook.notebook,
                    format=req.format,
                    include_code=req.include_code,
                )
                return {"format": req.format, "path": path}
            else:
                raise HTTPException(400, f"Unsupported format: {req.format}")

        # --- Report Generation ---

        @app.post("/api/report/generate")
        async def generate_report_endpoint(req: ReportRequest):
            """Generate a report and return download path."""
            from flowyml_notebook.reporting import generate_report
            # Auto-execute all cells to populate outputs
            try:
                self.notebook.run()
            except Exception as e:
                logger.warning(f"Some cells failed during report auto-execution: {e}")
            title = req.title or f"{self.notebook.notebook.metadata.name} — Report"
            path = generate_report(
                self.notebook.notebook,
                format=req.format,
                title=title,
                include_code=req.include_code,
            )
            return {"path": path, "format": req.format, "title": title}

        @app.get("/api/report/preview")
        async def preview_report(include_code: bool = False, title: str = ""):
            """Generate and serve report as HTML for preview."""
            from flowyml_notebook.reporting import _generate_html_report
            # Auto-execute all cells to populate outputs
            try:
                self.notebook.run()
            except Exception as e:
                logger.warning(f"Some cells failed during report preview: {e}")
            report_title = title or f"{self.notebook.notebook.metadata.name} — Report"
            html = _generate_html_report(self.notebook.notebook, report_title, include_code)
            return HTMLResponse(content=html)

        @app.get("/api/report/download")
        async def download_report(format: str = "html", include_code: bool = False, title: str = ""):
            """Generate report and return as downloadable file."""
            from flowyml_notebook.reporting import generate_report
            report_title = title or f"{self.notebook.notebook.metadata.name} — Report"
            path = generate_report(
                self.notebook.notebook,
                format=format,
                title=report_title,
                include_code=include_code,
            )
            return FileResponse(path, filename=os.path.basename(path),
                                media_type="text/html" if format == "html" else "application/pdf")

        # --- App Mode / Publish ---

        @app.post("/api/app/publish")
        async def publish_app(req: AppPublishRequest):
            """Generate and store app mode HTML. Auto-executes all cells first."""
            from flowyml_notebook.ui.app_mode import AppMode, LayoutType

            # Auto-execute all cells to ensure outputs are populated
            try:
                self.notebook.run()
            except Exception as e:
                logger.warning(f"Some cells failed during auto-execution: {e}")

            app = AppMode(self.notebook)
            app.configure(
                layout=req.layout,
                theme=req.theme,
                show_code=req.show_code,
                title=req.title or self.notebook.notebook.metadata.name,
                grid_columns=req.grid_columns,
            )
            for cell_id, visible in req.cell_visibility.items():
                if visible:
                    app.show_cell(cell_id)
                else:
                    app.hide_cell(cell_id)

            html = app.to_html()
            # Save to file
            save_dir = os.path.join(os.path.expanduser("~"), ".flowyml", "published_apps")
            os.makedirs(save_dir, exist_ok=True)
            safe_name = (req.title or self.notebook.notebook.metadata.name).replace(" ", "_").lower()
            save_path = os.path.join(save_dir, f"{safe_name}.html")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html)
            self._published_app_html = html
            return {"path": save_path, "preview_url": "/api/app/preview"}

        @app.get("/api/app/preview")
        async def preview_app():
            """Serve the published app HTML."""
            html = getattr(self, "_published_app_html", None)
            if not html:
                # Generate default app view
                from flowyml_notebook.ui.app_mode import AppMode
                app = AppMode(self.notebook)
                app.configure(title=self.notebook.notebook.metadata.name)
                html = app.to_html()
            return HTMLResponse(content=html)

        # --- Widget Updates ---

        @app.post("/api/widgets/update")
        async def update_widget(req: WidgetUpdate):
            """Update a widget value in the kernel namespace."""
            self.notebook.session._namespace[req.widget_id] = req.value
            return {"widget_id": req.widget_id, "value": req.value, "synced": True}

        @app.post("/api/connect")
        async def connect_server(url: str):
            """Connect to a FlowyML server."""
            self.notebook.connect(url)
            return {"connected": True, "server": url}

        @app.post("/api/kernel/reset")
        async def reset_kernel():
            """Reset the execution kernel."""
            self.notebook.session.reset()
            return {"status": "reset"}

        # --- Notebook Management ---

        @app.get("/api/demo/load")
        async def load_demo():
            """Load a pre-populated demo notebook with fake data."""
            import uuid as _uuid
            from datetime import datetime as _dt

            demo_cells = [
                {
                    "id": str(_uuid.uuid4())[:8],
                    "cell_type": "code",
                    "source": (
                        "# FlowyML Notebook — E2E Demo\n"
                        "import pandas as pd\n"
                        "import numpy as np\n"
                        "from datetime import datetime, timedelta\n"
                        "print('\\u2705 Libraries loaded successfully')"
                    ),
                    "outputs": [],
                    "execution_count": 0,
                    "name": "imports",
                },
                {
                    "id": str(_uuid.uuid4())[:8],
                    "cell_type": "code",
                    "source": (
                        "# Generate ML experiment dataset\n"
                        "np.random.seed(42)\n"
                        "n = 100\n\n"
                        "df = pd.DataFrame({\n"
                        "    'experiment_id': [f'exp_{i:03d}' for i in range(n)],\n"
                        "    'model': np.random.choice(['RandomForest', 'XGBoost', 'LightGBM', 'Neural Net', 'SVM'], n),\n"
                        "    'learning_rate': np.round(np.random.uniform(0.001, 0.1, n), 4),\n"
                        "    'n_estimators': np.random.choice([50, 100, 200, 500, 1000], n),\n"
                        "    'accuracy': np.round(np.random.uniform(0.72, 0.98, n), 4),\n"
                        "    'f1_score': np.round(np.random.uniform(0.68, 0.96, n), 4),\n"
                        "    'training_time_s': np.round(np.random.exponential(30, n), 2),\n"
                        "    'memory_mb': np.round(np.random.uniform(50, 2000, n), 1),\n"
                        "    'dataset_size': np.random.choice([1000, 5000, 10000, 50000, 100000], n),\n"
                        "    'status': np.random.choice(['completed', 'completed', 'completed', 'failed', 'timeout'], n),\n"
                        "    'created_at': [datetime.now() - timedelta(hours=np.random.randint(1, 720)) for _ in range(n)],\n"
                        "})\n\n"
                        "print(f'Generated {len(df)} experiments with {len(df.columns)} features')\n"
                        "df"
                    ),
                    "outputs": [],
                    "execution_count": 0,
                    "name": "data_generation",
                },
                {
                    "id": str(_uuid.uuid4())[:8],
                    "cell_type": "code",
                    "source": (
                        "# Analysis: Best models by accuracy\n"
                        "summary = df.groupby('model').agg(\n"
                        "    avg_accuracy=('accuracy', 'mean'),\n"
                        "    avg_f1=('f1_score', 'mean'),\n"
                        "    avg_time=('training_time_s', 'mean'),\n"
                        "    count=('experiment_id', 'count'),\n"
                        "    best_accuracy=('accuracy', 'max'),\n"
                        ").round(4).sort_values('avg_accuracy', ascending=False)\n\n"
                        "print('\\U0001f3c6 Model Performance Summary:')\n"
                        "summary"
                    ),
                    "outputs": [],
                    "execution_count": 0,
                    "name": "analysis",
                },
                {
                    "id": str(_uuid.uuid4())[:8],
                    "cell_type": "code",
                    "source": (
                        "# Filter and explore: high-performance experiments\n"
                        "top_experiments = df[\n"
                        "    (df['accuracy'] > 0.90) &\n"
                        "    (df['status'] == 'completed')\n"
                        "].sort_values('accuracy', ascending=False)\n\n"
                        "print(f'\\U0001f680 Found {len(top_experiments)} high-performance experiments (accuracy > 90%)')\n"
                        "top_experiments[['experiment_id', 'model', 'accuracy', 'f1_score', 'training_time_s', 'memory_mb']]"
                    ),
                    "outputs": [],
                    "execution_count": 0,
                    "name": "exploration",
                },
                {
                    "id": str(_uuid.uuid4())[:8],
                    "cell_type": "markdown",
                    "source": (
                        "## \\U0001f4ca Results Summary\\n\\n"
                        "This demo notebook shows end-to-end FlowyML Notebook capabilities:\\n\\n"
                        "- **DataFrame display** with interactive exploration\\n"
                        "- **Cell execution metrics** (duration, memory)\\n"
                        "- **Reactive execution** — downstream cells auto-update\\n"
                        "- **Variable inspector** — track all variables in the session\\n\\n"
                        "> Click **Run All** to execute all cells and see results!"
                    ),
                    "outputs": [],
                    "execution_count": 0,
                    "name": "summary",
                },
            ]

            # Load the demo cells into the current notebook
            self.notebook.notebook.metadata.name = "FlowyML E2E Demo"
            self.notebook.notebook.cells.clear()
            for cell_data in demo_cells:
                from flowyml_notebook.cells import Cell, CellType
                ct = CellType.CODE if cell_data["cell_type"] == "code" else CellType.MARKDOWN
                cell = Cell(
                    id=cell_data["id"],
                    cell_type=ct,
                    source=cell_data["source"],
                    name=cell_data.get("name", ""),
                )
                self.notebook.notebook.cells.append(cell)
                try:
                    self.notebook.graph.add_cell(cell.id)
                    if ct == CellType.CODE:
                        self.notebook.graph.analyze_cell(cell.id, cell.source)
                except Exception:
                    pass  # graph analysis is optional

            return self.notebook.get_state()

        @app.get("/api/notebooks")
        async def list_notebooks():
            """List all saved notebooks."""
            return self.nb_manager.list_notebooks()

        @app.post("/api/notebooks")
        async def create_notebook(data: NotebookCreate):
            """Create a new notebook."""
            result = self.nb_manager.create_notebook(name=data.name)
            # Switch to the new notebook
            nb_data = self.nb_manager.get_notebook(result["id"])
            if nb_data:
                self.notebook.load_from_dict(nb_data)
                self.current_nb_id = result["id"]
            return result

        @app.put("/api/notebooks/{nb_id}/rename")
        async def rename_notebook(nb_id: str, name: str):
            """Rename a notebook."""
            result = self.nb_manager.rename_notebook(nb_id, name)
            if not result:
                raise HTTPException(404, "Notebook not found")
            return result

        @app.delete("/api/notebooks/{nb_id}")
        async def delete_notebook(nb_id: str):
            """Delete a notebook."""
            if not self.nb_manager.delete_notebook(nb_id):
                raise HTTPException(404, "Notebook not found")
            return {"deleted": True}

        @app.post("/api/notebooks/{nb_id}/duplicate")
        async def duplicate_notebook(nb_id: str):
            """Duplicate a notebook."""
            result = self.nb_manager.duplicate_notebook(nb_id)
            if not result:
                raise HTTPException(404, "Notebook not found")
            return result

        @app.put("/api/notebooks/{nb_id}/open")
        async def open_notebook(nb_id: str):
            """Switch to a different notebook."""
            nb_data = self.nb_manager.get_notebook(nb_id)
            if not nb_data:
                raise HTTPException(404, "Notebook not found")
            # Load the notebook data
            self.notebook.load_from_dict(nb_data)
            self.current_nb_id = nb_id
            return self.notebook.get_state()

        @app.post("/api/auto-save")
        async def auto_save():
            """Auto-save current notebook state."""
            try:
                saved_path = self.notebook.save()
                # Also update notebook manager index if we have a current notebook
                if self.current_nb_id:
                    cells_data = [c.to_dict() for c in self.notebook.cells]
                    self.nb_manager.save_notebook_data(
                        self.current_nb_id,
                        cells_data,
                        {"name": self.notebook.notebook.metadata.name},
                    )
                return {"saved": True, "path": saved_path, "timestamp": __import__("datetime").datetime.now().isoformat()}
            except Exception as e:
                return {"saved": False, "error": str(e)}

        @app.put("/api/metadata")
        async def update_metadata(name: str | None = None, description: str | None = None):
            """Update current notebook metadata."""
            if name is not None:
                self.notebook.notebook.metadata.name = name
                # Also update in notebook manager index
                if self.current_nb_id:
                    self.nb_manager.rename_notebook(self.current_nb_id, name)
            if description is not None:
                self.notebook.notebook.metadata.description = description
                if self.current_nb_id:
                    self.nb_manager.update_metadata(self.current_nb_id, description=description)
            return {"name": self.notebook.notebook.metadata.name}

        # --- Production Panel Data (Real Data) ---

        @app.get("/api/production/pipelines")
        async def get_pipelines():
            """Get real pipeline data from notebook cells and execution history."""
            pipelines = []
            # Build pipeline info from cells that use @step or Pipeline()
            step_cells = []
            for cell in self.notebook.cells:
                if cell.cell_type.value == "code" and cell.source:
                    if "@step" in cell.source or "Pipeline(" in cell.source:
                        step_cells.append({
                            "cell_id": cell.id,
                            "name": cell.name or f"cell_{cell.id[:6]}",
                            "source": cell.source[:200],
                            "has_step": "@step" in cell.source,
                            "has_pipeline": "Pipeline(" in cell.source,
                            "executed": cell.execution_count > 0,
                            "last_executed": cell.last_executed,
                        })

            # Check if notebook was promoted to pipeline
            import os
            pipeline_dir = Path(os.getcwd())
            promoted = []
            for f in pipeline_dir.glob("*_pipeline.py"):
                stat = f.stat()
                promoted.append({
                    "name": f.stem,
                    "path": str(f),
                    "status": "success",
                    "steps": len(step_cells),
                    "last_run": __import__("datetime").datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_bytes": stat.st_size,
                })

            return {
                "step_cells": step_cells,
                "promoted_pipelines": promoted,
                "total_steps": len(step_cells),
            }

        @app.get("/api/production/experiments")
        async def get_experiments():
            """Get real experiment data from kernel namespace."""
            experiments = []
            metrics_summary = {}

            ns = self.notebook.session._namespace if self.notebook.session._initialized else {}

            # Look for Experiment, Metrics, and model objects in namespace
            for name, obj in ns.items():
                if name.startswith("_"):
                    continue
                type_name = type(obj).__name__

                # Detect metrics objects
                if type_name == "Metrics" or (isinstance(obj, dict) and any(k in str(obj) for k in ["accuracy", "f1", "precision", "recall", "loss", "mse"])):
                    if isinstance(obj, dict):
                        metrics_summary.update(obj)
                    elif hasattr(obj, "to_dict"):
                        metrics_summary.update(obj.to_dict())

                # Detect sklearn/xgboost/etc models
                if hasattr(obj, "predict") and hasattr(obj, "fit"):
                    model_info = {
                        "name": name,
                        "type": type_name,
                        "module": type(obj).__module__,
                    }
                    # Try to get params
                    if hasattr(obj, "get_params"):
                        try:
                            params = obj.get_params()
                            model_info["params"] = {k: _safe_serialize(v) for k, v in list(params.items())[:10]}
                        except Exception:
                            pass
                    # Try to get score
                    if hasattr(obj, "score"):
                        model_info["has_score"] = True

                    experiments.append(model_info)

            return {
                "models": experiments,
                "metrics": metrics_summary,
                "has_data": len(experiments) > 0 or len(metrics_summary) > 0,
            }

        @app.get("/api/production/assets")
        async def get_assets():
            """Get real asset data from kernel namespace."""
            assets = []
            ns = self.notebook.session._namespace if self.notebook.session._initialized else {}

            for name, obj in ns.items():
                if name.startswith("_"):
                    continue
                type_name = type(obj).__name__
                module = type(obj).__module__

                asset_info = None

                # DataFrames
                if type_name == "DataFrame":
                    size = obj.memory_usage(deep=True).sum()
                    asset_info = {
                        "name": name,
                        "type": "dataset",
                        "subtype": "DataFrame",
                        "size": _format_size(size),
                        "size_bytes": int(size),
                        "rows": len(obj),
                        "columns": len(obj.columns),
                        "column_names": list(obj.columns),
                    }

                # NumPy arrays
                elif type_name == "ndarray":
                    size = obj.nbytes
                    asset_info = {
                        "name": name,
                        "type": "dataset",
                        "subtype": "ndarray",
                        "size": _format_size(size),
                        "size_bytes": int(size),
                        "shape": list(obj.shape),
                        "dtype": str(obj.dtype),
                    }

                # ML Models
                elif hasattr(obj, "predict") and hasattr(obj, "fit"):
                    import sys
                    size = sys.getsizeof(obj)
                    asset_info = {
                        "name": name,
                        "type": "model",
                        "subtype": type_name,
                        "module": module,
                        "size": _format_size(size),
                        "size_bytes": int(size),
                    }

                # Dicts that look like metrics
                elif isinstance(obj, dict) and len(obj) > 0 and len(obj) < 50:
                    if all(isinstance(v, (int, float)) for v in obj.values()):
                        asset_info = {
                            "name": name,
                            "type": "metrics",
                            "subtype": "dict",
                            "size": f"{len(obj)} entries",
                            "entries": {k: round(v, 6) if isinstance(v, float) else v for k, v in list(obj.items())[:20]},
                        }

                if asset_info:
                    assets.append(asset_info)

            return {"assets": assets, "count": len(assets)}

        @app.get("/api/production/schedules")
        async def get_schedules():
            """Get schedule data."""
            # Return actual schedules if connected to server, otherwise local state
            schedules = []
            try:
                if hasattr(self.notebook, '_connection') and self.notebook._connection:
                    schedules = self.notebook._connection.get_schedules()
            except Exception:
                pass
            return {"schedules": schedules, "count": len(schedules)}

        @app.post("/api/production/promote")
        async def promote_notebook():
            """Promote notebook to production pipeline."""
            from flowyml_notebook.deployer import promote_to_pipeline
            path = promote_to_pipeline(self.notebook.notebook)
            return {"path": path, "status": "promoted"}

        @app.post("/api/production/deploy")
        async def deploy_model(mode: str = "api", model_name: str | None = None):
            """Deploy a model from the notebook."""
            ns = self.notebook.session._namespace if self.notebook.session._initialized else {}

            # Find model if not specified
            if not model_name:
                for name, obj in ns.items():
                    if hasattr(obj, "predict") and hasattr(obj, "fit") and not name.startswith("_"):
                        model_name = name
                        break

            if not model_name or model_name not in ns:
                raise HTTPException(400, "No model found in notebook namespace")

            model = ns[model_name]
            result = {
                "model_name": model_name,
                "model_type": type(model).__name__,
                "mode": mode,
                "status": "deployed" if mode == "api" else "generated",
            }

            if mode == "docker":
                from flowyml_notebook.deployer import generate_dockerfile
                dockerfile_path = generate_dockerfile(self.notebook.notebook)
                result["dockerfile"] = dockerfile_path
            elif mode == "api":
                from flowyml_notebook.deployer import deploy_model as do_deploy
                result.update(do_deploy(model))

            return result

        # --- AI Configuration ---

        @app.get("/api/ai/config")
        async def get_ai_config():
            """Get AI provider configuration."""
            # Return config but mask the API key for security
            safe_config = dict(self._ai_config)
            if safe_config.get("api_key"):
                key = safe_config["api_key"]
                safe_config["api_key_set"] = True
                safe_config["api_key_preview"] = key[:4] + "..." + key[-4:] if len(key) > 8 else "****"
            else:
                safe_config["api_key_set"] = False
                safe_config["api_key_preview"] = ""
            safe_config.pop("api_key", None)
            return safe_config

        @app.post("/api/ai/config")
        async def save_ai_config(config: dict):
            """Save AI provider configuration.

            Accepts: provider, model, api_key, base_url, temperature
            """
            allowed_keys = {"provider", "model", "api_key", "base_url", "temperature"}
            for key in allowed_keys:
                if key in config:
                    self._ai_config[key] = config[key]

            # Set sensible defaults per provider
            provider = self._ai_config.get("provider", "openai").lower()
            if not self._ai_config.get("model"):
                defaults = {
                    "openai": "gpt-4o-mini",
                    "ollama": "llama3.1",
                    "google": "gemini-pro",
                    "anthropic": "claude-3-5-sonnet-20241022",
                }
                self._ai_config["model"] = defaults.get(provider, "gpt-4o-mini")

            if provider == "ollama" and not self._ai_config.get("base_url"):
                self._ai_config["base_url"] = "http://localhost:11434/v1"

            self._save_ai_config()

            return {"saved": True, "provider": provider, "model": self._ai_config["model"]}

        @app.post("/api/ai/test")
        async def test_ai_connection():
            """Test the current AI provider connection."""
            try:
                from flowyml_notebook.ai.assistant import NotebookAIAssistant
                provider = self._ai_config.get("provider", "openai")
                model = self._ai_config.get("model") or None
                base_url = self._ai_config.get("base_url") or None
                api_key = self._ai_config.get("api_key")

                # Set API key as env var if provided
                if api_key:
                    os.environ["OPENAI_API_KEY"] = api_key

                assistant = NotebookAIAssistant(
                    notebook=self.notebook,
                    provider=provider,
                    model=model,
                    base_url=base_url,
                )
                response = assistant.chat("Reply with exactly: OK")
                return {
                    "success": True,
                    "provider": provider,
                    "model": model,
                    "response": response.content[:100],
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                }

        @app.post("/api/ai/chat")
        async def ai_chat(body: dict):
            """Chat with the AI assistant. Used by the AI panel in the frontend."""
            message = body.get("message", "")
            if not message:
                raise HTTPException(400, "Message is required")

            # Use stored AI config
            ai_provider = self._ai_config.get("provider", "openai")
            ai_model = self._ai_config.get("model") or None
            ai_base_url = self._ai_config.get("base_url") or None
            stored_key = self._ai_config.get("api_key")
            if stored_key:
                os.environ["OPENAI_API_KEY"] = stored_key

            try:
                from flowyml_notebook.ai.assistant import NotebookAIAssistant
                assistant = NotebookAIAssistant(
                    notebook=self.notebook,
                    provider=ai_provider,
                    model=ai_model,
                    base_url=ai_base_url,
                )
                response = assistant.chat(message)
                return {
                    "content": response.content,
                    "code": response.code,
                    "suggestions": response.suggestions,
                }
            except Exception as e:
                raise HTTPException(500, f"AI error: {str(e)}")

        # --- AI Data Analysis ---

        @app.post("/api/ai/analyze")
        async def ai_analyze(variable_name: str, provider: str = "openai", api_key: str | None = None):
            """Get AI-powered analysis of a DataFrame."""
            ns = self.notebook.session._namespace if self.notebook.session._initialized else {}
            if variable_name not in ns:
                raise HTTPException(404, f"Variable '{variable_name}' not found")

            obj = ns[variable_name]
            type_name = type(obj).__name__
            if type_name != "DataFrame":
                raise HTTPException(400, "Only DataFrames can be analyzed")

            # Build a data profile summary for the LLM
            import pandas as pd
            df = obj
            profile = {
                "shape": list(df.shape),
                "columns": {},
                "missing_values": df.isnull().sum().to_dict(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            }
            for col in df.columns:
                col_info = {"dtype": str(df[col].dtype), "null_count": int(df[col].isnull().sum())}
                if pd.api.types.is_numeric_dtype(df[col]):
                    desc = df[col].describe()
                    col_info.update({
                        "mean": round(float(desc.get("mean", 0)), 4),
                        "std": round(float(desc.get("std", 0)), 4),
                        "min": round(float(desc.get("min", 0)), 4),
                        "max": round(float(desc.get("max", 0)), 4),
                        "unique": int(df[col].nunique()),
                    })
                else:
                    col_info.update({
                        "unique": int(df[col].nunique()),
                        "top_values": df[col].value_counts().head(5).to_dict(),
                    })
                profile["columns"][col] = col_info

            # Use stored AI config (prefer stored config over request params)
            ai_provider = self._ai_config.get("provider", provider)
            ai_model = self._ai_config.get("model") or None
            ai_base_url = self._ai_config.get("base_url") or None
            stored_key = self._ai_config.get("api_key")
            if stored_key:
                os.environ["OPENAI_API_KEY"] = stored_key
            elif api_key:
                os.environ["OPENAI_API_KEY"] = api_key

            prompt = f"""Analyze this dataset and provide:
1. **Data Quality Summary** — missing values, outliers, data type issues
2. **Key Insights** — interesting patterns, correlations, distributions
3. **Preprocessing Suggestions** — what to clean, transform, encode
4. **Feature Engineering Ideas** — new features to create
5. **ML Model Recommendations** — which models would work best and why

Dataset profile:
- Shape: {profile['shape'][0]} rows × {profile['shape'][1]} columns
- Columns: {json.dumps(profile['columns'], indent=2, default=str)}
"""
            try:
                from flowyml_notebook.ai.assistant import NotebookAIAssistant
                assistant = NotebookAIAssistant(
                    notebook=self.notebook,
                    provider=ai_provider,
                    model=ai_model,
                    base_url=ai_base_url,
                )
                response = assistant.chat(prompt)
                return {
                    "analysis": response.content,
                    "code": response.code,
                    "profile": profile,
                }
            except Exception as e:
                return {
                    "analysis": f"AI analysis requires an LLM provider. Error: {str(e)}",
                    "profile": profile,
                    "error": str(e),
                }

        @app.get("/api/completions")
        async def get_completions(code: str, cursor_pos: int | None = None):
            """Get code completions."""
            completions = []
            if self.notebook.session._ip:
                try:
                    text = code[:cursor_pos] if cursor_pos else code
                    _, matches = self.notebook.session._ip.complete(text)
                    completions = matches[:50]
                except Exception:
                    pass
            return {"completions": completions}

        # --- FlowyML Session Introspection ---

        @app.get("/api/flowyml/session-info")
        async def flowyml_session_info():
            """Introspect the current notebook session for FlowyML objects.

            Scans the live namespace for registered steps, pipelines, assets,
            experiments, and active tracking — letting users see what
            FlowyML objects they've created during this session.
            """
            ns = self.notebook.session._namespace if self.notebook.session else {}
            info: dict = {
                "steps": [],
                "pipelines": [],
                "assets": [],
                "experiments": [],
                "registries": [],
                "has_tracking": False,
            }

            for name, obj in ns.items():
                if name.startswith("_"):
                    continue
                obj_type = type(obj).__name__
                obj_module = type(obj).__module__ or ""

                # Registered steps (via @step decorator)
                if obj_type == "Step" or (hasattr(obj, "_flowyml_step") and obj._flowyml_step):
                    inputs = getattr(obj, "inputs", []) or []
                    outputs = getattr(obj, "outputs", []) or []
                    info["steps"].append({
                        "name": name,
                        "inputs": list(inputs)[:10],
                        "outputs": list(outputs)[:10],
                    })

                # Pipelines
                elif obj_type == "Pipeline":
                    step_names = []
                    if hasattr(obj, "steps"):
                        step_names = [
                            getattr(s, "name", str(s))
                            for s in (obj.steps or [])
                        ][:20]
                    info["pipelines"].append({
                        "name": getattr(obj, "name", name),
                        "steps": step_names,
                        "variable": name,
                    })

                # Assets (Dataset, Model, Metrics, etc.)
                elif "flowyml.assets" in obj_module or obj_type in (
                    "Dataset", "Model", "Metrics", "Artifact",
                    "FeatureSet", "Report", "Prompt", "Checkpoint",
                ):
                    asset_info = {"name": getattr(obj, "name", name), "type": obj_type, "variable": name}
                    if hasattr(obj, "shape"):
                        asset_info["shape"] = str(obj.shape)
                    elif hasattr(obj, "data") and hasattr(obj.data, "shape"):
                        asset_info["shape"] = str(obj.data.shape)
                    info["assets"].append(asset_info)

                # Experiments & Runs
                elif obj_type in ("Experiment", "Run"):
                    exp_info = {"name": getattr(obj, "name", name), "type": obj_type, "variable": name}
                    if hasattr(obj, "status"):
                        exp_info["status"] = str(obj.status)
                    info["experiments"].append(exp_info)
                    info["has_tracking"] = True

                # Model Registry
                elif obj_type == "ModelRegistry":
                    info["registries"].append({"variable": name})

            # Also check StepRegistry for globally registered steps
            try:
                from flowyml import get_registered_steps
                registered = get_registered_steps()
                existing_names = {s["name"] for s in info["steps"]}
                for s in registered:
                    sname = getattr(s, "name", str(s))
                    if sname not in existing_names:
                        info["steps"].append({
                            "name": sname,
                            "inputs": list(getattr(s, "inputs", []))[:10],
                            "outputs": list(getattr(s, "outputs", []))[:10],
                        })
            except Exception:
                pass

            info["total"] = (
                len(info["steps"]) + len(info["pipelines"])
                + len(info["assets"]) + len(info["experiments"])
            )
            return info

        @app.get("/api/flowyml/pipeline-graph")
        async def flowyml_pipeline_graph(variable: str = "pipe"):
            """Get the step DAG for a Pipeline object in the session.

            Returns the graph structure for rendering a mini pipeline
            visualization — reads from the live session, does not reimplement
            any FlowyML logic.
            """
            ns = self.notebook.session._namespace if self.notebook.session else {}
            obj = ns.get(variable)
            if obj is None:
                return {"error": f"Variable '{variable}' not found in session"}

            obj_type = type(obj).__name__
            if obj_type != "Pipeline":
                return {"error": f"'{variable}' is a {obj_type}, not a Pipeline"}

            nodes = []
            edges = []
            steps = getattr(obj, "steps", []) or []
            for i, s in enumerate(steps):
                sname = getattr(s, "name", f"step_{i}")
                outputs = list(getattr(s, "outputs", []))[:10]
                inputs = list(getattr(s, "inputs", []))[:10]
                nodes.append({"id": sname, "inputs": inputs, "outputs": outputs, "index": i})

            # Build edges from output → input matching
            output_map = {}
            for node in nodes:
                for out in node["outputs"]:
                    output_map[out] = node["id"]
            for node in nodes:
                for inp in node["inputs"]:
                    if inp in output_map and output_map[inp] != node["id"]:
                        edges.append({"from": output_map[inp], "to": node["id"], "artifact": inp})

            return {
                "name": getattr(obj, "name", variable),
                "nodes": nodes,
                "edges": edges,
            }

        # --- GitHub Sync Endpoints ---

        @app.post("/api/github/init")
        async def github_init(repo_url: str, local_path: str | None = None, flowyml_url: str | None = None):
            """Initialize or connect to a GitHub repository."""
            try:
                result = self.github_sync.init_repo(repo_url, local_path, flowyml_url)
                return result
            except Exception as e:
                raise HTTPException(500, str(e))

        @app.get("/api/github/status")
        async def github_status():
            """Get git status for the current repository."""
            return self.github_sync.get_status()

        @app.get("/api/github/config")
        async def github_config():
            """Get GitHub sync configuration."""
            return self.github_sync.get_config()

        @app.post("/api/github/push")
        async def github_push(
            project: str = "default",
            experiment: str = "main",
            message: str | None = None,
        ):
            """Push current notebook to GitHub. Also syncs comments and reviews."""
            state = self.notebook.get_state()
            nb_data = state.get("notebook", {})
            result = self.github_sync.push_notebook(project, experiment, nb_data, message)
            # Auto-sync comments and reviews on push
            if self._comments:
                self.github_sync.push_comments(project, experiment, self._comments)
            if self._reviews:
                for review in self._reviews:
                    self.github_sync.push_review(project, experiment, review)
            return result

        @app.post("/api/github/pull")
        async def github_pull(project: str = "default", experiment: str = "main"):
            """Pull notebook from GitHub. Also syncs comments and reviews."""
            data = self.github_sync.pull_notebook(project, experiment)
            if not data:
                raise HTTPException(404, "Notebook not found in repository")
            self.notebook.load_from_dict(data)
            # Auto-sync comments and reviews on pull
            remote_comments = self.github_sync.pull_comments(project, experiment)
            self._comments = self.github_sync.merge_comments(self._comments, remote_comments)
            self._reviews = self.github_sync.pull_reviews(project, experiment)
            return self.notebook.get_state()

        @app.get("/api/github/branches")
        async def github_branches():
            """List branches."""
            return self.github_sync.list_branches()

        @app.post("/api/github/branch")
        async def github_create_branch(name: str, checkout: bool = True):
            """Create or switch branch."""
            return self.github_sync.create_branch(name, checkout)

        @app.put("/api/github/branch")
        async def github_switch_branch(name: str):
            """Switch to an existing branch."""
            return self.github_sync.switch_branch(name)

        @app.delete("/api/github/branch")
        async def github_delete_branch(name: str, force: bool = False):
            """Delete a local branch."""
            return self.github_sync.delete_branch(name, force)

        @app.get("/api/github/projects")
        async def github_projects():
            """List projects in the repository."""
            return {"projects": self.github_sync.list_projects()}

        # --- GitHub: Merge & Conflict Resolution ---

        @app.get("/api/github/merge-status")
        async def github_merge_status():
            """Check for upstream changes before push (ahead/behind/conflict)."""
            return self.github_sync.check_merge_status()

        @app.post("/api/github/pull-rebase")
        async def github_pull_rebase():
            """Pull with rebase — safe for collaboration."""
            return self.github_sync.pull_with_rebase()

        @app.post("/api/github/stash")
        async def github_stash(message: str | None = None):
            """Stash local changes (work-in-progress)."""
            return self.github_sync.stash_changes(message)

        @app.post("/api/github/stash/pop")
        async def github_stash_pop():
            """Pop the most recent stash."""
            return self.github_sync.pop_stash()

        @app.get("/api/github/stash/list")
        async def github_stash_list():
            """List all stashes."""
            return {"stashes": self.github_sync.list_stashes()}

        # --- GitHub: Rich History & Activity ---

        @app.get("/api/github/log")
        async def github_commit_log(limit: int = 30):
            """Get rich commit history with author avatars and stats."""
            return {"commits": self.github_sync.get_commit_log(limit)}

        @app.get("/api/github/activity")
        async def github_activity_feed(limit: int = 50):
            """Get unified team activity feed (commits + comments + reviews)."""
            return {"feed": self.github_sync.get_activity_feed(limit)}

        @app.get("/api/github/diff-summary/{commit_sha}")
        async def github_diff_summary(commit_sha: str):
            """Get cell-level change summary for a commit."""
            return self.github_sync.get_commit_diff_summary(commit_sha)

        # --- GitHub: Team Presence ---

        @app.get("/api/github/presence")
        async def github_get_presence():
            """Get list of active editors."""
            return {"editors": self.github_sync.get_active_editors()}

        @app.post("/api/github/presence")
        async def github_set_presence(notebook: str = "default", editing: bool = True):
            """Set editing status for the current user."""
            return self.github_sync.set_editing_status(notebook, editing)

        # --- Comments & Collaboration (Git-Persisted) ---

        @app.get("/api/comments")
        async def list_comments():
            """List all comments for the current notebook."""
            return {"comments": self._comments}

        @app.post("/api/comments")
        async def add_comment(comment: dict):
            """Add a comment (cell-level or notebook-level) with rich features."""
            import uuid
            git_user = self.github_sync._get_git_user(
                str(self.github_sync.repo_path)
            ) if self.github_sync.repo_path else {"name": "Local User", "email": ""}
            new_comment = {
                "id": str(uuid.uuid4())[:8],
                "cell_id": comment.get("cell_id"),
                "text": comment.get("text", ""),
                "author": git_user,
                "created_at": datetime.now().isoformat(),
                "resolved": False,
                "replies": [],
                "reactions": {},
                "priority": comment.get("priority", "normal"),
                "line_range": comment.get("line_range"),
                "mentions": comment.get("mentions", []),
                "synced": False,
            }
            self._comments.append(new_comment)
            return new_comment

        @app.put("/api/comments/{comment_id}/resolve")
        async def resolve_comment(comment_id: str):
            """Toggle resolved status on a comment."""
            for c in self._comments:
                if c["id"] == comment_id:
                    c["resolved"] = not c["resolved"]
                    return c
            raise HTTPException(404, "Comment not found")

        @app.delete("/api/comments/{comment_id}")
        async def delete_comment(comment_id: str):
            """Delete a comment."""
            self._comments = [c for c in self._comments if c["id"] != comment_id]
            return {"deleted": True}

        @app.post("/api/comments/{comment_id}/reply")
        async def reply_to_comment(comment_id: str, reply: dict):
            """Add a reply to a comment thread."""
            git_user = self.github_sync._get_git_user(
                str(self.github_sync.repo_path)
            ) if self.github_sync.repo_path else {"name": "Local User", "email": ""}
            for c in self._comments:
                if c["id"] == comment_id:
                    c["replies"].append({
                        "id": str(__import__("uuid").uuid4())[:8],
                        "text": reply.get("text", ""),
                        "author": git_user,
                        "created_at": datetime.now().isoformat(),
                        "reactions": {},
                    })
                    return c
            raise HTTPException(404, "Comment not found")

        @app.post("/api/comments/{comment_id}/react")
        async def react_to_comment(comment_id: str, emoji: str = "👍"):
            """Add an emoji reaction to a comment."""
            git_user = self.github_sync._get_git_user(
                str(self.github_sync.repo_path)
            ) if self.github_sync.repo_path else {"name": "Local User", "email": ""}
            user_name = git_user.get("name", "Local User")
            for c in self._comments:
                if c["id"] == comment_id:
                    reactions = c.get("reactions", {})
                    if emoji not in reactions:
                        reactions[emoji] = []
                    if user_name in reactions[emoji]:
                        reactions[emoji].remove(user_name)
                    else:
                        reactions[emoji].append(user_name)
                    c["reactions"] = reactions
                    return c
            raise HTTPException(404, "Comment not found")

        @app.post("/api/comments/sync")
        async def sync_comments(project: str = "default", experiment: str = "main"):
            """Sync comments to/from Git repository."""
            remote = self.github_sync.pull_comments(project, experiment)
            self._comments = self.github_sync.merge_comments(self._comments, remote)
            result = self.github_sync.push_comments(project, experiment, self._comments)
            for c in self._comments:
                c["synced"] = True
            return {"synced": result.get("synced", False), "count": len(self._comments)}

        # --- Reviews (Git-Persisted) ---

        @app.get("/api/reviews")
        async def list_reviews():
            """List all reviews for the current notebook."""
            return {"reviews": self._reviews}

        @app.post("/api/reviews")
        async def request_review(review: dict):
            """Request a review for the current notebook (PR-like workflow)."""
            import uuid
            git_user = self.github_sync._get_git_user(
                str(self.github_sync.repo_path)
            ) if self.github_sync.repo_path else {"name": "Local User", "email": ""}
            new_review = {
                "id": str(uuid.uuid4())[:8],
                "requested_by": git_user,
                "reviewers": review.get("reviewers", []),
                "status": "pending",
                "title": review.get("title", "Notebook Review"),
                "description": review.get("description", ""),
                "comments": review.get("comments", ""),
                "created_at": datetime.now().isoformat(),
                "resolved_at": None,
                "branch": review.get("branch"),
                "cell_ids": review.get("cell_ids", []),
                "review_comments": [],
            }
            self._reviews.append(new_review)
            return new_review

        @app.put("/api/reviews/{review_id}")
        async def update_review(review_id: str, update: dict):
            """Approve, request changes, or close a review."""
            git_user = self.github_sync._get_git_user(
                str(self.github_sync.repo_path)
            ) if self.github_sync.repo_path else {"name": "Local User", "email": ""}
            for r in self._reviews:
                if r["id"] == review_id:
                    r["status"] = update.get("status", r["status"])
                    if update.get("comments"):
                        r["comments"] = update["comments"]
                    if update.get("review_comment"):
                        r.setdefault("review_comments", []).append({
                            "author": git_user,
                            "text": update["review_comment"],
                            "status": update.get("status", "comment"),
                            "created_at": datetime.now().isoformat(),
                        })
                    if r["status"] in ("approved", "rejected", "changes_requested"):
                        r["resolved_at"] = datetime.now().isoformat()
                        r["reviewer"] = git_user
                    return r
            raise HTTPException(404, "Review not found")

        @app.post("/api/reviews/sync")
        async def sync_reviews(project: str = "default", experiment: str = "main"):
            """Sync reviews to/from Git repository."""
            for review in self._reviews:
                self.github_sync.push_review(project, experiment, review)
            self._reviews = self.github_sync.pull_reviews(project, experiment)
            return {"synced": True, "count": len(self._reviews)}

        # --- User Profile ---

        @app.get("/api/user/profile")
        async def get_user_profile():
            """Get the current user's profile (from git config)."""
            git_user = self.github_sync._get_git_user(
                str(self.github_sync.repo_path)
            ) if self.github_sync.repo_path else {"name": "Local User", "email": ""}
            # Generate a consistent avatar color from the user's name
            name = git_user.get("name", "User")
            hue = sum(ord(c) for c in name) * 37 % 360
            return {
                "name": name,
                "email": git_user.get("email", ""),
                "avatar_color": f"hsl({hue}, 60%, 45%)",
                "avatar_hue": hue,
                "initials": name[0].upper() if name else "U",
            }

        # --- Recipe Endpoints (Enhanced with Ratings, Forking, Leaderboard) ---

        @app.get("/api/recipes")
        async def list_recipes():
            """List all recipes (local custom + shared from GitHub)."""
            local = self.recipe_store.list_recipes()
            shared = []
            try:
                shared = self.github_sync.pull_recipes()
            except Exception:
                pass
            # Merge, avoiding duplicates by id
            seen_ids = {r["id"] for r in local}
            combined = local + [r for r in shared if r.get("id") not in seen_ids]
            return {
                "recipes": combined,
                "usage": self.recipe_store.get_all_usage(),
            }

        @app.post("/api/recipes")
        async def save_recipe(recipe: dict):
            """Save a custom recipe."""
            saved = self.recipe_store.save_recipe(recipe)
            return saved

        @app.delete("/api/recipes/{recipe_id}")
        async def delete_recipe(recipe_id: str):
            """Delete a custom recipe."""
            if not self.recipe_store.delete_recipe(recipe_id):
                raise HTTPException(404, "Recipe not found")
            return {"deleted": True}

        @app.post("/api/recipes/{recipe_id}/use")
        async def track_recipe_usage(recipe_id: str):
            """Track usage of a recipe."""
            count = self.recipe_store.track_usage(recipe_id)
            return {"recipe_id": recipe_id, "usage_count": count}

        @app.post("/api/recipes/share/{recipe_id}")
        async def share_recipe(recipe_id: str):
            """Share a recipe to the GitHub repository."""
            recipe = self.recipe_store.get_recipe(recipe_id)
            if not recipe:
                raise HTTPException(404, "Recipe not found")
            result = self.github_sync.push_recipe(recipe)
            return result

        @app.post("/api/recipes/{recipe_id}/rate")
        async def rate_recipe(recipe_id: str, rating: int = 5):
            """Rate a shared recipe (1-5 stars)."""
            return self.github_sync.rate_recipe(recipe_id, rating)

        @app.post("/api/recipes/{recipe_id}/fork")
        async def fork_recipe(recipe_id: str, new_name: str | None = None):
            """Fork a shared recipe to create a variant with attribution."""
            return self.github_sync.fork_recipe(recipe_id, new_name)

        @app.get("/api/recipes/{recipe_id}/history")
        async def recipe_history(recipe_id: str):
            """Get version history for a recipe."""
            return {"history": self.github_sync.get_recipe_history(recipe_id)}

        @app.get("/api/recipes/leaderboard")
        async def recipe_leaderboard():
            """Get top-rated and most-forked recipes."""
            return self.github_sync.get_recipe_leaderboard()

        @app.post("/api/recipes/import")
        async def import_recipes(recipes: list[dict], overwrite: bool = False):
            """Import recipes from a JSON list."""
            count = self.recipe_store.import_recipes(recipes, overwrite)
            return {"imported": count}

        @app.get("/api/recipes/export")
        async def export_recipes():
            """Export all custom recipes as JSON."""
            return {"recipes": self.recipe_store.export_all()}

        # --- WebSocket for real-time kernel ---

        @app.websocket("/ws/kernel")
        async def kernel_websocket(websocket: WebSocket):
            """WebSocket endpoint for real-time kernel communication."""
            await websocket.accept()
            logger.info("Kernel WebSocket connected")

            try:
                while True:
                    message = await websocket.receive_text()
                    await self.kernel.handle_message(websocket, message)
            except WebSocketDisconnect:
                logger.info("Kernel WebSocket disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)

        # --- Frontend Serving ---

        frontend_dir = Path(__file__).parent / "frontend" / "dist"
        if frontend_dir.exists():
            app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="assets")

            @app.get("/{path:path}")
            async def serve_frontend(path: str = ""):
                """Serve the frontend SPA."""
                file_path = frontend_dir / path
                if file_path.is_file():
                    return FileResponse(file_path)
                return FileResponse(frontend_dir / "index.html")
        else:
            @app.get("/")
            async def dev_index():
                """Development placeholder when frontend isn't built."""
                return HTMLResponse(_DEV_PLACEHOLDER)

        return app

    def run(self) -> None:
        """Start the server."""
        uvicorn.run(self.app, host="0.0.0.0", port=self.port, log_level="warning")


def create_app_server(notebook: Notebook, app_mode: Any = None) -> FastAPI:
    """Create a standalone app server for notebook-as-app deployment."""
    server = NotebookServer(notebook)
    return server.app


def dev_app_factory() -> FastAPI:
    """Factory function for uvicorn --factory in dev mode.

    Reads config from environment variables set by the DevServer orchestrator.
    This allows uvicorn to recreate the app on each reload.
    """
    import os

    name = os.environ.get("FLOWYML_NB_NAME", "untitled")
    file_path = os.environ.get("FLOWYML_NB_FILE", "") or None
    server_url = os.environ.get("FLOWYML_NB_SERVER", "") or None

    nb = Notebook(name=name, server=server_url, file_path=file_path)

    if server_url:
        try:
            nb.connect(server_url)
        except Exception:
            pass  # Continue in local mode

    srv = NotebookServer(nb)
    return srv.app


def _compute_diff_lines(old_lines: list, new_lines: list) -> list:
    """Simple line-by-line diff for version control."""
    result = []
    old_set = set(old_lines)
    new_set = set(new_lines)

    max_len = max(len(old_lines), len(new_lines))
    for i in range(max_len):
        old = old_lines[i] if i < len(old_lines) else None
        new = new_lines[i] if i < len(new_lines) else None

        if old == new:
            result.append({"type": "context", "content": old})
        else:
            if old is not None:
                result.append({"type": "remove", "content": old})
            if new is not None:
                result.append({"type": "add", "content": new})

    return result


def _safe_serialize(value: Any) -> Any:
    """Safely serialize a value for JSON output."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_serialize(v) for v in value[:10]]
    if isinstance(value, dict):
        return {str(k): _safe_serialize(v) for k, v in list(value.items())[:10]}
    return str(value)


def _format_size(size_bytes: int | float) -> str:
    """Format bytes to human-readable string."""
    size_bytes = int(size_bytes)
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


_DEV_PLACEHOLDER = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>FlowyML Notebook</title>
    <style>
        body { background: #0f172a; color: #e2e8f0; font-family: system-ui; display: flex;
               align-items: center; justify-content: center; min-height: 100vh; }
        .msg { text-align: center; }
        h1 { font-size: 2rem; margin-bottom: 1rem;
             background: linear-gradient(135deg, #3b82f6, #8b5cf6);
             -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { color: #94a3b8; }
        code { background: #1e293b; padding: 0.25rem 0.5rem; border-radius: 6px; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="msg">
        <h1>🌊 FlowyML Notebook</h1>
        <p>Frontend not built yet. Run:</p>
        <p><code>cd flowyml-notebook/flowyml_notebook/frontend && npm install && npm run build</code></p>
        <p style="margin-top: 1rem">API is running at <code>/api/state</code></p>
    </div>
</body>
</html>"""

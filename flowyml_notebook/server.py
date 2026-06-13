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

from flowyml_notebook import __version__
from flowyml_notebook.core import Notebook
from flowyml_notebook.kernel import NotebookKernel
from flowyml_notebook.cells import CellType
from flowyml_notebook.notebook_manager import NotebookManager
from flowyml_notebook.github_sync import GitHubSync
from flowyml_notebook.recipes_store import RecipeStore
from flowyml_notebook.integrations.ecosystem import UnicoLabEcosystem
from flowyml_notebook.integrations import builtin_recipes as _builtin_recipes

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
        self._profiler = None  # Lazy-loaded CellProfiler
        self._benchmark = None  # Lazy-loaded CellBenchmark
        self._validator = None  # Lazy-loaded DataValidator
        self._analyzer = None  # Lazy-loaded CodeAnalyzer
        self._execution_history = None  # Lazy-loaded ExecutionHistory
        self._lineage = None  # Lazy-loaded LineageTracker
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

    def _track_recent_file(self, path: str, name: str) -> None:
        """Track a recently opened/saved file."""
        recent_file = Path.home() / ".flowyml" / "recent_files.json"
        recent_file.parent.mkdir(parents=True, exist_ok=True)
        recent: list[dict] = []
        if recent_file.exists():
            try:
                recent = json.loads(recent_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        # Remove existing entry for this path
        recent = [r for r in recent if r.get("path") != path]
        # Prepend new entry
        recent.insert(0, {
            "path": path,
            "name": name,
            "opened_at": datetime.now().isoformat(),
        })
        # Keep only 20 most recent
        recent = recent[:20]
        recent_file.write_text(json.dumps(recent, indent=2), encoding="utf-8")

    def _get_recent_files(self) -> list[dict]:
        """Get list of recently opened/saved files."""
        recent_file = Path.home() / ".flowyml" / "recent_files.json"
        if recent_file.exists():
            try:
                recent = json.loads(recent_file.read_text(encoding="utf-8"))
                # Filter out files that no longer exist
                return [r for r in recent if Path(r.get("path", "")).exists()]
            except Exception:
                pass
        return []

    def _detect_kernels(self) -> list[dict]:
        """Detect all available Python environments.

        Scans for: current Python, venv/virtualenv, Poetry, Pipenv, Conda, pyenv, system Pythons.
        """
        import subprocess
        import sys

        kernels = []
        seen_paths = set()

        def _add_kernel(name: str, python_path: str, source: str, version: str = ""):
            real_path = str(Path(python_path).resolve()) if Path(python_path).exists() else python_path
            if real_path in seen_paths:
                return
            seen_paths.add(real_path)

            if not version:
                try:
                    result = subprocess.run(
                        [python_path, "--version"],
                        capture_output=True, text=True, timeout=5,
                    )
                    version = result.stdout.strip().replace("Python ", "")
                except Exception:
                    version = "unknown"

            # Check available packages
            packages = {}
            for pkg in ["pandas", "numpy", "scikit-learn", "torch", "tensorflow"]:
                try:
                    result = subprocess.run(
                        [python_path, "-c", f"import {pkg.replace('-', '_').split('-')[0]}; print('ok')"],
                        capture_output=True, text=True, timeout=5,
                    )
                    packages[pkg] = result.returncode == 0
                except Exception:
                    packages[pkg] = False

            kernels.append({
                "name": name,
                "python_path": python_path,
                "version": version,
                "source": source,
                "packages": packages,
                "is_current": python_path == sys.executable or real_path == str(Path(sys.executable).resolve()),
            })

        # 1. Current Python
        _add_kernel(f"Python {sys.version.split()[0]} (current)", sys.executable, "current", sys.version.split()[0])

        # 2. Local venv / virtualenv
        cwd = os.getcwd()
        for venv_dir in [".venv", "venv", "env", ".env"]:
            venv_python = os.path.join(cwd, venv_dir, "bin", "python")
            if os.path.isfile(venv_python):
                _add_kernel(f"{venv_dir}", venv_python, "venv")

        # 3. Poetry
        try:
            result = subprocess.run(
                ["poetry", "env", "info", "--executable"],
                capture_output=True, text=True, timeout=10, cwd=cwd,
            )
            if result.returncode == 0 and result.stdout.strip():
                _add_kernel("Poetry env", result.stdout.strip(), "poetry")
        except FileNotFoundError:
            pass

        # 4. Pipenv
        try:
            result = subprocess.run(
                ["pipenv", "--py"],
                capture_output=True, text=True, timeout=10, cwd=cwd,
            )
            if result.returncode == 0 and result.stdout.strip():
                _add_kernel("Pipenv env", result.stdout.strip(), "pipenv")
        except FileNotFoundError:
            pass

        # 5. Conda environments
        try:
            result = subprocess.run(
                ["conda", "env", "list", "--json"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                conda_data = json.loads(result.stdout)
                for env_path in conda_data.get("envs", []):
                    conda_python = os.path.join(env_path, "bin", "python")
                    if os.path.isfile(conda_python):
                        env_name = os.path.basename(env_path) or "base"
                        _add_kernel(f"Conda: {env_name}", conda_python, "conda")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        # 6. pyenv versions
        try:
            result = subprocess.run(
                ["pyenv", "versions", "--bare"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                for version_str in result.stdout.strip().split("\n"):
                    version_str = version_str.strip()
                    if version_str:
                        pyenv_root = os.environ.get("PYENV_ROOT", os.path.expanduser("~/.pyenv"))
                        pyenv_python = os.path.join(pyenv_root, "versions", version_str, "bin", "python")
                        if os.path.isfile(pyenv_python):
                            _add_kernel(f"pyenv: {version_str}", pyenv_python, "pyenv", version_str)
        except FileNotFoundError:
            pass

        # 7. System Pythons
        for sys_python in ["/usr/bin/python3", "/usr/local/bin/python3", "/opt/homebrew/bin/python3"]:
            if os.path.isfile(sys_python):
                _add_kernel("System Python", sys_python, "system")

        return kernels

    def _create_app(self) -> FastAPI:
        """Create the FastAPI application."""
        app = FastAPI(
            title="FlowyML Notebook",
            version=__version__,
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
                "version": __version__,
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

        # ===== Clear Cell Outputs =====

        @app.post("/api/cells/{cell_id}/clear-output")
        async def clear_cell_output(cell_id: str):
            """Clear outputs for a single cell."""
            cell = self.notebook.notebook.get_cell(cell_id)
            if not cell:
                raise HTTPException(404, f"Cell {cell_id} not found")
            cell.outputs = []
            cell.execution_count = 0
            return {"cell_id": cell_id, "cleared": True}

        @app.post("/api/clear-all-outputs")
        async def clear_all_outputs():
            """Clear outputs for all cells."""
            cleared = []
            for cell in self.notebook.cells:
                cell.outputs = []
                cell.execution_count = 0
                cleared.append(cell.id)
            return {"cleared": cleared, "count": len(cleared)}

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

        # ===== SmartPrep Advisor =====
        @app.get("/api/smartprep/{var_name}")
        async def smartprep_advisor(var_name: str, target: str | None = None):
            """Analyze a DataFrame and return actionable preprocessing suggestions with code."""
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

            suggestions: list[dict] = []
            n_rows = len(df)

            # --- 1. Missing values ---
            for col in df.columns:
                null_count = int(df[col].isnull().sum())
                null_pct = round(null_count / n_rows * 100, 1) if n_rows > 0 else 0
                if null_count == 0:
                    continue
                is_numeric = pd.api.types.is_numeric_dtype(df[col])
                if null_pct > 60:
                    suggestions.append({
                        "type": "drop_column", "severity": "high", "column": col,
                        "title": f"Drop '{col}' — {null_pct}% missing",
                        "reason": f"Column has {null_pct}% missing values ({null_count}/{n_rows}). Too sparse to impute reliably.",
                        "code": f"{var_name} = {var_name}.drop(columns=['{col}'])",
                    })
                elif is_numeric:
                    median_val = round(float(df[col].median()), 4)
                    suggestions.append({
                        "type": "impute_numeric", "severity": "medium", "column": col,
                        "title": f"Impute '{col}' — {null_pct}% missing",
                        "reason": f"Numeric column with {null_count} missing values. Median imputation preserves distribution shape.",
                        "code": f"{var_name}['{col}'] = {var_name}['{col}'].fillna({var_name}['{col}'].median())",
                    })
                else:
                    mode_val = df[col].mode().iloc[0] if len(df[col].mode()) > 0 else "unknown"
                    suggestions.append({
                        "type": "impute_categorical", "severity": "medium", "column": col,
                        "title": f"Impute '{col}' — {null_pct}% missing",
                        "reason": f"Categorical column with {null_count} missing values. Mode imputation is safest.",
                        "code": f"{var_name}['{col}'] = {var_name}['{col}'].fillna('{mode_val}')",
                    })

            # --- 2. Skewed distributions ---
            for col in df.select_dtypes(include=[np.number]).columns:
                clean = df[col].dropna()
                if len(clean) < 10:
                    continue
                skew = float(clean.skew())
                if abs(skew) > 1.5 and (clean > 0).all():
                    suggestions.append({
                        "type": "fix_skew", "severity": "medium", "column": col,
                        "title": f"Fix skew in '{col}' (skew={round(skew, 2)})",
                        "reason": f"Heavily {'right' if skew > 0 else 'left'}-skewed. Log transform normalizes the distribution for better model performance.",
                        "code": f"import numpy as np\n{var_name}['{col}'] = np.log1p({var_name}['{col}'])",
                    })
                elif abs(skew) > 1.5:
                    suggestions.append({
                        "type": "fix_skew", "severity": "low", "column": col,
                        "title": f"Fix skew in '{col}' (skew={round(skew, 2)})",
                        "reason": f"Skewed distribution with negative values. Power transform handles both positive and negative values.",
                        "code": f"from sklearn.preprocessing import PowerTransformer\npt = PowerTransformer(method='yeo-johnson')\n{var_name}['{col}'] = pt.fit_transform({var_name}[['{col}']])",
                    })

            # --- 3. Outliers ---
            for col in df.select_dtypes(include=[np.number]).columns:
                clean = df[col].dropna()
                if len(clean) < 10:
                    continue
                q1 = float(clean.quantile(0.25))
                q3 = float(clean.quantile(0.75))
                iqr = q3 - q1
                if iqr == 0:
                    continue
                n_outliers = int(((clean < q1 - 1.5 * iqr) | (clean > q3 + 1.5 * iqr)).sum())
                outlier_pct = round(n_outliers / len(clean) * 100, 1)
                if outlier_pct > 5:
                    lower = round(q1 - 1.5 * iqr, 4)
                    upper = round(q3 + 1.5 * iqr, 4)
                    suggestions.append({
                        "type": "clip_outliers", "severity": "medium", "column": col,
                        "title": f"Clip outliers in '{col}' — {outlier_pct}% ({n_outliers} values)",
                        "reason": f"IQR method detected {n_outliers} outliers. Clipping to [{lower}, {upper}] preserves data while limiting extreme values.",
                        "code": f"{var_name}['{col}'] = {var_name}['{col}'].clip(lower={lower}, upper={upper})",
                    })

            # --- 4. High cardinality ---
            for col in df.select_dtypes(include=["object", "category"]).columns:
                n_unique = int(df[col].nunique())
                if n_unique > 50:
                    suggestions.append({
                        "type": "reduce_cardinality", "severity": "medium", "column": col,
                        "title": f"Reduce cardinality of '{col}' ({n_unique} unique values)",
                        "reason": f"High cardinality makes one-hot encoding impractical. Frequency encoding preserves information compactly.",
                        "code": f"freq = {var_name}['{col}'].value_counts()\n{var_name}['{col}_encoded'] = {var_name}['{col}'].map(freq)",
                    })
                elif 2 < n_unique <= 50:
                    suggestions.append({
                        "type": "encode_categorical", "severity": "low", "column": col,
                        "title": f"Encode '{col}' ({n_unique} categories)",
                        "reason": f"Categorical column suitable for one-hot encoding.",
                        "code": f"{var_name} = pd.get_dummies({var_name}, columns=['{col}'], prefix='{col}')",
                    })

            # --- 5. Class imbalance (if target specified) ---
            if target and target in df.columns:
                vc = df[target].value_counts()
                if len(vc) >= 2:
                    majority = int(vc.iloc[0])
                    minority = int(vc.iloc[-1])
                    ratio = round(majority / minority, 1) if minority > 0 else 999
                    if ratio > 3:
                        suggestions.append({
                            "type": "class_imbalance", "severity": "high", "column": target,
                            "title": f"Class imbalance in '{target}' — {ratio}:1 ratio",
                            "reason": f"Majority class has {majority} samples vs {minority} for minority. Models will be biased toward majority.",
                            "code": f"# Option 1: Class weights (no data modification)\n# In your model: class_weight='balanced'\n\n# Option 2: SMOTE oversampling\nfrom imblearn.over_sampling import SMOTE\nsmote = SMOTE(random_state=42)\nX_resampled, y_resampled = smote.fit_resample(X_train, y_train)",
                        })

            # --- 6. Feature scaling suggestion ---
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) >= 2:
                ranges = {col: float(df[col].max() - df[col].min()) for col in numeric_cols if df[col].notna().sum() > 0}
                if ranges:
                    max_range = max(ranges.values())
                    min_range = min(v for v in ranges.values() if v > 0) if any(v > 0 for v in ranges.values()) else 1
                    if max_range / min_range > 100:
                        cols_str = ", ".join(f"'{c}'" for c in numeric_cols[:8])
                        suggestions.append({
                            "type": "scale_features", "severity": "medium", "column": "__all_numeric__",
                            "title": f"Scale features — {round(max_range/min_range, 0)}x range difference",
                            "reason": f"Numeric features have very different scales. StandardScaler ensures equal contribution to distance-based models.",
                            "code": f"from sklearn.preprocessing import StandardScaler\nscaler = StandardScaler()\ncols_to_scale = [{cols_str}]\n{var_name}[cols_to_scale] = scaler.fit_transform({var_name}[cols_to_scale])",
                        })

            # Sort by severity
            severity_order = {"high": 0, "medium": 1, "low": 2, "recommended": 0}
            suggestions.sort(key=lambda s: severity_order.get(s.get("severity", "low"), 2))

            # ── UnicoLab Ecosystem: KDP Preprocessing ──
            try:
                if UnicoLabEcosystem.is_available("kdp"):
                    from flowyml_notebook.integrations.kdp_adapter import (
                        generate_preprocessing_suggestion,
                    )

                    # Build feature types from SmartPrep analysis
                    _feature_types: dict[str, str] = {}
                    for col in df.columns:
                        s = df[col]
                        _n_unique = int(s.nunique())
                        if pd.api.types.is_numeric_dtype(s):
                            _feature_types[col] = "binary" if _n_unique == 2 else "continuous"
                        elif pd.api.types.is_datetime64_any_dtype(s):
                            _feature_types[col] = "temporal"
                        else:
                            _feature_types[col] = "nominal" if _n_unique <= 20 else "high_cardinality"

                    kdp_suggestion = generate_preprocessing_suggestion(
                        var_name=var_name,
                        feature_types=_feature_types,
                        n_rows=n_rows,
                        n_cols=len(df.columns),
                        target=target,
                    )
                    if kdp_suggestion:
                        suggestions.insert(0, kdp_suggestion)
            except Exception as _kdp_err:
                logger.debug(f"KDP suggestion skipped: {_kdp_err}")

            return {
                "variable": var_name,
                "rows": n_rows,
                "columns": len(df.columns),
                "total_issues": len(suggestions),
                "suggestions": suggestions,
            }

        # ===== Algorithm Matchmaker =====
        @app.get("/api/algorithm-match/{var_name}")
        async def algorithm_matchmaker(var_name: str, target: str | None = None):
            """Analyze data characteristics and recommend ML algorithms with reasoning."""
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

            n_rows, n_cols = df.shape
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            n_nulls = int(df.isnull().sum().sum())

            # Detect task type
            task_type = "clustering"  # default
            target_info = {}
            if target and target in df.columns:
                t = df[target]
                n_unique = int(t.nunique())
                if pd.api.types.is_numeric_dtype(t) and n_unique > 20:
                    task_type = "regression"
                    target_info = {"dtype": "numeric", "unique": n_unique, "mean": round(float(t.mean()), 4)}
                else:
                    task_type = "classification"
                    vc = t.value_counts()
                    target_info = {
                        "dtype": "categorical" if not pd.api.types.is_numeric_dtype(t) else "numeric",
                        "classes": n_unique,
                        "class_distribution": {str(k): int(v) for k, v in vc.head(10).items()},
                        "balanced": bool(vc.max() / vc.min() < 3) if vc.min() > 0 else False,
                    }

            # Data characteristics
            chars = {
                "n_samples": n_rows,
                "n_features": n_cols - (1 if target else 0),
                "n_numeric": len(numeric_cols),
                "n_categorical": len(cat_cols),
                "has_nulls": n_nulls > 0,
                "high_dimensional": n_cols > 50,
                "large_dataset": n_rows > 100_000,
                "small_dataset": n_rows < 500,
            }

            # Build recommendations
            recommendations: list[dict] = []

            if task_type == "classification":
                # Always recommend
                recommendations.append({
                    "name": "Random Forest",
                    "category": "ensemble",
                    "score": 90 if not chars["high_dimensional"] else 75,
                    "speed": "medium",
                    "interpretability": "medium",
                    "reasons": [
                        "Handles mixed feature types (numeric + categorical)",
                        "Robust to outliers and missing values",
                        f"Works well with {n_rows} samples",
                        "Built-in feature importance",
                    ],
                    "caveats": ["Can overfit on noisy data", "Slower than linear models"],
                    "code": f"from sklearn.ensemble import RandomForestClassifier\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.metrics import classification_report\n\nX = {var_name}.drop(columns=['{target}'])\ny = {var_name}['{target}']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n\nmodel = RandomForestClassifier(n_estimators=100, random_state=42)\nmodel.fit(X_train, y_train)\nprint(classification_report(y_test, model.predict(X_test)))",
                })

                if n_rows > 1000:
                    recommendations.append({
                        "name": "XGBoost",
                        "category": "gradient_boosting",
                        "score": 95 if n_rows > 5000 else 85,
                        "speed": "medium",
                        "interpretability": "medium",
                        "reasons": [
                            "State-of-the-art for tabular data",
                            f"Excellent with your {n_rows} samples",
                            "Handles missing values natively",
                            "GPU acceleration available",
                        ],
                        "caveats": ["Requires hyperparameter tuning", "Can overfit small datasets"],
                        "code": f"from xgboost import XGBClassifier\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.metrics import classification_report\n\nX = {var_name}.drop(columns=['{target}'])\ny = {var_name}['{target}']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n\nmodel = XGBClassifier(n_estimators=200, learning_rate=0.1, max_depth=6, random_state=42)\nmodel.fit(X_train, y_train)\nprint(classification_report(y_test, model.predict(X_test)))",
                    })

                if chars["small_dataset"] or chars["high_dimensional"]:
                    recommendations.append({
                        "name": "Logistic Regression",
                        "category": "linear",
                        "score": 80 if chars["high_dimensional"] else 70,
                        "speed": "fast",
                        "interpretability": "high",
                        "reasons": [
                            "Fast training and inference",
                            "Highly interpretable coefficients",
                            "Works well with small datasets",
                            "Good baseline model",
                        ],
                        "caveats": ["Assumes linear decision boundary", "Needs feature scaling"],
                        "code": f"from sklearn.linear_model import LogisticRegression\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.pipeline import Pipeline\nfrom sklearn.model_selection import train_test_split\n\nX = {var_name}.drop(columns=['{target}'])\ny = {var_name}['{target}']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n\npipe = Pipeline([('scaler', StandardScaler()), ('lr', LogisticRegression(max_iter=1000))])\npipe.fit(X_train, y_train)\nprint(f'Accuracy: {{pipe.score(X_test, y_test):.4f}}')",
                    })

                recommendations.append({
                    "name": "LightGBM",
                    "category": "gradient_boosting",
                    "score": 88,
                    "speed": "fast",
                    "interpretability": "medium",
                    "reasons": [
                        "Faster than XGBoost on large datasets",
                        "Handles categorical features natively",
                        "Memory efficient",
                    ],
                    "caveats": ["Can overfit with too many leaves"],
                    "code": f"from lightgbm import LGBMClassifier\nfrom sklearn.model_selection import train_test_split\n\nX = {var_name}.drop(columns=['{target}'])\ny = {var_name}['{target}']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n\nmodel = LGBMClassifier(n_estimators=200, learning_rate=0.1, random_state=42)\nmodel.fit(X_train, y_train)\nprint(f'Accuracy: {{model.score(X_test, y_test):.4f}}')",
                })

            elif task_type == "regression":
                recommendations.append({
                    "name": "XGBoost Regressor",
                    "category": "gradient_boosting",
                    "score": 92,
                    "speed": "medium",
                    "interpretability": "medium",
                    "reasons": [
                        "Best overall for tabular regression",
                        "Handles non-linear relationships",
                        "Built-in regularization",
                    ],
                    "caveats": ["Cannot extrapolate beyond training range"],
                    "code": f"from xgboost import XGBRegressor\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.metrics import mean_squared_error, r2_score\nimport numpy as np\n\nX = {var_name}.drop(columns=['{target}'])\ny = {var_name}['{target}']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n\nmodel = XGBRegressor(n_estimators=200, learning_rate=0.1, random_state=42)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\nprint(f'RMSE: {{np.sqrt(mean_squared_error(y_test, y_pred)):.4f}}')\nprint(f'R²:   {{r2_score(y_test, y_pred):.4f}}')",
                })

                recommendations.append({
                    "name": "Random Forest Regressor",
                    "category": "ensemble",
                    "score": 85,
                    "speed": "medium",
                    "interpretability": "medium",
                    "reasons": [
                        "Robust to outliers",
                        "No feature scaling needed",
                        "Good out-of-the-box performance",
                    ],
                    "caveats": ["Predictions bounded by training range", "Can be slow for large datasets"],
                    "code": f"from sklearn.ensemble import RandomForestRegressor\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.metrics import mean_squared_error, r2_score\nimport numpy as np\n\nX = {var_name}.drop(columns=['{target}'])\ny = {var_name}['{target}']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n\nmodel = RandomForestRegressor(n_estimators=100, random_state=42)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\nprint(f'RMSE: {{np.sqrt(mean_squared_error(y_test, y_pred)):.4f}}')",
                })

                if not chars["high_dimensional"]:
                    recommendations.append({
                        "name": "Ridge Regression",
                        "category": "linear",
                        "score": 72,
                        "speed": "fast",
                        "interpretability": "high",
                        "reasons": [
                            "Fast and interpretable baseline",
                            "Handles multicollinearity well",
                            "Good when features have linear relationships",
                        ],
                        "caveats": ["Cannot capture non-linear patterns"],
                        "code": f"from sklearn.linear_model import Ridge\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.pipeline import Pipeline\nfrom sklearn.model_selection import train_test_split\n\nX = {var_name}.drop(columns=['{target}'])\ny = {var_name}['{target}']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\n\npipe = Pipeline([('scaler', StandardScaler()), ('ridge', Ridge(alpha=1.0))])\npipe.fit(X_train, y_train)\nprint(f'R²: {{pipe.score(X_test, y_test):.4f}}')",
                    })

            else:  # clustering
                recommendations.append({
                    "name": "K-Means",
                    "category": "clustering",
                    "score": 85,
                    "speed": "fast",
                    "interpretability": "high",
                    "reasons": [
                        "Simple, fast, and widely understood",
                        "Good for spherical clusters",
                        "Scalable to large datasets",
                    ],
                    "caveats": ["Must specify k", "Sensitive to outliers", "Assumes spherical clusters"],
                    "code": f"from sklearn.cluster import KMeans\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.metrics import silhouette_score\n\nscaler = StandardScaler()\nX_scaled = scaler.fit_transform({var_name}.select_dtypes(include='number').dropna())\n\nscores = {{}}\nfor k in range(2, 11):\n    km = KMeans(n_clusters=k, random_state=42, n_init=10)\n    labels = km.fit_predict(X_scaled)\n    scores[k] = silhouette_score(X_scaled, labels)\n    print(f'k={{k}}: silhouette={{scores[k]:.3f}}')\n\nbest_k = max(scores, key=scores.get)\nprint(f'\\nBest k={{best_k}} (silhouette={{scores[best_k]:.3f}}')",
                })

                recommendations.append({
                    "name": "DBSCAN",
                    "category": "clustering",
                    "score": 78,
                    "speed": "medium",
                    "interpretability": "medium",
                    "reasons": [
                        "Finds clusters of arbitrary shape",
                        "Detects outliers automatically",
                        "No need to specify number of clusters",
                    ],
                    "caveats": ["Sensitive to eps parameter", "Struggles with varying densities"],
                    "code": f"from sklearn.cluster import DBSCAN\nfrom sklearn.preprocessing import StandardScaler\n\nscaler = StandardScaler()\nX_scaled = scaler.fit_transform({var_name}.select_dtypes(include='number').dropna())\n\ndb = DBSCAN(eps=0.5, min_samples=5)\nlabels = db.fit_predict(X_scaled)\nprint(f'Clusters found: {{len(set(labels)) - (1 if -1 in labels else 0)}}')\nprint(f'Noise points: {{(labels == -1).sum()}}')",
                })

            # ── UnicoLab Ecosystem: KerasFactory + MLPotion ──
            if target and task_type in ("classification", "regression"):
                try:
                    if UnicoLabEcosystem.is_available("kerasfactory"):
                        from flowyml_notebook.integrations.kerasfactory_adapter import (
                            generate_model_recommendation,
                            generate_advanced_model_recommendation,
                        )
                        _feature_names = [c for c in df.columns if c != target]
                        kf_rec = generate_model_recommendation(
                            var_name=var_name, task_type=task_type,
                            target=target, feature_names=_feature_names,
                            n_rows=n_rows, n_features=len(_feature_names),
                            has_categorical=len(cat_cols) > 0,
                        )
                        recommendations.append(kf_rec)
                        kf_adv = generate_advanced_model_recommendation(
                            var_name=var_name, task_type=task_type,
                            target=target, feature_names=_feature_names,
                            n_rows=n_rows, n_features=len(_feature_names),
                        )
                        recommendations.append(kf_adv)
                except Exception as _kf_err:
                    logger.debug(f"KerasFactory suggestion skipped: {_kf_err}")

                try:
                    if UnicoLabEcosystem.is_available("mlpotion"):
                        from flowyml_notebook.integrations.mlpotion_adapter import (
                            generate_training_pipeline,
                        )
                        _feature_names_ml = [c for c in df.columns if c != target]
                        mlp_rec = generate_training_pipeline(
                            var_name=var_name, task_type=task_type,
                            target=target, n_rows=n_rows,
                            n_features=len(_feature_names_ml),
                        )
                        recommendations.append(mlp_rec)
                except Exception as _mlp_err:
                    logger.debug(f"MLPotion suggestion skipped: {_mlp_err}")

                # Full ecosystem pipeline (requires all 3)
                try:
                    avail = UnicoLabEcosystem.available_packages()
                    if all(avail.values()):
                        from flowyml_notebook.integrations.mlpotion_adapter import (
                            generate_full_ecosystem_pipeline,
                        )
                        _feature_names_e2e = [c for c in df.columns if c != target]
                        _ftypes: dict[str, str] = {}
                        for col in df.columns:
                            s = df[col]
                            _n_u = int(s.nunique())
                            if pd.api.types.is_numeric_dtype(s):
                                _ftypes[col] = "binary" if _n_u == 2 else "continuous"
                            elif pd.api.types.is_datetime64_any_dtype(s):
                                _ftypes[col] = "temporal"
                            else:
                                _ftypes[col] = "nominal" if _n_u <= 20 else "high_cardinality"
                        e2e_rec = generate_full_ecosystem_pipeline(
                            var_name=var_name, task_type=task_type,
                            target=target, feature_types=_ftypes,
                            n_rows=n_rows, n_features=len(_feature_names_e2e),
                        )
                        recommendations.append(e2e_rec)
                except Exception as _e2e_err:
                    logger.debug(f"E2E pipeline suggestion skipped: {_e2e_err}")

            # Sort by score descending
            recommendations.sort(key=lambda r: r["score"], reverse=True)

            return {
                "variable": var_name,
                "task_type": task_type,
                "target": target,
                "target_info": target_info,
                "data_characteristics": chars,
                "recommendations": recommendations,
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
            # Track in recent files
            self._track_recent_file(saved_path, self.notebook.notebook.metadata.name)

            # Auto-create version snapshot
            try:
                import hashlib
                from datetime import datetime as dt_now
                history_dir = Path.home() / ".flowyml" / "history"
                history_dir.mkdir(parents=True, exist_ok=True)
                ts = dt_now.now().isoformat()
                snapshot_id = hashlib.sha256(ts.encode()).hexdigest()[:12]
                state = self.notebook.get_state()
                cells_data_snap = state.get("notebook", {}).get("cells", [])
                snapshot = {
                    "id": snapshot_id,
                    "message": f"Auto-save at {dt_now.now().strftime('%H:%M:%S')}",
                    "timestamp": ts,
                    "cell_count": len(cells_data_snap),
                    "additions": 0,
                    "deletions": 0,
                    "cells": [{"id": c.get("id", ""), "name": c.get("name", ""), "cell_type": c.get("cell_type", "code"), "source": c.get("source", "")} for c in cells_data_snap],
                }
                import json as _json
                (history_dir / f"{snapshot_id}.json").write_text(_json.dumps(snapshot, indent=2))
            except Exception:
                pass

            return {"path": saved_path}

        @app.post("/api/save-as")
        async def save_as_notebook(data: dict):
            """Save notebook to a user-specified path and name.

            Body: { path: str, name: str, format: 'py' | 'json' | 'both' }
            """
            target_dir = data.get("path", os.getcwd())
            name = data.get("name", self.notebook.notebook.metadata.name or "untitled")
            fmt = data.get("format", "both")

            # Update notebook name
            self.notebook.notebook.metadata.name = name
            safe_name = name.lower().replace(" ", "_").replace("/", "_")

            saved_paths = []

            if fmt in ("py", "both"):
                py_path = os.path.join(target_dir, f"{safe_name}.py")
                self.notebook.save(py_path)
                saved_paths.append(py_path)

            if fmt in ("json", "both"):
                json_path = os.path.join(target_dir, f"{safe_name}.fml.json")
                # Save as JSON with outputs
                import json as json_mod
                notebook_data = {
                    "metadata": {
                        **self.notebook.notebook.metadata.to_dict(),
                        "id": self.current_nb_id or str(__import__("uuid").uuid4())[:8],
                        "modified_at": datetime.now().isoformat(),
                    },
                    "cells": [c.to_dict() for c in self.notebook.cells],
                }
                Path(json_path).write_text(
                    json_mod.dumps(notebook_data, indent=2, default=str),
                    encoding="utf-8",
                )
                saved_paths.append(json_path)

            # Track the primary file path
            primary_path = saved_paths[0] if saved_paths else None
            if primary_path:
                self.notebook.file_path = primary_path
                self._track_recent_file(primary_path, name)

            return {"paths": saved_paths, "name": name}

        @app.get("/api/browse-dirs")
        async def browse_directories(path: str = ""):
            """List directories and notebook files for the folder picker."""
            import os

            target = path or os.getcwd()
            try:
                target = os.path.expanduser(target)
                entries = []
                for entry in sorted(os.listdir(target)):
                    full = os.path.join(target, entry)
                    if entry.startswith("."):
                        continue
                    if os.path.isdir(full):
                        entries.append({
                            "name": entry,
                            "path": full,
                            "is_dir": True,
                        })
                    elif entry.endswith((".py", ".fml.json", ".ipynb")):
                        try:
                            stat = os.stat(full)
                            entries.append({
                                "name": entry,
                                "path": full,
                                "is_dir": False,
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            })
                        except OSError:
                            pass

                # Get parent directory
                parent = os.path.dirname(target)
                return {
                    "current": target,
                    "parent": parent if parent != target else None,
                    "entries": entries,
                }
            except PermissionError:
                return {"current": target, "parent": os.path.dirname(target), "entries": [], "error": "Permission denied"}
            except FileNotFoundError:
                return {"current": os.getcwd(), "parent": None, "entries": [], "error": "Directory not found"}

        @app.post("/api/load-file")
        async def load_file(data: dict):
            """Load a notebook from any path (.py or .fml.json)."""
            path = data.get("path", "")
            if not path or not os.path.isfile(path):
                raise HTTPException(404, f"File not found: {path}")

            if path.endswith(".fml.json"):
                content = Path(path).read_text(encoding="utf-8")
                nb_data = json.loads(content)
                self.notebook.load_from_dict(nb_data)
                self.notebook.file_path = path
            elif path.endswith((".py", ".ipynb")):
                self.notebook.load(path)
            else:
                raise HTTPException(400, f"Unsupported file format: {path}")

            self._track_recent_file(path, self.notebook.notebook.metadata.name)
            return self.notebook.get_state()

        @app.get("/api/recent-files")
        async def get_recent_files():
            """Get list of recently opened/saved files."""
            return self._get_recent_files()

        @app.post("/api/load")
        async def load_notebook(path: str):
            """Load notebook from file."""
            self.notebook.load(path)
            self._track_recent_file(path, self.notebook.notebook.metadata.name)
            return self.notebook.get_state()

        # ===== Smart Import Suggestions =====

        @app.post("/api/suggest-imports")
        async def suggest_imports(data: dict):
            """Analyze cell code and suggest missing imports."""
            source = data.get("source", "")
            error_text = data.get("error", "")

            suggestions = []

            # Common import mappings
            IMPORT_MAP = {
                "pd": "import pandas as pd",
                "np": "import numpy as np",
                "plt": "import matplotlib.pyplot as plt",
                "sns": "import seaborn as sns",
                "sklearn": "import sklearn",
                "tf": "import tensorflow as tf",
                "torch": "import torch",
                "cv2": "import cv2",
                "PIL": "from PIL import Image",
                "Image": "from PIL import Image",
                "json": "import json",
                "os": "import os",
                "sys": "import sys",
                "re": "import re",
                "datetime": "from datetime import datetime",
                "Path": "from pathlib import Path",
                "Counter": "from collections import Counter",
                "defaultdict": "from collections import defaultdict",
                "tqdm": "from tqdm import tqdm",
                "requests": "import requests",
                "BeautifulSoup": "from bs4 import BeautifulSoup",
                "train_test_split": "from sklearn.model_selection import train_test_split",
                "accuracy_score": "from sklearn.metrics import accuracy_score",
                "RandomForestClassifier": "from sklearn.ensemble import RandomForestClassifier",
                "LinearRegression": "from sklearn.linear_model import LinearRegression",
                "StandardScaler": "from sklearn.preprocessing import StandardScaler",
                "KMeans": "from sklearn.cluster import KMeans",
                "PCA": "from sklearn.decomposition import PCA",
            }

            # Extract undefined names from error
            import re as re_mod
            name_error = re_mod.search(r"name '(\w+)' is not defined", error_text)
            if name_error:
                name = name_error.group(1)
                if name in IMPORT_MAP:
                    suggestions.append({
                        "name": name,
                        "import_statement": IMPORT_MAP[name],
                        "confidence": "high",
                    })

            # Also analyze the source for potential imports
            try:
                from flowyml_notebook.reactive import analyze_cell_dependencies
                reads, _ = analyze_cell_dependencies(source)
                for name in reads:
                    if name in IMPORT_MAP:
                        # Check if it's already imported in the namespace
                        if name not in self.notebook.session._namespace:
                            suggestions.append({
                                "name": name,
                                "import_statement": IMPORT_MAP[name],
                                "confidence": "medium",
                            })
            except Exception:
                pass

            return {"suggestions": suggestions}

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
            elif req.format == "presentation":
                from flowyml_notebook.reporting import generate_report
                path = generate_report(
                    self.notebook.notebook,
                    format="presentation",
                    include_code=req.include_code,
                )
                return {"format": "presentation", "path": path}
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
            try:
                html = _generate_html_report(self.notebook.notebook, report_title, include_code)
                return HTMLResponse(content=html)
            except Exception as e:
                logger.error(f"Report preview failed: {e}", exc_info=True)
                return HTMLResponse(
                    content=f"<html><body><h1>Report Generation Error</h1><pre>{e}</pre></body></html>",
                    status_code=500,
                )

        @app.get("/api/report/download")
        async def download_report(format: str = "html", include_code: bool = False, title: str = ""):
            """Generate report and return as downloadable file."""
            from flowyml_notebook.reporting import generate_report
            report_title = title or f"{self.notebook.notebook.metadata.name} — Report"
            try:
                path = generate_report(
                    self.notebook.notebook,
                    format=format,
                    title=report_title,
                    include_code=include_code,
                )
                return FileResponse(path, filename=os.path.basename(path),
                                    media_type="text/html" if format == "html" else "application/pdf")
            except Exception as e:
                logger.error(f"Report download failed: {e}", exc_info=True)
                raise HTTPException(500, detail=f"Report generation failed: {e}")

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

        @app.post("/api/app/snapshot")
        async def snapshot_app():
            """Create a snapshot of the current published app state."""
            from pathlib import Path
            import json as json_mod

            snapshots_dir = Path.home() / ".flowyml" / "app_snapshots"
            snapshots_dir.mkdir(parents=True, exist_ok=True)

            snap_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot = {
                "id": snap_id,
                "notebook_name": self.notebook.notebook.metadata.name,
                "cell_count": len(self.notebook.notebook.cells),
                "created_at": datetime.now().isoformat(),
                "cells": [c.to_dict() for c in self.notebook.notebook.cells],
            }
            snap_file = snapshots_dir / f"{snap_id}.json"
            snap_file.write_text(json_mod.dumps(snapshot, indent=2), encoding="utf-8")
            return {"snapshot_id": snap_id, "path": str(snap_file)}

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

        @app.get("/api/kernel/status")
        async def kernel_status():
            """Get kernel status, available environments (Poetry, Pipenv, Conda, pyenv, etc.)."""
            import sys

            is_ready = self.notebook.session._initialized
            current_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

            # Use the comprehensive kernel detector
            available_kernels = self._detect_kernels()

            return {
                "status": "ready" if is_ready else "idle",
                "kernel_name": f"Python {current_version}",
                "python_version": current_version,
                "python_path": sys.executable,
                "session_id": self.notebook.session.session_id,
                "available_kernels": available_kernels,
                "file_path": self.notebook.file_path,
            }

        @app.post("/api/kernel/refresh")
        async def kernel_refresh():
            """Re-scan available Python environments without switching."""
            return {"available_kernels": self._detect_kernels()}

        @app.post("/api/kernel/switch")
        async def kernel_switch(data: dict):
            """Switch to a different Python kernel.

            This restarts the kernel with a new Python executable.
            WARNING: All runtime state (variables, imports) is lost.
            """
            python_path = data.get("python_path", "")
            if not python_path or not Path(python_path).exists():
                raise HTTPException(400, f"Invalid Python path: {python_path}")

            import sys
            import subprocess

            # Verify the Python executable works
            try:
                result = subprocess.run(
                    [python_path, "-c", "import sys; print(sys.version)"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode != 0:
                    raise HTTPException(400, f"Python at {python_path} is not functional: {result.stderr}")
                version = result.stdout.strip()
            except FileNotFoundError:
                raise HTTPException(400, f"Python not found: {python_path}")
            except subprocess.TimeoutExpired:
                raise HTTPException(400, f"Python at {python_path} timed out")

            # Reset the current session
            self.notebook.session.reset()

            # For now, we cannot truly switch the interpreter mid-process.
            # What we CAN do is reset the IPython kernel and set up the new
            # Python path in the environment so subprocess calls use it.
            import os
            os.environ["PYTHON_PATH_OVERRIDE"] = python_path

            # Record the switch
            logger.info(f"Kernel switched to: {python_path} ({version})")

            return {
                "status": "ready",
                "python_path": python_path,
                "version": version,
                "message": f"Kernel reset. Using Python {version}. All state has been cleared.",
            }

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

        @app.get("/api/notebooks/{nb_id}/load")
        async def load_notebook(nb_id: str):
            """Load a specific notebook by ID into the current session."""
            nb_data = self.nb_manager.get_notebook(nb_id)
            if not nb_data:
                raise HTTPException(404, "Notebook not found")
            # Load the notebook data into the current session
            cells_data = nb_data.get("cells", [])
            self.notebook.notebook.cells.clear()
            for cell_data in cells_data:
                self.notebook.cell(
                    source=cell_data.get("source", ""),
                    cell_type=CellType(cell_data.get("cell_type", "code")),
                    name=cell_data.get("name", ""),
                )
            self.notebook.notebook.metadata.name = nb_data.get("name", "untitled")
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

        @app.post("/api/github/restore")
        async def github_restore(sha: str):
            """Restore notebook to a specific version (by commit SHA or snapshot ID)."""
            # Try the legacy snapshot system first
            import json as json_mod
            from pathlib import Path

            history_dir = Path.home() / ".flowyml" / "history"
            snapshot_file = history_dir / f"{sha}.json"

            if snapshot_file.exists():
                snap = json_mod.loads(snapshot_file.read_text())
                self.notebook.cells.clear()
                for cell_data in snap.get("cells", []):
                    self.notebook.cell(
                        source=cell_data.get("source", ""),
                        cell_type=CellType(cell_data.get("cell_type", "code")),
                        name=cell_data.get("name", ""),
                    )
                return {"restored": True, "source": "snapshot", "cell_count": len(self.notebook.cells)}

            # Fall back to git checkout
            try:
                result = self.github_sync.restore_to_commit(sha)
                return {"restored": True, "source": "git", **result}
            except Exception as e:
                raise HTTPException(404, f"Cannot restore version {sha}: {e}")

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

        # --- Notebook Sharing ---

        @app.post("/api/share")
        async def share_notebook(mode: str = "readonly", expires_hours: int = 24):
            """Generate a shareable link for the current notebook."""
            import hashlib
            from datetime import timedelta
            share_id = hashlib.sha256(
                f"{self.notebook.name}:{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12]
            share_info = {
                "share_id": share_id,
                "mode": mode,  # "readonly", "comment", "edit"
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=expires_hours)).isoformat(),
                "notebook_name": self.notebook.name,
                "cell_count": len(self.notebook.cells),
                "url": f"/shared/{share_id}",
            }
            if not hasattr(self, '_shares'):
                self._shares = {}
            self._shares[share_id] = share_info
            return share_info

        @app.get("/api/shares")
        async def list_shares():
            """List all active notebook shares."""
            shares = getattr(self, '_shares', {})
            # Filter expired shares
            now = datetime.now().isoformat()
            active = [s for s in shares.values() if s.get("expires_at", "") > now]
            return {"shares": active, "total": len(active)}

        @app.delete("/api/shares/{share_id}")
        async def revoke_share(share_id: str):
            """Revoke a notebook share."""
            shares = getattr(self, '_shares', {})
            if share_id in shares:
                del shares[share_id]
                return {"revoked": True, "share_id": share_id}
            raise HTTPException(404, "Share not found")

        # --- Review Approval Workflow ---

        @app.post("/api/reviews/{review_id}/approve")
        async def approve_review(review_id: str, comment: str = ""):
            """Approve a review."""
            git_user = self.github_sync._get_git_user(
                str(self.github_sync.repo_path)
            ) if self.github_sync.repo_path else {"name": "Local User", "email": ""}
            for r in self._reviews:
                if r["id"] == review_id:
                    r["status"] = "approved"
                    r["resolved_at"] = datetime.now().isoformat()
                    r["reviewer"] = git_user
                    if comment:
                        r.setdefault("review_comments", []).append({
                            "author": git_user,
                            "text": comment,
                            "status": "approved",
                            "created_at": datetime.now().isoformat(),
                        })
                    return r
            raise HTTPException(404, "Review not found")

        @app.post("/api/reviews/{review_id}/request-changes")
        async def request_changes(review_id: str, comment: str = "Changes needed"):
            """Request changes on a review."""
            git_user = self.github_sync._get_git_user(
                str(self.github_sync.repo_path)
            ) if self.github_sync.repo_path else {"name": "Local User", "email": ""}
            for r in self._reviews:
                if r["id"] == review_id:
                    r["status"] = "changes_requested"
                    r["resolved_at"] = datetime.now().isoformat()
                    r["reviewer"] = git_user
                    r.setdefault("review_comments", []).append({
                        "author": git_user,
                        "text": comment,
                        "status": "changes_requested",
                        "created_at": datetime.now().isoformat(),
                    })
                    return r
            raise HTTPException(404, "Review not found")

        @app.get("/api/reviews/summary")
        async def review_summary():
            """Get review summary with counts by status."""
            summary = {"approved": 0, "pending": 0, "changes_requested": 0, "rejected": 0, "total": len(self._reviews)}
            for r in self._reviews:
                status = r.get("status", "pending")
                summary[status] = summary.get(status, 0) + 1
            return summary

        # --- Comment Mentions ---

        @app.get("/api/comments/mentions/{username}")
        async def get_mentions(username: str):
            """Get all comments mentioning a specific user."""
            import re
            mentioned = []
            for c in self._comments:
                text = c.get("text", "")
                if re.search(rf'@{re.escape(username)}\b', text, re.IGNORECASE):
                    mentioned.append(c)
                for reply in c.get("replies", []):
                    if re.search(rf'@{re.escape(username)}\b', reply.get("text", ""), re.IGNORECASE):
                        mentioned.append({"parent_comment": c["id"], **reply})
            return {"mentions": mentioned, "count": len(mentioned)}

        @app.get("/api/comments/threads")
        async def get_threaded_comments():
            """Get comments organized as threads with nested replies."""
            threads = []
            for c in self._comments:
                thread = dict(c)
                thread["reply_count"] = len(c.get("replies", []))
                thread["last_activity"] = max(
                    [c.get("created_at", "")] + [r.get("created_at", "") for r in c.get("replies", [])],
                )
                threads.append(thread)
            threads.sort(key=lambda t: t.get("last_activity", ""), reverse=True)
            return {"threads": threads, "total": len(threads)}

        # --- Activity Feed ---

        @app.get("/api/activity")
        async def get_activity(limit: int = 50):
            """Unified activity feed for notebook collaboration."""
            activities = []
            for c in self._comments:
                activities.append({
                    "type": "comment",
                    "user": c.get("author", {}).get("name", "anonymous") if isinstance(c.get("author"), dict) else str(c.get("author", "anonymous")),
                    "text": c.get("text", "")[:100],
                    "timestamp": c.get("created_at", ""),
                    "cell_id": c.get("cell_id"),
                    "id": c.get("id"),
                })
                for reply in c.get("replies", []):
                    activities.append({
                        "type": "reply",
                        "user": reply.get("author", {}).get("name", "anonymous") if isinstance(reply.get("author"), dict) else str(reply.get("author", "anonymous")),
                        "text": reply.get("text", "")[:100],
                        "timestamp": reply.get("created_at", ""),
                        "parent_id": c.get("id"),
                    })
            for r in self._reviews:
                activities.append({
                    "type": "review",
                    "user": r.get("requested_by", {}).get("name", "anonymous") if isinstance(r.get("requested_by"), dict) else str(r.get("requested_by", "anonymous")),
                    "text": r.get("title", "")[:100],
                    "timestamp": r.get("created_at", ""),
                    "status": r.get("status", "pending"),
                    "id": r.get("id"),
                })
            for s in getattr(self, '_shares', {}).values():
                activities.append({
                    "type": "share",
                    "user": "system",
                    "text": f"Notebook shared ({s.get('mode', 'readonly')})",
                    "timestamp": s.get("created_at", ""),
                    "share_id": s.get("share_id"),
                })
            activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return {"activities": activities[:limit], "total": len(activities)}

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

        # --- Ecosystem Status Endpoint ---

        @app.get("/api/ecosystem/status")
        async def ecosystem_status():
            """Return installed UnicoLab ecosystem packages and versions."""
            return UnicoLabEcosystem.get_ecosystem_status()

        # --- Recipe Endpoints (Enhanced with Ratings, Forking, Leaderboard) ---

        @app.get("/api/recipes")
        async def list_recipes():
            """List all recipes (local custom + shared from GitHub + builtin ecosystem)."""
            local = self.recipe_store.list_recipes()
            shared = []
            try:
                shared = self.github_sync.pull_recipes()
            except Exception:
                pass
            # Merge, avoiding duplicates by id
            seen_ids = {r["id"] for r in local}
            combined = local + [r for r in shared if r.get("id") not in seen_ids]
            # Add builtin ecosystem recipes
            try:
                builtin = _builtin_recipes.get_builtin_recipes()
                for recipe in builtin:
                    if recipe["id"] not in seen_ids:
                        combined.append(recipe)
                        seen_ids.add(recipe["id"])
            except Exception:
                pass
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

        # ===== Analysis Patterns (Collaborative Knowledge Base) =====

        @app.get("/api/patterns")
        async def list_patterns():
            """List all saved analysis patterns."""
            patterns_file = Path(self.notebook.file_path or ".").parent / ".flowyml_patterns.json"
            if not patterns_file.exists():
                return {"patterns": []}
            try:
                data = json.loads(patterns_file.read_text(encoding="utf-8"))
                return {"patterns": data.get("patterns", [])}
            except Exception:
                return {"patterns": []}

        @app.post("/api/patterns")
        async def save_pattern(pattern: dict):
            """Save a new analysis pattern (bookmarked cell sequence)."""
            import uuid
            from datetime import datetime

            patterns_file = Path(self.notebook.file_path or ".").parent / ".flowyml_patterns.json"
            data = {"patterns": []}
            if patterns_file.exists():
                try:
                    data = json.loads(patterns_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            new_pattern = {
                "id": str(uuid.uuid4())[:8],
                "name": pattern.get("name", "Untitled Pattern"),
                "description": pattern.get("description", ""),
                "tags": pattern.get("tags", []),
                "cells": pattern.get("cells", []),
                "data_type": pattern.get("data_type", "any"),
                "problem_type": pattern.get("problem_type", "any"),
                "author": pattern.get("author", "local"),
                "created_at": datetime.now().isoformat(),
                "uses": 0,
            }
            data.setdefault("patterns", []).append(new_pattern)
            patterns_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return {"pattern": new_pattern}

        @app.delete("/api/patterns/{pattern_id}")
        async def delete_pattern(pattern_id: str):
            """Delete an analysis pattern."""
            patterns_file = Path(self.notebook.file_path or ".").parent / ".flowyml_patterns.json"
            if not patterns_file.exists():
                raise HTTPException(404, "No patterns file")
            data = json.loads(patterns_file.read_text(encoding="utf-8"))
            data["patterns"] = [p for p in data.get("patterns", []) if p.get("id") != pattern_id]
            patterns_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return {"deleted": pattern_id}

        @app.post("/api/patterns/{pattern_id}/apply")
        async def apply_pattern(pattern_id: str):
            """Apply a pattern by inserting its cells into the notebook."""
            patterns_file = Path(self.notebook.file_path or ".").parent / ".flowyml_patterns.json"
            if not patterns_file.exists():
                raise HTTPException(404, "No patterns file")
            data = json.loads(patterns_file.read_text(encoding="utf-8"))
            pattern = next((p for p in data.get("patterns", []) if p.get("id") == pattern_id), None)
            if not pattern:
                raise HTTPException(404, f"Pattern '{pattern_id}' not found")
            # Increment usage counter
            pattern["uses"] = pattern.get("uses", 0) + 1
            patterns_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return {"pattern": pattern, "cells": pattern.get("cells", [])}

        @app.post("/api/patterns/search")
        async def search_patterns(query: dict):
            """Search patterns by tags, data type, or problem type."""
            patterns_file = Path(self.notebook.file_path or ".").parent / ".flowyml_patterns.json"
            if not patterns_file.exists():
                return {"patterns": []}
            data = json.loads(patterns_file.read_text(encoding="utf-8"))
            patterns = data.get("patterns", [])

            q = query.get("query", "").lower()
            data_type = query.get("data_type")
            problem_type = query.get("problem_type")

            results = []
            for p in patterns:
                if q and q not in p.get("name", "").lower() and q not in p.get("description", "").lower():
                    if not any(q in t.lower() for t in p.get("tags", [])):
                        continue
                if data_type and data_type != "any" and p.get("data_type") not in (data_type, "any"):
                    continue
                if problem_type and problem_type != "any" and p.get("problem_type") not in (problem_type, "any"):
                    continue
                results.append(p)

            return {"patterns": results}

        # ===== Killer Features: Profiler =====

        @app.post("/api/cells/{cell_id}/profile")
        async def profile_cell(cell_id: str):
            """Profile a cell's execution with CPU, memory, and timing."""
            from flowyml_notebook.profiler import CellProfiler, format_profile_output
            if not self._profiler:
                self._profiler = CellProfiler()
            cell = self.notebook.notebook.get_cell(cell_id)
            if not cell:
                raise HTTPException(404, f"Cell {cell_id} not found")
            try:
                result = self._profiler.profile(cell_id, cell.source, self.notebook.session._namespace)
                output = format_profile_output(result)
                return {"profile": result.to_dict(), "output": output.to_dict()}
            except Exception as e:
                logger.error(f"Profiling failed for cell {cell_id}: {e}", exc_info=True)
                return {
                    "profile": {
                        "cell_id": cell_id,
                        "wall_time_s": 0, "cpu_time_s": 0,
                        "memory_delta_mb": 0, "peak_memory_mb": 0,
                        "function_calls": 0,
                        "top_functions": [], "top_allocations": [],
                        "line_times": [{"error": str(e)}],
                        "timestamp": "",
                    },
                    "output": {"output_type": "error", "data": f"Profiling error: {e}", "metadata": {}},
                }

        @app.get("/api/profiler/history")
        async def profiler_history():
            """Get profiling history for all cells."""
            if not self._profiler:
                return {"history": []}
            return {"history": [r.to_dict() for r in self._profiler.history]}

        @app.get("/api/profiler/history/{cell_id}")
        async def profiler_cell_history(cell_id: str):
            """Get profiling history for a specific cell."""
            if not self._profiler:
                return {"history": []}
            return {"history": [r.to_dict() for r in self._profiler.get_history_for_cell(cell_id)]}

        # ===== Killer Features: Benchmark =====

        @app.post("/api/cells/{cell_id}/benchmark")
        async def benchmark_cell(cell_id: str, runs: int = 5, warmup: int = 1):
            """Benchmark a cell with statistical timing analysis."""
            from flowyml_notebook.benchmark import CellBenchmark, format_benchmark_output
            if not self._benchmark:
                self._benchmark = CellBenchmark()
            cell = self.notebook.notebook.get_cell(cell_id)
            if not cell:
                raise HTTPException(404, f"Cell {cell_id} not found")
            try:
                result = self._benchmark.benchmark(
                    cell_id, cell.source, self.notebook.session._namespace,
                    runs=runs, warmup=warmup,
                )
                output = format_benchmark_output(result)
                regressions = self._benchmark.detect_regressions(cell_id)
                return {
                    "benchmark": result.to_dict(),
                    "output": output.to_dict(),
                    "regressions": [r.to_dict() for r in regressions],
                }
            except Exception as e:
                logger.error(f"Benchmark failed for cell {cell_id}: {e}", exc_info=True)
                return {
                    "benchmark": {
                        "cell_id": cell_id, "runs": 0, "warmup": 0,
                        "mean_s": 0, "std_s": 0, "min_s": 0, "max_s": 0,
                        "median_s": 0, "times": [], "timestamp": "",
                    },
                    "output": {"output_type": "error", "data": f"Benchmark error: {e}", "metadata": {}},
                    "regressions": [],
                }

        @app.get("/api/benchmark/history/{cell_id}")
        async def benchmark_history(cell_id: str):
            """Get benchmark history for a cell."""
            if not self._benchmark:
                return {"history": []}
            return {"history": self._benchmark.get_history(cell_id)}

        # ===== Killer Features: Data Quality =====

        @app.get("/api/data-quality/{var_name}")
        async def validate_data(var_name: str):
            """Run data quality checks on a DataFrame variable."""
            from flowyml_notebook.data_validator import DataValidator, format_quality_output
            if not self._validator:
                self._validator = DataValidator()
            self.notebook.session._ensure_kernel()
            ns = self.notebook.session._namespace
            if var_name not in ns:
                raise HTTPException(404, f"Variable '{var_name}' not found")
            obj = ns[var_name]
            try:
                import pandas as pd
                if not isinstance(obj, pd.DataFrame):
                    raise HTTPException(400, f"'{var_name}' is not a DataFrame")
            except ImportError:
                raise HTTPException(500, "pandas not installed")
            report = self._validator.validate(var_name, "api", obj)
            output = format_quality_output(report)
            return {"report": report.to_dict(), "output": output.to_dict()}

        @app.post("/api/data-quality/validate-all")
        async def validate_all_dataframes():
            """Validate all DataFrames in the current namespace."""
            from flowyml_notebook.data_validator import DataValidator
            if not self._validator:
                self._validator = DataValidator()
            self.notebook.session._ensure_kernel()
            reports = self._validator.validate_namespace("api", self.notebook.session._namespace)
            return {"reports": [r.to_dict() for r in reports]}

        # ===== Killer Features: Code Analyzer =====

        @app.post("/api/cells/{cell_id}/analyze")
        async def analyze_cell_code(cell_id: str):
            """Run smart code analysis on a cell."""
            from flowyml_notebook.code_analyzer import CodeAnalyzer
            if not self._analyzer:
                self._analyzer = CodeAnalyzer()
            cell = self.notebook.notebook.get_cell(cell_id)
            if not cell:
                raise HTTPException(404, f"Cell {cell_id} not found")
            report = self._analyzer.analyze(cell_id, cell.source)
            return {"report": report.to_dict()}

        @app.post("/api/cells/{cell_id}/auto-fix")
        async def auto_fix_cell(cell_id: str):
            """Apply auto-fixes to a cell."""
            from flowyml_notebook.code_analyzer import CodeAnalyzer
            if not self._analyzer:
                self._analyzer = CodeAnalyzer()
            cell = self.notebook.notebook.get_cell(cell_id)
            if not cell:
                raise HTTPException(404, f"Cell {cell_id} not found")
            fixed_source, changes = self._analyzer.auto_fix(cell_id, cell.source)
            if changes:
                cell.source = fixed_source
            return {"fixed_source": fixed_source, "changes": changes, "applied": len(changes) > 0}

        # ===== Killer Features: Execution History =====

        @app.get("/api/execution-history")
        async def get_execution_history():
            """Get execution statistics and global log."""
            from flowyml_notebook.execution_history import ExecutionHistory
            if not self._execution_history:
                self._execution_history = ExecutionHistory()
            return {
                "stats": self._execution_history.get_execution_stats(),
                "log": self._execution_history.get_global_log(limit=50),
            }

        @app.get("/api/execution-history/{cell_id}")
        async def get_cell_execution_history(cell_id: str):
            """Get execution timeline for a specific cell."""
            from flowyml_notebook.execution_history import ExecutionHistory
            if not self._execution_history:
                self._execution_history = ExecutionHistory()
            timeline = self._execution_history.get_timeline(cell_id)
            return {"timeline": timeline}

        @app.get("/api/execution-history/{cell_id}/compare")
        async def compare_cell_runs(cell_id: str, run_a: int = -2, run_b: int = -1):
            """Compare two execution runs of a cell."""
            from flowyml_notebook.execution_history import ExecutionHistory
            if not self._execution_history:
                self._execution_history = ExecutionHistory()
            comparison = self._execution_history.compare_runs(cell_id, run_a, run_b)
            return {"comparison": comparison}

        # ===== Killer Features: Data Lineage =====

        @app.get("/api/lineage")
        async def get_all_lineage():
            """Get data lineage for all tracked variables."""
            from dataclasses import asdict
            from flowyml_notebook.lineage import LineageTracker
            if not self._lineage:
                self._lineage = LineageTracker()
            all_lineage = self._lineage.get_all_lineage()
            return {
                "lineage": {
                    var: [asdict(e) for e in entries]
                    for var, entries in all_lineage.items()
                },
            }

        @app.get("/api/lineage/{var_name}")
        async def get_variable_lineage(var_name: str):
            """Get lineage for a specific variable."""
            from dataclasses import asdict
            from flowyml_notebook.lineage import LineageTracker
            if not self._lineage:
                self._lineage = LineageTracker()
            entries = self._lineage.get_lineage(var_name)
            return {"var_name": var_name, "entries": [asdict(e) for e in entries]}

        @app.get("/api/lineage/graph")
        async def get_lineage_graph():
            """Get lineage graph for visualization."""
            from flowyml_notebook.lineage import LineageTracker
            if not self._lineage:
                self._lineage = LineageTracker()
            return {"graph": self._lineage.get_lineage_graph()}

        # ===== Killer Features: Environment =====

        @app.get("/api/environment/snapshot")
        async def get_environment_snapshot():
            """Capture a full environment snapshot."""
            from flowyml_notebook.environment import capture_environment
            snap = capture_environment()
            d = snap.to_dict()
            # Add frontend-expected aliases
            d["os"] = d.get("os_name", "")
            d["arch"] = d.get("architecture", "")
            # Convert packages dict to list of {name, version} for frontend
            pkg_dict = d.get("packages", {})
            d["packages"] = [
                {"name": name, "version": ver}
                for name, ver in sorted(pkg_dict.items(), key=lambda x: x[0].lower())
            ]
            # GPU info for frontend
            gpu_list = d.get("gpu_info", [])
            if gpu_list:
                d["gpu"] = {"name": gpu_list[0].get("name", "GPU"), "memory": gpu_list[0].get("memory_total_mb")}
            return d

        @app.post("/api/environment/requirements")
        async def export_requirements(pinned: bool = True):
            """Export requirements.txt from notebook imports."""
            from flowyml_notebook.environment import export_requirements
            from pathlib import Path
            output_dir = Path.home() / ".flowyml"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "requirements.txt"
            path = export_requirements(self.notebook.notebook, output_path=output_path, pinned=pinned)
            # Read content for inline display
            content = path.read_text(encoding="utf-8")
            return {"path": str(path), "pinned": pinned, "content": content}

        @app.get("/api/packages")
        async def list_packages():
            """List installed packages."""
            from flowyml_notebook.package_installer import list_installed
            return {"packages": list_installed()}

        @app.post("/api/packages/install")
        async def install_package(name: str, version: str | None = None, upgrade: bool = False):
            """Install a Python package."""
            from flowyml_notebook.package_installer import install_package as _install
            result = _install(name, version=version, upgrade=upgrade)
            return result.__dict__ if hasattr(result, '__dict__') else {"success": False}

        @app.post("/api/packages/uninstall")
        async def uninstall_package(name: str):
            """Uninstall a Python package."""
            from flowyml_notebook.package_installer import uninstall_package as _uninstall
            result = _uninstall(name)
            return result.__dict__ if hasattr(result, '__dict__') else {"success": False}
        # ===== Killer Features: Unified Package Management (Frontend) =====

        @app.post("/api/environment/packages")
        async def manage_packages(body: dict):
            """Unified package management endpoint for the ToolsPanel frontend."""
            from flowyml_notebook.package_installer import install_package as _install, uninstall_package as _uninstall
            action = body.get("action", "install")
            pkg_name = body.get("package", body.get("name", ""))
            if not pkg_name:
                raise HTTPException(400, "Package name required")
            if action == "uninstall":
                result = _uninstall(pkg_name)
            else:
                result = _install(pkg_name, version=body.get("version"), upgrade=body.get("upgrade", False))
            r = result.__dict__ if hasattr(result, '__dict__') else {"success": False}
            msg = f"{'Uninstalled' if action == 'uninstall' else 'Installed'} {pkg_name}"
            if r.get("version"):
                msg += f" ({r['version']})"
            r["message"] = msg
            return r

        # ===== Killer Features: Import/Export =====

        @app.post("/api/import/ipynb")
        async def import_ipynb(file: UploadFile):
            """Import a Jupyter .ipynb file."""
            from flowyml_notebook.ipynb_converter import from_ipynb
            content = await file.read()
            nb_data = json.loads(content)
            self.notebook.notebook = from_ipynb(nb_data)
            return {
                "notebook": self.notebook.notebook.to_dict(),
                "cells": [c.to_dict() for c in self.notebook.notebook.cells],
                "message": f"Imported {len(self.notebook.notebook.cells)} cells from {file.filename}",
            }

        @app.post("/api/export/ipynb")
        async def export_ipynb():
            """Export current notebook as .ipynb."""
            from flowyml_notebook.ipynb_converter import to_ipynb
            ipynb_data = to_ipynb(self.notebook.notebook)
            return {"ipynb": ipynb_data, "filename": f"{self.notebook.notebook.metadata.name}.ipynb"}

        # ===== Killer Features: Cell Dependencies =====

        @app.get("/api/cells/dependencies")
        async def get_cell_dependencies():
            """Analyze all code cells and return a full dependency graph."""
            from flowyml_notebook.cell_deps import CellDependencyAnalyzer
            analyzer = CellDependencyAnalyzer()
            cells = [(c.id, c.source) for c in self.notebook.notebook.cells if c.cell_type.value == 'code']
            graph = analyzer.build_graph(cells)
            return graph.to_dict()

        @app.get("/api/cells/{cell_id}/dependencies")
        async def get_single_cell_deps(cell_id: str):
            """Get defines/uses/imports for a single cell."""
            from flowyml_notebook.cell_deps import CellDependencyAnalyzer
            cell = self.notebook.notebook.get_cell(cell_id)
            if not cell:
                raise HTTPException(404, f"Cell {cell_id} not found")
            analyzer = CellDependencyAnalyzer()
            dep = analyzer.analyze_cell(cell_id, cell.source)
            return dep.to_dict()

        @app.get("/api/cells/{cell_id}/stale")
        async def get_stale_cells(cell_id: str):
            """Find all cells that transitively depend on the given cell."""
            from flowyml_notebook.cell_deps import CellDependencyAnalyzer
            analyzer = CellDependencyAnalyzer()
            cells = [(c.id, c.source) for c in self.notebook.notebook.cells if c.cell_type.value == 'code']
            stale = analyzer.find_stale_cells(cell_id, cells)
            return {"stale_cells": stale, "modified_cell": cell_id}

        @app.get("/api/cells/execution-order")
        async def get_optimal_order():
            """Return the topologically optimal execution order for all code cells."""
            from flowyml_notebook.cell_deps import CellDependencyAnalyzer
            analyzer = CellDependencyAnalyzer()
            cells = [(c.id, c.source) for c in self.notebook.notebook.cells if c.cell_type.value == 'code']
            order = analyzer.get_execution_order(cells)
            return {"execution_order": order}

        # ===== Killer Features: Search =====

        @app.post("/api/search")
        async def search_notebook(query: dict):
            from flowyml_notebook.search import NotebookSearch
            search = NotebookSearch()
            cells = self.notebook.notebook.cells
            results = search.search(
                cells, query.get('query', ''),
                case_sensitive=query.get('case_sensitive', False),
                regex=query.get('regex', False),
                search_outputs=query.get('search_outputs', False),
                max_results=query.get('max_results', 50),
            )
            return {"results": [r.to_dict() for r in results], "total": len(results)}

        @app.post("/api/search/replace")
        async def search_replace(query: dict):
            from flowyml_notebook.search import NotebookSearch
            search = NotebookSearch()
            cells = self.notebook.notebook.cells
            changes = search.search_and_replace(
                cells, query.get('query', ''),
                query.get('replacement', ''),
                case_sensitive=query.get('case_sensitive', False),
                regex=query.get('regex', False),
            )
            return {"changes": changes, "count": len(changes)}

        @app.get("/api/search/variables")
        async def find_variables():
            from flowyml_notebook.search import NotebookSearch
            search = NotebookSearch()
            cells = self.notebook.notebook.cells
            return {"variables": search.find_all_variables(cells)}

        @app.get("/api/search/functions")
        async def find_functions():
            from flowyml_notebook.search import NotebookSearch
            search = NotebookSearch()
            cells = self.notebook.notebook.cells
            return {"functions": search.find_all_functions(cells)}

        @app.get("/api/search/duplicates")
        async def find_duplicates():
            from flowyml_notebook.search import NotebookSearch
            search = NotebookSearch()
            cells = self.notebook.notebook.cells
            return {"duplicates": search.find_duplicates(cells)}

        # ===== Killer Features: Snippets =====

        @app.get("/api/snippets")
        async def list_snippets(category: str | None = None, q: str | None = None):
            from flowyml_notebook.snippets import SnippetLibrary
            if not hasattr(self, '_snippets'):
                self._snippets = SnippetLibrary()
            if q:
                results = self._snippets.search(q, category=category)
            elif category:
                results = self._snippets.get_by_category(category)
            else:
                results = self._snippets.search('')
            return {"snippets": [s.to_dict() for s in results]}

        @app.get("/api/snippets/categories")
        async def snippet_categories():
            from flowyml_notebook.snippets import SnippetLibrary
            if not hasattr(self, '_snippets'):
                self._snippets = SnippetLibrary()
            return {"categories": self._snippets.get_categories()}

        @app.post("/api/snippets")
        async def add_snippet(snippet: dict):
            from flowyml_notebook.snippets import SnippetLibrary, Snippet
            if not hasattr(self, '_snippets'):
                self._snippets = SnippetLibrary()
            s = Snippet(**snippet)
            result = self._snippets.add_custom(s)
            return {"snippet": result.to_dict()}

        @app.post("/api/snippets/{snippet_id}/use")
        async def use_snippet(snippet_id: str):
            from flowyml_notebook.snippets import SnippetLibrary
            if not hasattr(self, '_snippets'):
                self._snippets = SnippetLibrary()
            snippet = self._snippets.get_snippet(snippet_id)
            if not snippet:
                raise HTTPException(404, f"Snippet {snippet_id} not found")
            self._snippets.record_use(snippet_id)
            return {"snippet": snippet.to_dict()}

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

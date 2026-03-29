"""Core notebook engine with reactive cell execution.

Provides the main Notebook class that manages cell execution
with a reactive dependency graph, auto-imported FlowyML SDK,
and session tracking.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from flowyml_notebook.cells import Cell, CellOutput, CellType, NotebookFile, NotebookMetadata
from flowyml_notebook.cells import parse_notebook, serialize_notebook
from flowyml_notebook.reactive import CellState, ReactiveGraph

logger = logging.getLogger(__name__)

# FlowyML imports that are auto-injected into notebook namespace
_FLOWYML_AUTO_IMPORTS = """
import flowyml
from flowyml import (
    # Core
    Pipeline, step, context, Context,
    # Assets
    Dataset, Model, Metrics, Artifact, FeatureSet, Report, Prompt, Checkpoint,
    AssetRegistry,
    # Tracking
    Experiment, Run,
    # Registry
    ModelRegistry, ModelVersion, ModelStage,
    # Catalog
    ArtifactCatalog,
    # Scheduling
    PipelineScheduler,
    # Evaluations
    evaluate, EvalDataset, EvalSuite, EvalResult,
    EvalRun, EvalSchedule,
    make_scorer, make_judge, get_scorer, TraceBridge,
    # Monitoring
    detect_drift, compute_stats,
    configure_notifications,
    # Parallel & Dynamic
    parallel_map, map_task, dynamic,
    sub_pipeline,
    # Workflow Control
    approval, ApprovalStep,
    # Versioning & Projects
    VersionedPipeline, freeze_pipeline,
    Project, ProjectManager,
    # Advanced Caching
    SmartCache, memoize,
    # Debugging
    debug_step, trace_step, profile_step,
    # GenAI Observability
    trace_genai, observe_genai, span,
)
import pandas as pd
import numpy as np

# UnicoLab Ecosystem (optional — installed via pip install 'flowyml-notebook[keras]')
try:
    from kdp import PreprocessingModel, FeatureType
except ImportError:
    pass
try:
    import kerasfactory
    from kerasfactory.layers import (
        DistributionTransformLayer, GatedFeatureFusion,
        TabularAttention, GatedResidualNetwork,
    )
    from kerasfactory.models import BaseFeedForwardModel
except ImportError:
    pass
try:
    import mlpotion
    from mlpotion.frameworks.keras.training import ModelTrainer
    from mlpotion.frameworks.keras.config import ModelTrainingConfig
except ImportError:
    pass
"""



@dataclass
class ExecutionResult:
    """Result of executing a single cell."""

    cell_id: str
    success: bool
    outputs: list[CellOutput] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0
    memory_delta_mb: float = 0.0
    cpu_time_s: float = 0.0
    peak_memory_mb: float = 0.0
    variables_defined: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "success": self.success,
            "outputs": [o.to_dict() for o in self.outputs],
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "memory_delta_mb": self.memory_delta_mb,
            "cpu_time_s": self.cpu_time_s,
            "peak_memory_mb": self.peak_memory_mb,
            "variables_defined": self.variables_defined,
        }


class NotebookSession:
    """An active notebook execution session.

    Manages an IPython kernel with shared namespace,
    reactive dependency tracking, and output capture.
    """

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())
        self._namespace: dict[str, Any] = {}
        self._ip = None  # IPython InteractiveShell (lazy init)
        self._initialized = False

    def _ensure_kernel(self) -> None:
        """Lazily initialize the IPython kernel."""
        if self._initialized:
            return

        try:
            from IPython.core.interactiveshell import InteractiveShell

            self._ip = InteractiveShell.instance()
            # Inject auto-imports
            self._ip.run_cell(_FLOWYML_AUTO_IMPORTS, silent=True)
            self._namespace = self._ip.user_ns
            self._initialized = True
            logger.info(f"Notebook kernel initialized (session: {self.session_id})")
        except ImportError:
            # Fallback: plain exec with shared namespace
            logger.warning("IPython not available, using plain exec fallback")
            self._namespace = {"__builtins__": __builtins__}
            try:
                exec(_FLOWYML_AUTO_IMPORTS, self._namespace)  # noqa: S102
            except ImportError as e:
                logger.warning(f"Some auto-imports failed: {e}")
            self._initialized = True

    def execute_cell(self, cell: Cell) -> ExecutionResult:
        """Execute a single cell and capture output.

        Args:
            cell: Cell to execute.

        Returns:
            ExecutionResult with outputs and error info.
        """
        import time
        import resource

        self._ensure_kernel()
        start = time.time()
        cpu_start = time.process_time()
        mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        outputs: list[CellOutput] = []
        error: str | None = None
        success = True

        if cell.cell_type == CellType.CODE:
            success, outputs, error = self._execute_code(cell.source)
        elif cell.cell_type == CellType.SQL:
            success, outputs, error = self._execute_sql(cell.source)
        elif cell.cell_type == CellType.MARKDOWN:
            outputs.append(CellOutput(output_type="html", data=cell.source))

        duration = time.time() - start
        cpu_time = time.process_time() - cpu_start
        mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS reports bytes, Linux reports KB
        import sys
        divisor = 1024 * 1024 if sys.platform == 'darwin' else 1024
        memory_delta = (mem_after - mem_before) / divisor
        peak_memory = mem_after / divisor
        cell.execution_count += 1
        cell.last_executed = datetime.now().isoformat()
        cell.outputs = outputs

        # Determine which variables were defined
        vars_defined = list(self._namespace.keys()) if success else []

        return ExecutionResult(
            cell_id=cell.id,
            success=success,
            outputs=outputs,
            error=error,
            duration_seconds=duration,
            memory_delta_mb=round(memory_delta, 2),
            cpu_time_s=round(cpu_time, 4),
            peak_memory_mb=round(peak_memory, 1),
            variables_defined=vars_defined,
        )

    def _execute_code(self, source: str) -> tuple[bool, list[CellOutput], str | None]:
        """Execute Python code cell."""
        import io
        import sys
        import contextlib

        outputs: list[CellOutput] = []
        error: str | None = None
        success = True

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            if self._ip:
                # IPython execution — must redirect stdout/stderr manually
                # because IPython writes print() to sys.stdout, NOT to result.stdout
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture

                try:
                    result = self._ip.run_cell(source, silent=False)
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr

                if result.error_in_exec:
                    success = False
                    error = str(result.error_in_exec)
                    outputs.append(CellOutput(output_type="error", data=error))
                elif result.error_before_exec:
                    success = False
                    error = str(result.error_before_exec)
                    outputs.append(CellOutput(output_type="error", data=error))
                else:
                    # Capture stdout (print output)
                    stdout_val = stdout_capture.getvalue()
                    if stdout_val:
                        outputs.append(CellOutput(output_type="text", data=stdout_val))

                    # Capture the cell's return value (last expression)
                    if result.result is not None:
                        output = self._format_result(result.result)
                        outputs.append(output)

                # Always capture stderr (warnings etc.)
                stderr_val = stderr_capture.getvalue()
                if stderr_val:
                    outputs.append(CellOutput(output_type="text", data=stderr_val))

            else:
                # Plain exec fallback
                with contextlib.redirect_stdout(stdout_capture), \
                     contextlib.redirect_stderr(stderr_capture):
                    exec(source, self._namespace)  # noqa: S102

                stdout_val = stdout_capture.getvalue()
                if stdout_val:
                    outputs.append(CellOutput(output_type="text", data=stdout_val))

                stderr_val = stderr_capture.getvalue()
                if stderr_val:
                    outputs.append(CellOutput(output_type="text", data=stderr_val))

        except Exception as e:
            import traceback

            success = False
            error = traceback.format_exc()
            outputs.append(CellOutput(output_type="error", data=error))

        return success, outputs, error

    def _execute_sql(self, source: str) -> tuple[bool, list[CellOutput], str | None]:
        """Execute SQL cell and bind result to DataFrame variable."""
        outputs: list[CellOutput] = []
        error: str | None = None
        success = True

        try:
            # Try to use the SQL engine if available
            from flowyml_notebook.sql.engine import execute_sql

            df, result_info = execute_sql(source, self._namespace)
            # Bind result to 'df' variable in namespace (or custom variable)
            self._namespace["df"] = df
            outputs.append(
                CellOutput(
                    output_type="dataframe",
                    data=df.to_dict("records") if hasattr(df, "to_dict") else str(df),
                    metadata={"rows": len(df), "columns": list(df.columns) if hasattr(df, "columns") else []},
                )
            )
        except ImportError:
            success = False
            error = "SQL engine not available. Install with: pip install 'flowyml-notebook[sql]'"
            outputs.append(CellOutput(output_type="error", data=error))
        except Exception as e:
            import traceback

            success = False
            error = traceback.format_exc()
            outputs.append(CellOutput(output_type="error", data=error))

        return success, outputs, error

    def _format_result(self, result: Any) -> CellOutput:
        """Format a cell result into a CellOutput based on its type."""
        try:
            import pandas as pd

            if isinstance(result, pd.DataFrame):
                # Build column-level statistics for auto-exploration
                col_stats = {}
                histograms = {}
                for col in result.columns:
                    series = result[col].dropna()
                    if pd.api.types.is_numeric_dtype(series):
                        desc = series.describe()
                        col_stats[col] = {
                            "type": "numeric",
                            "count": int(desc.get("count", 0)),
                            "mean": round(float(desc.get("mean", 0)), 4),
                            "std": round(float(desc.get("std", 0)), 4),
                            "min": round(float(desc.get("min", 0)), 4),
                            "q25": round(float(desc.get("25%", 0)), 4),
                            "median": round(float(desc.get("50%", 0)), 4),
                            "q75": round(float(desc.get("75%", 0)), 4),
                            "max": round(float(desc.get("max", 0)), 4),
                            "null_count": int(result[col].isna().sum()),
                        }
                        # Histogram bins (max 20 bins for frontend rendering)
                        try:
                            import numpy as np
                            counts, bin_edges = np.histogram(series, bins=min(20, max(5, len(series) // 10)))
                            histograms[col] = {
                                "counts": counts.tolist(),
                                "bin_edges": [round(float(e), 4) for e in bin_edges],
                            }
                        except Exception:
                            pass
                    else:
                        try:
                            vc = series.value_counts()
                            col_stats[col] = {
                                "type": "categorical",
                                "count": int(len(series)),
                                "unique": int(series.nunique()),
                                "top_values": {str(k): int(v) for k, v in vc.head(8).items()},
                                "null_count": int(result[col].isna().sum()),
                            }
                        except (TypeError, ValueError):
                            # Columns with unhashable types (lists, dicts, etc.)
                            col_stats[col] = {
                                "type": "object",
                                "count": int(len(series)),
                                "unique": None,
                                "top_values": {},
                                "null_count": int(result[col].isna().sum()),
                            }

                # Find variable name in namespace
                var_name = None
                for k, v in self._namespace.items():
                    if v is result and not k.startswith("_"):
                        var_name = k
                        break

                # Safely serialize DataFrame rows — convert unhashable types to strings
                safe_df = result.head(100).copy()
                for col in safe_df.columns:
                    if safe_df[col].dtype == object:
                        try:
                            safe_df[col].apply(hash)  # test hashability
                        except (TypeError, ValueError):
                            safe_df[col] = safe_df[col].apply(lambda x: str(x) if x is not None else None)

                return CellOutput(
                    output_type="dataframe",
                    data=safe_df.to_dict("records"),
                    metadata={
                        "rows": len(result),
                        "columns": list(result.columns),
                        "dtypes": {col: str(dt) for col, dt in result.dtypes.items()},
                        "shape": list(result.shape),
                        "stats": col_stats,
                        "histograms": histograms,
                        "variable_name": var_name,
                    },
                )
        except ImportError:
            pass

        # Check for FlowyML asset types
        if hasattr(result, "__class__") and result.__class__.__module__.startswith("flowyml"):
            return CellOutput(
                output_type="asset",
                data=repr(result),
                metadata={"type": result.__class__.__name__},
            )

        # Check for dict/list (render as JSON)
        if isinstance(result, (dict, list)):
            import json

            try:
                return CellOutput(output_type="json", data=json.dumps(result, indent=2, default=str))
            except (TypeError, ValueError):
                pass

        # Default: text representation
        return CellOutput(output_type="text", data=repr(result))

    def get_variable(self, name: str) -> Any:
        """Get a variable from the namespace."""
        return self._namespace.get(name)

    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable in the namespace."""
        self._namespace[name] = value

    def get_variables(self) -> dict[str, dict]:
        """Get all user-defined variables with type info."""
        skip = {"__builtins__", "__name__", "__doc__", "__package__",
                "__loader__", "__spec__", "In", "Out", "get_ipython",
                "exit", "quit", "_", "__", "___"}
        result = {}
        for name, value in self._namespace.items():
            if name.startswith("_") and name not in ("_",):
                continue
            if name in skip:
                continue
            try:
                result[name] = {
                    "type": type(value).__name__,
                    "repr": repr(value)[:200],
                    "module": type(value).__module__,
                }
                # Add shape for array-like objects
                if hasattr(value, "shape"):
                    result[name]["shape"] = list(value.shape)
                if hasattr(value, "__len__"):
                    result[name]["length"] = len(value)
            except Exception:
                result[name] = {"type": "unknown", "repr": "<unrepresentable>"}
        return result

    def reset(self) -> None:
        """Reset the kernel namespace."""
        if self._ip:
            self._ip.reset(new_session=True)
            self._ip.run_cell(_FLOWYML_AUTO_IMPORTS, silent=True)
            self._namespace = self._ip.user_ns
        else:
            self._namespace.clear()
            self._namespace["__builtins__"] = __builtins__
            try:
                exec(_FLOWYML_AUTO_IMPORTS, self._namespace)  # noqa: S102
            except ImportError:
                pass


class Notebook:
    """Main FlowyML Notebook — reactive, production-grade notebook engine.

    Usage:
        nb = Notebook("my_analysis", server="https://flowyml.company.com")
        nb.cell("dataset = Dataset.from_csv('data.csv')")
        nb.cell("model = train(dataset)")
        nb.run()
        nb.schedule(cron="0 2 * * *")
    """

    def __init__(
        self,
        name: str = "untitled",
        server: str | None = None,
        file_path: str | None = None,
    ):
        self.notebook = NotebookFile(
            metadata=NotebookMetadata(name=name, server=server or "")
        )
        self.session = NotebookSession()
        self.graph = ReactiveGraph()
        self.file_path = file_path
        self._connection = None

        # Load from file if provided
        if file_path and Path(file_path).exists():
            self.load(file_path)

    @property
    def name(self) -> str:
        return self.notebook.metadata.name

    @property
    def cells(self) -> list[Cell]:
        return self.notebook.cells

    def cell(self, source: str, cell_type: CellType = CellType.CODE, name: str = "") -> Cell:
        """Add a new cell to the notebook.

        Args:
            source: Cell source code.
            cell_type: Type of cell (code, markdown, sql).
            name: Optional display name.

        Returns:
            The created Cell object.
        """
        new_cell = self.notebook.add_cell(source=source, cell_type=cell_type, name=name)

        # Update reactive graph
        if cell_type == CellType.CODE:
            self.graph.update_cell(new_cell.id, source)

        return new_cell

    def update_cell(self, cell_id: str, source: str) -> set[str]:
        """Update a cell's source and get IDs of cells that need re-execution.

        Args:
            cell_id: Cell to update.
            source: New source code.

        Returns:
            Set of stale cell IDs.
        """
        cell = self.notebook.get_cell(cell_id)
        if not cell:
            raise ValueError(f"Cell {cell_id} not found")

        cell.source = source

        if cell.cell_type == CellType.CODE:
            stale = self.graph.update_cell(cell_id, source)
            return stale

        return set()

    def execute_cell(self, cell_id: str) -> ExecutionResult:
        """Execute a single cell.

        Args:
            cell_id: Cell to execute.

        Returns:
            ExecutionResult with outputs.
        """
        cell = self.notebook.get_cell(cell_id)
        if not cell:
            raise ValueError(f"Cell {cell_id} not found")

        self.graph.set_cell_state(cell_id, CellState.RUNNING)
        result = self.session.execute_cell(cell)

        if result.success:
            self.graph.set_cell_state(cell_id, CellState.SUCCESS)
        else:
            self.graph.set_cell_state(cell_id, CellState.ERROR)

        return result

    def execute_cell_reactive(self, cell_id: str) -> list[ExecutionResult]:
        """Execute a cell and all its stale downstream dependencies.

        This is the core reactive execution model: when you run a cell,
        all cells that depend on it are automatically re-executed in
        topological order. Handles diamond dependencies correctly via
        deduplication.

        Args:
            cell_id: Cell to execute.

        Returns:
            List of ExecutionResults for all executed cells.
        """
        results: list[ExecutionResult] = []
        executed: set[str] = set()  # Deduplication for diamond dependencies

        # Execute the target cell
        result = self.execute_cell(cell_id)
        results.append(result)
        executed.add(cell_id)

        if not result.success:
            return results  # Don't cascade on error

        # Find and execute ALL transitively downstream cells
        stale = self.graph.update_cell(cell_id, self.notebook.get_cell(cell_id).source)
        if stale:
            execution_order = self.graph.get_execution_order(stale)
            for downstream_id in execution_order:
                # Skip already-executed cells (deduplication for diamond deps)
                if downstream_id in executed:
                    continue
                downstream_result = self.execute_cell(downstream_id)
                results.append(downstream_result)
                executed.add(downstream_id)

                # Update graph for this cell too (it may have changed)
                downstream_cell = self.notebook.get_cell(downstream_id)
                if downstream_cell and downstream_cell.cell_type == CellType.CODE:
                    self.graph.update_cell(downstream_id, downstream_cell.source)

                if not downstream_result.success:
                    # Mark remaining downstream as stale instead of executing
                    for remaining_id in execution_order:
                        if remaining_id not in executed:
                            self.graph.set_cell_state(remaining_id, CellState.STALE)
                    break

        # Clear stale state for all successfully executed cells
        for rid in executed:
            self.graph.set_cell_state(rid, CellState.SUCCESS)

        return results

    def run(self) -> list[ExecutionResult]:
        """Execute all cells in dependency-safe order.

        Returns:
            List of ExecutionResults for all cells.
        """
        all_cell_ids = {cell.id for cell in self.notebook.cells if cell.cell_type == CellType.CODE}
        execution_order = self.graph.get_execution_order(all_cell_ids)

        # Include non-code cells in order (markdown, SQL)
        ordered_ids = []
        code_idx = 0
        for cell in self.notebook.cells:
            if cell.cell_type == CellType.CODE and cell.id in all_cell_ids:
                # Insert in topological order
                while code_idx < len(execution_order):
                    ordered_ids.append(execution_order[code_idx])
                    code_idx += 1
                    if execution_order[code_idx - 1] == cell.id:
                        break
            else:
                ordered_ids.append(cell.id)

        # Add any remaining code cells
        while code_idx < len(execution_order):
            if execution_order[code_idx] not in ordered_ids:
                ordered_ids.append(execution_order[code_idx])
            code_idx += 1

        results = []
        for cell_id in ordered_ids:
            result = self.execute_cell(cell_id)
            results.append(result)
            if not result.success and self.notebook.get_cell(cell_id).cell_type == CellType.CODE:
                logger.warning(f"Cell {cell_id} failed, stopping execution")
                break

        return results

    def save(self, path: str | None = None) -> str:
        """Save notebook to .py file.

        Args:
            path: File path. Uses self.file_path or generates from name.

        Returns:
            Path to saved file.
        """
        save_path = path or self.file_path or f"{self.name}.py"
        content = serialize_notebook(self.notebook)
        Path(save_path).write_text(content, encoding="utf-8")
        self.file_path = save_path
        logger.info(f"Notebook saved to {save_path}")
        return save_path

    def load(self, path: str) -> None:
        """Load notebook from .py file.

        Args:
            path: Path to notebook .py file.
        """
        content = Path(path).read_text(encoding="utf-8")
        self.notebook = parse_notebook(content)
        self.file_path = path

        # Rebuild reactive graph
        for cell in self.notebook.cells:
            if cell.cell_type == CellType.CODE:
                self.graph.update_cell(cell.id, cell.source)

        logger.info(f"Notebook loaded from {path} ({len(self.notebook.cells)} cells)")

    def load_from_dict(self, data: dict) -> None:
        """Load notebook from a dictionary (JSON data).

        Args:
            data: Notebook data dict with 'metadata' and 'cells' keys.
        """
        meta = data.get("metadata", {})
        self.notebook.metadata.name = meta.get("name", "untitled")
        self.notebook.metadata.description = meta.get("description", "")
        self.notebook.metadata.server = meta.get("server", "")

        # Clear and rebuild cells
        self.notebook.cells.clear()
        self.graph = ReactiveGraph()

        for cell_data in data.get("cells", []):
            cell_type = CellType(cell_data.get("cell_type", "code"))
            new_cell = self.notebook.add_cell(
                source=cell_data.get("source", ""),
                cell_type=cell_type,
                name=cell_data.get("name", ""),
            )
            if cell_type == CellType.CODE:
                self.graph.update_cell(new_cell.id, new_cell.source)

        logger.info(f"Notebook loaded from dict ({len(self.notebook.cells)} cells)")

    def connect(self, server: str | None = None) -> None:
        """Connect to a centralized FlowyML server.

        Args:
            server: Server URL. Uses metadata.server if not provided.
        """
        from flowyml_notebook.connection import FlowyMLConnection

        url = server or self.notebook.metadata.server
        if not url:
            raise ValueError("No server URL provided. Use Notebook(server='...') or nb.connect('...')")

        self._connection = FlowyMLConnection(url)
        self._connection.connect()
        self.notebook.metadata.server = url

    def schedule(self, cron: str | None = None, interval_hours: int | None = None) -> dict:
        """Schedule this notebook as a production pipeline.

        Args:
            cron: Cron expression (e.g., "0 2 * * *" for daily at 2am).
            interval_hours: Run every N hours.

        Returns:
            Schedule info dict.
        """
        from flowyml_notebook.scheduler_bridge import schedule_notebook

        return schedule_notebook(self, cron=cron, interval_hours=interval_hours)

    def deploy(self, model_name: str, endpoint: str | None = None) -> dict:
        """Deploy a model from the notebook to FlowyML serving.

        Args:
            model_name: Name of the model variable in notebook namespace.
            endpoint: Optional endpoint name.

        Returns:
            Deployment info dict.
        """
        from flowyml_notebook.deployer import deploy_model

        model = self.session.get_variable(model_name)
        if model is None:
            raise ValueError(f"Variable '{model_name}' not found in notebook namespace")

        return deploy_model(model, endpoint=endpoint, connection=self._connection)

    def promote(self, output_path: str | None = None) -> str:
        """Export notebook as a clean production pipeline .py file.

        Args:
            output_path: Output file path.

        Returns:
            Path to exported pipeline file.
        """
        from flowyml_notebook.deployer import promote_to_pipeline

        return promote_to_pipeline(self.notebook, output_path)

    def report(self, format: str = "html", output_path: str | None = None) -> str:
        """Generate a report from this notebook.

        Args:
            format: Output format ("html", "pdf").
            output_path: Output file path.

        Returns:
            Path to generated report.
        """
        from flowyml_notebook.reporting import generate_report

        return generate_report(self.notebook, format=format, output_path=output_path)

    def get_state(self) -> dict:
        """Get complete notebook state for the GUI.

        Returns:
            Dict with cells, graph, variables, and metadata.
        """
        return {
            "notebook": self.notebook.to_dict(),
            "graph": self.graph.to_dict(),
            "variables": self.session.get_variables(),
            "session_id": self.session.session_id,
            "connected": self._connection is not None,
            "server": self.notebook.metadata.server,
        }

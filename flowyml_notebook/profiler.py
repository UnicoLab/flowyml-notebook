"""Cell-level execution profiler for FlowyML Notebook.

Provides wall-clock timing, CPU timing, memory tracking via tracemalloc,
and function-level profiling via cProfile for individual notebook cells.
"""

from __future__ import annotations

import cProfile
import io
import logging
import pstats
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from flowyml_notebook.cells import CellOutput

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ProfileResult:
    """Aggregated profiling result for a single cell execution."""

    cell_id: str
    wall_time_s: float
    cpu_time_s: float
    memory_delta_mb: float
    peak_memory_mb: float
    function_calls: int
    top_functions: list[dict[str, Any]] = field(default_factory=list)
    top_allocations: list[dict[str, Any]] = field(default_factory=list)
    line_times: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "cell_id": self.cell_id,
            "wall_time_s": self.wall_time_s,
            "cpu_time_s": self.cpu_time_s,
            "memory_delta_mb": self.memory_delta_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "function_calls": self.function_calls,
            "top_functions": self.top_functions,
            "top_allocations": self.top_allocations,
            "line_times": self.line_times,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Profiler
# ---------------------------------------------------------------------------


class CellProfiler:
    """Profile individual cell executions and maintain a history of results."""

    def __init__(self, max_history: int = 1000) -> None:
        self._max_history = max_history
        self._history: list[ProfileResult] = []

    # -- public API --------------------------------------------------------

    def profile(
        self,
        cell_id: str,
        source: str,
        namespace: dict[str, Any] | None = None,
    ) -> ProfileResult:
        """Execute *source* under profiling and return a `ProfileResult`.

        Parameters
        ----------
        cell_id:
            Unique identifier for the cell being profiled.
        source:
            Python source code to execute.
        namespace:
            Optional globals dict for ``exec``.  A new dict is used when
            *None*.
        """
        ns = namespace if namespace is not None else {}

        # -- tracemalloc setup -----------------------------------------------
        tracemalloc_was_running = tracemalloc.is_tracing()
        try:
            if not tracemalloc_was_running:
                tracemalloc.start()
            snapshot_before = tracemalloc.take_snapshot()
            mem_before = tracemalloc.get_traced_memory()
        except Exception:
            logger.warning("Failed to initialise tracemalloc", exc_info=True)
            snapshot_before = None
            mem_before = (0, 0)

        # -- compile ---------------------------------------------------------
        try:
            code = compile(source, f"<cell:{cell_id}>", "exec")
        except SyntaxError as exc:
            if not tracemalloc_was_running:
                try:
                    tracemalloc.stop()
                except Exception:
                    pass
            return ProfileResult(
                cell_id=cell_id,
                wall_time_s=0.0,
                cpu_time_s=0.0,
                memory_delta_mb=0.0,
                peak_memory_mb=0.0,
                function_calls=0,
                top_functions=[],
                top_allocations=[],
                line_times=[{"error": f"SyntaxError: {exc}"}],
            )

        # -- cProfile --------------------------------------------------------
        profiler = cProfile.Profile()
        wall_start = time.perf_counter()
        cpu_start = time.process_time()
        exec_error = None

        try:
            profiler.enable()
            exec(code, ns)  # noqa: S102
        except Exception as exc:
            exec_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Profiler: cell %s raised during execution: %s", cell_id, exec_error)
        finally:
            profiler.disable()

        wall_end = time.perf_counter()
        cpu_end = time.process_time()

        wall_time_s = wall_end - wall_start
        cpu_time_s = cpu_end - cpu_start

        # -- parse cProfile stats -------------------------------------------
        top_functions: list[dict[str, Any]] = []
        function_calls = 0
        try:
            stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stream)
            stats.sort_stats("cumulative")
            function_calls = stats.total_calls
            # stats.stats is dict[(file, line, name) -> (cc, nc, tt, ct, callers)]
            entries = sorted(
                stats.stats.items(),
                key=lambda item: item[1][3],  # cumulative time
                reverse=True,
            )
            for (file, line, name), (cc, nc, tt, ct, _callers) in entries[:20]:
                per_call = ct / nc if nc else 0.0
                top_functions.append(
                    {
                        "name": f"{file}:{line}({name})",
                        "calls": nc,
                        "total_time": round(tt, 6),
                        "cumulative_time": round(ct, 6),
                        "per_call": round(per_call, 6),
                    }
                )
        except Exception:
            logger.warning("Failed to parse cProfile stats", exc_info=True)

        # -- parse tracemalloc snapshot -------------------------------------
        top_allocations: list[dict[str, Any]] = []
        memory_delta_mb = 0.0
        peak_memory_mb = 0.0
        try:
            snapshot_after = tracemalloc.take_snapshot()
            mem_after = tracemalloc.get_traced_memory()

            memory_delta_mb = (mem_after[0] - mem_before[0]) / (1024 * 1024)
            peak_memory_mb = mem_after[1] / (1024 * 1024)

            top_stats = (
                snapshot_after.compare_to(snapshot_before, "lineno") if snapshot_before else []
            )
            for stat in top_stats[:20]:
                frame = stat.traceback[0] if stat.traceback else None
                top_allocations.append(
                    {
                        "file": frame.filename if frame else "<unknown>",
                        "line": frame.lineno if frame else 0,
                        "size_kb": round(stat.size / 1024, 2),
                    }
                )
        except Exception:
            logger.warning("Failed to collect tracemalloc data", exc_info=True)
        finally:
            if not tracemalloc_was_running:
                try:
                    tracemalloc.stop()
                except Exception:
                    pass

        # -- assemble result ------------------------------------------------
        result = ProfileResult(
            cell_id=cell_id,
            wall_time_s=round(wall_time_s, 6),
            cpu_time_s=round(cpu_time_s, 6),
            memory_delta_mb=round(memory_delta_mb, 4),
            peak_memory_mb=round(peak_memory_mb, 4),
            function_calls=function_calls,
            top_functions=top_functions,
            top_allocations=top_allocations,
            line_times=[{"error": exec_error}] if exec_error else [],
        )

        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        return result

    # -- history helpers ---------------------------------------------------

    @property
    def history(self) -> list[ProfileResult]:
        """Return a copy of the full profiling history."""
        return list(self._history)

    def get_history_for_cell(self, cell_id: str) -> list[ProfileResult]:
        """Return profiling history entries for a specific *cell_id*."""
        return [r for r in self._history if r.cell_id == cell_id]

    def clear_history(self) -> None:
        """Remove all stored profiling results."""
        self._history.clear()


# ---------------------------------------------------------------------------
# Rich HTML output
# ---------------------------------------------------------------------------


def _badge(value: float, thresholds: tuple[float, float] = (0.1, 1.0)) -> str:
    """Return an inline badge span coloured by *value* vs *thresholds*."""
    fast, slow = thresholds
    if value <= fast:
        bg, fg = "#22c55e", "#052e16"
    elif value <= slow:
        bg, fg = "#eab308", "#422006"
    else:
        bg, fg = "#ef4444", "#450a0a"
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'background:{bg};color:{fg};font-weight:600;font-size:0.85em;">'
        f"{value:.4f}</span>"
    )


def _mem_badge(value: float) -> str:
    """Badge for memory values (MB)."""
    if value <= 1.0:
        bg, fg = "#22c55e", "#052e16"
    elif value <= 50.0:
        bg, fg = "#eab308", "#422006"
    else:
        bg, fg = "#ef4444", "#450a0a"
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'background:{bg};color:{fg};font-weight:600;font-size:0.85em;">'
        f"{value:.4f} MB</span>"
    )


def format_profile_output(result: ProfileResult) -> CellOutput:
    """Format a `ProfileResult` into a rich dark-themed HTML `CellOutput`."""

    # -- Summary section ----------------------------------------------------
    summary_html = f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
                gap:12px;margin-bottom:20px;">
      <div style="background:#334155;padding:12px 16px;border-radius:8px;">
        <div style="font-size:0.75em;color:#94a3b8;text-transform:uppercase;
                    letter-spacing:0.05em;margin-bottom:4px;">Wall Time</div>
        <div>{_badge(result.wall_time_s)} s</div>
      </div>
      <div style="background:#334155;padding:12px 16px;border-radius:8px;">
        <div style="font-size:0.75em;color:#94a3b8;text-transform:uppercase;
                    letter-spacing:0.05em;margin-bottom:4px;">CPU Time</div>
        <div>{_badge(result.cpu_time_s)} s</div>
      </div>
      <div style="background:#334155;padding:12px 16px;border-radius:8px;">
        <div style="font-size:0.75em;color:#94a3b8;text-transform:uppercase;
                    letter-spacing:0.05em;margin-bottom:4px;">Memory Delta</div>
        <div>{_mem_badge(result.memory_delta_mb)}</div>
      </div>
      <div style="background:#334155;padding:12px 16px;border-radius:8px;">
        <div style="font-size:0.75em;color:#94a3b8;text-transform:uppercase;
                    letter-spacing:0.05em;margin-bottom:4px;">Peak Memory</div>
        <div>{_mem_badge(result.peak_memory_mb)}</div>
      </div>
      <div style="background:#334155;padding:12px 16px;border-radius:8px;">
        <div style="font-size:0.75em;color:#94a3b8;text-transform:uppercase;
                    letter-spacing:0.05em;margin-bottom:4px;">Function Calls</div>
        <div style="font-size:1.1em;font-weight:700;color:#e2e8f0;">
          {result.function_calls:,}
        </div>
      </div>
    </div>
    """

    # -- Top functions table ------------------------------------------------
    fn_rows = ""
    for i, fn in enumerate(result.top_functions):
        row_bg = "#263548" if i % 2 else "#1e293b"
        fn_rows += (
            f'<tr style="background:{row_bg};">'
            f'<td style="padding:6px 10px;border-bottom:1px solid #334155;'
            f'max-width:360px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
            f"{fn['name']}</td>"
            f'<td style="padding:6px 10px;border-bottom:1px solid #334155;text-align:right;">'
            f"{fn['calls']}</td>"
            f'<td style="padding:6px 10px;border-bottom:1px solid #334155;text-align:right;">'
            f"{fn['total_time']:.6f}</td>"
            f'<td style="padding:6px 10px;border-bottom:1px solid #334155;text-align:right;">'
            f"{fn['cumulative_time']:.6f}</td>"
            f'<td style="padding:6px 10px;border-bottom:1px solid #334155;text-align:right;">'
            f"{fn['per_call']:.6f}</td>"
            f"</tr>"
        )

    functions_table = f"""
    <div style="margin-bottom:20px;">
      <h3 style="margin:0 0 8px;font-size:0.95em;color:#94a3b8;
                 text-transform:uppercase;letter-spacing:0.05em;">
        Top Functions (by cumulative time)
      </h3>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:0.85em;">
          <thead>
            <tr style="background:#334155;">
              <th style="padding:8px 10px;text-align:left;color:#cbd5e1;
                         border-bottom:2px solid #475569;">Function</th>
              <th style="padding:8px 10px;text-align:right;color:#cbd5e1;
                         border-bottom:2px solid #475569;">Calls</th>
              <th style="padding:8px 10px;text-align:right;color:#cbd5e1;
                         border-bottom:2px solid #475569;">Total(s)</th>
              <th style="padding:8px 10px;text-align:right;color:#cbd5e1;
                         border-bottom:2px solid #475569;">Cumul(s)</th>
              <th style="padding:8px 10px;text-align:right;color:#cbd5e1;
                         border-bottom:2px solid #475569;">Per Call(s)</th>
            </tr>
          </thead>
          <tbody>{fn_rows}</tbody>
        </table>
      </div>
    </div>
    """

    # -- Top allocations table ----------------------------------------------
    alloc_rows = ""
    for i, alloc in enumerate(result.top_allocations):
        row_bg = "#263548" if i % 2 else "#1e293b"
        alloc_rows += (
            f'<tr style="background:{row_bg};">'
            f'<td style="padding:6px 10px;border-bottom:1px solid #334155;'
            f'max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
            f"{alloc['file']}:{alloc['line']}</td>"
            f'<td style="padding:6px 10px;border-bottom:1px solid #334155;text-align:right;">'
            f"{alloc['size_kb']:.2f}</td>"
            f"</tr>"
        )

    allocations_table = f"""
    <div style="margin-bottom:10px;">
      <h3 style="margin:0 0 8px;font-size:0.95em;color:#94a3b8;
                 text-transform:uppercase;letter-spacing:0.05em;">
        Top Memory Allocations
      </h3>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:0.85em;">
          <thead>
            <tr style="background:#334155;">
              <th style="padding:8px 10px;text-align:left;color:#cbd5e1;
                         border-bottom:2px solid #475569;">File:Line</th>
              <th style="padding:8px 10px;text-align:right;color:#cbd5e1;
                         border-bottom:2px solid #475569;">Size(KB)</th>
            </tr>
          </thead>
          <tbody>{alloc_rows}</tbody>
        </table>
      </div>
    </div>
    """

    # -- Full HTML ----------------------------------------------------------
    html = f"""
    <div style="background:#1e293b;color:#e2e8f0;padding:20px 24px;
                border-radius:12px;font-family:'JetBrains Mono','Fira Code',monospace;
                line-height:1.6;">
      <h2 style="margin:0 0 16px;font-size:1.1em;color:#f8fafc;
                 border-bottom:1px solid #334155;padding-bottom:10px;">
        &#9201; Profile &mdash; <code style="color:#38bdf8;">{result.cell_id}</code>
        <span style="float:right;font-size:0.7em;color:#64748b;font-weight:400;">
          {result.timestamp}
        </span>
      </h2>
      {summary_html}
      {functions_table}
      {allocations_table}
    </div>
    """

    return CellOutput(
        output_type="html",
        data=html,
        metadata={"profile_cell_id": result.cell_id},
    )

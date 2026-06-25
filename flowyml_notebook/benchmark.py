"""Cell execution timing & benchmarking utilities.

Provides the `%%timeit` and `%%benchmark` magic equivalents for FlowyML cells,
plus execution time comparison across runs and performance regression detection.
"""

from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime

from flowyml_notebook.cells import CellOutput

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of benchmarking a cell over multiple runs."""

    cell_id: str
    runs: int = 0
    mean_s: float = 0.0
    median_s: float = 0.0
    std_s: float = 0.0
    min_s: float = 0.0
    max_s: float = 0.0
    all_times: list[float] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "runs": self.runs,
            "mean_s": round(self.mean_s, 6),
            "median_s": round(self.median_s, 6),
            "std_s": round(self.std_s, 6),
            "min_s": round(self.min_s, 6),
            "max_s": round(self.max_s, 6),
            "all_times": [round(t, 6) for t in self.all_times],
            "timestamp": self.timestamp,
        }


@dataclass
class PerformanceRegression:
    """Detected performance regression for a cell."""

    cell_id: str
    metric: str  # "wall_time", "memory"
    previous_value: float
    current_value: float
    change_pct: float
    severity: str  # "info", "warning", "critical"
    message: str

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "metric": self.metric,
            "previous": round(self.previous_value, 4),
            "current": round(self.current_value, 4),
            "change_pct": round(self.change_pct, 1),
            "severity": self.severity,
            "message": self.message,
        }


class CellBenchmark:
    """Benchmarks cell execution over multiple iterations with statistical analysis."""

    def __init__(self):
        self._history: dict[str, list[BenchmarkResult]] = {}

    def benchmark(
        self,
        cell_id: str,
        source: str,
        namespace: dict,
        runs: int = 7,
        warmup: int = 1,
    ) -> BenchmarkResult:
        """Benchmark a cell by running it multiple times.

        Args:
            cell_id: Cell identifier.
            source: Python source code.
            namespace: Execution namespace.
            runs: Number of timed runs.
            warmup: Number of warmup runs (not timed).

        Returns:
            BenchmarkResult with statistical summary.
        """
        try:
            compiled = compile(source, f"<cell:{cell_id}>", "exec")
        except SyntaxError:
            return BenchmarkResult(
                cell_id=cell_id,
                runs=0,
                mean_s=0.0,
                median_s=0.0,
                std_s=0.0,
                min_s=0.0,
                max_s=0.0,
                all_times=[],
            )

        # Warmup runs
        for _ in range(warmup):
            try:
                exec(compiled, namespace)  # noqa: S102
            except Exception:
                break

        # Timed runs
        times = []
        for _ in range(runs):
            try:
                start = time.perf_counter()
                exec(compiled, namespace)  # noqa: S102
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            except Exception:
                continue

        result = BenchmarkResult(
            cell_id=cell_id,
            runs=runs,
            mean_s=statistics.mean(times) if times else 0.0,
            median_s=statistics.median(times) if times else 0.0,
            std_s=statistics.stdev(times) if len(times) > 1 else 0.0,
            min_s=min(times) if times else 0.0,
            max_s=max(times) if times else 0.0,
            all_times=times,
        )

        if cell_id not in self._history:
            self._history[cell_id] = []
        self._history[cell_id].append(result)

        return result

    def detect_regressions(
        self,
        cell_id: str,
        threshold_pct: float = 25.0,
    ) -> list[PerformanceRegression]:
        """Detect performance regressions by comparing recent benchmarks.

        Args:
            cell_id: Cell to check.
            threshold_pct: Percentage increase to flag as regression.

        Returns:
            List of detected regressions.
        """
        history = self._history.get(cell_id, [])
        if len(history) < 2:
            return []

        prev = history[-2]
        curr = history[-1]
        regressions = []

        # Wall time regression
        if prev.mean_s > 0:
            change_pct = ((curr.mean_s - prev.mean_s) / prev.mean_s) * 100
            if change_pct > threshold_pct:
                severity = "critical" if change_pct > 100 else "warning"
                regressions.append(
                    PerformanceRegression(
                        cell_id=cell_id,
                        metric="wall_time",
                        previous_value=prev.mean_s,
                        current_value=curr.mean_s,
                        change_pct=change_pct,
                        severity=severity,
                        message=f"Cell {cell_id} is {change_pct:.0f}% slower ({prev.mean_s:.4f}s → {curr.mean_s:.4f}s)",
                    )
                )

        return regressions

    def get_history(self, cell_id: str) -> list[dict]:
        """Get benchmark history for a cell."""
        return [r.to_dict() for r in self._history.get(cell_id, [])]

    def clear(self) -> None:
        """Clear all benchmark history."""
        self._history.clear()


def format_benchmark_output(result: BenchmarkResult) -> CellOutput:
    """Format benchmark result as rich HTML for the GUI."""
    # Sparkline-style bars for individual run times
    max_time = max(result.all_times) if result.all_times else 1
    bars = ""
    for t in result.all_times:
        height = max(4, int(40 * t / max_time))
        color = (
            "#22c55e"
            if t <= result.median_s * 1.1
            else "#eab308"
            if t <= result.median_s * 1.5
            else "#ef4444"
        )
        bars += (
            f'<div style="width:12px;height:{height}px;background:{color};border-radius:2px"></div>'
        )

    html = (
        f'<div style="font-family:monospace;font-size:0.8rem;padding:12px;'
        f'background:#1e293b;border-radius:8px;border:1px solid rgba(255,255,255,0.06)">'
        f'<div style="color:#94a3b8;font-size:0.65rem;text-transform:uppercase;'
        f'letter-spacing:0.05em;margin-bottom:8px">⏱ Benchmark ({result.runs} runs)</div>'
        f'<div style="display:flex;gap:24px;margin-bottom:12px">'
        f'<div><span style="color:#64748b">Mean:</span> '
        f'<span style="color:#22d3ee;font-weight:700">{result.mean_s * 1000:.2f}ms</span></div>'
        f'<div><span style="color:#64748b">Median:</span> '
        f'<span style="color:#a78bfa;font-weight:700">{result.median_s * 1000:.2f}ms</span></div>'
        f'<div><span style="color:#64748b">σ:</span> '
        f'<span style="color:#fbbf24;font-weight:700">{result.std_s * 1000:.2f}ms</span></div>'
        f'<div><span style="color:#64748b">Range:</span> '
        f'<span style="color:#34d399;font-weight:700">{result.min_s * 1000:.2f}–{result.max_s * 1000:.2f}ms</span></div>'
        f"</div>"
        f'<div style="display:flex;align-items:flex-end;gap:3px;height:44px">{bars}</div>'
        f"</div>"
    )

    return CellOutput(
        output_type="html",
        data=html,
        metadata={"benchmark": result.to_dict()},
    )

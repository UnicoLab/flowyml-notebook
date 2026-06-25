"""Cell execution history and time-travel debugging.

Provides the ability to inspect previous execution states,
restore cell outputs, and revert to previous variable values.
A "time machine" for notebook exploration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from flowyml_notebook.cells import CellOutput

logger = logging.getLogger(__name__)


@dataclass
class ExecutionSnapshot:
    """Snapshot of a cell's state at a point in time."""

    cell_id: str
    source: str
    outputs: list[dict] = field(default_factory=list)
    variables_changed: dict[str, str] = field(default_factory=dict)  # name → type repr
    execution_count: int = 0
    success: bool = True
    duration_s: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "source": self.source,
            "outputs": self.outputs,
            "variables_changed": self.variables_changed,
            "execution_count": self.execution_count,
            "success": self.success,
            "duration_s": round(self.duration_s, 4),
            "timestamp": self.timestamp,
        }


@dataclass
class CellTimeline:
    """Complete execution timeline for a single cell."""

    cell_id: str
    snapshots: list[ExecutionSnapshot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "total_executions": len(self.snapshots),
            "snapshots": [s.to_dict() for s in self.snapshots],
            "first_executed": self.snapshots[0].timestamp if self.snapshots else None,
            "last_executed": self.snapshots[-1].timestamp if self.snapshots else None,
        }


class ExecutionHistory:
    """Tracks the full execution history of all cells.

    Enables time-travel debugging: inspect what a cell produced
    at any point in time, compare outputs across runs, and
    detect when behavior changed.

    Usage:
        history = ExecutionHistory(max_snapshots=50)
        history.record(cell_id, source, outputs, variables_changed, success, duration)
        timeline = history.get_timeline(cell_id)
        diff = history.compare_runs(cell_id, run_a=0, run_b=-1)
    """

    def __init__(self, max_snapshots: int = 50):
        self._timelines: dict[str, CellTimeline] = {}
        self._global_log: list[ExecutionSnapshot] = []
        self._max_snapshots = max_snapshots

    def record(
        self,
        cell_id: str,
        source: str,
        outputs: list[CellOutput] | None = None,
        variables_changed: dict[str, str] | None = None,
        success: bool = True,
        duration_s: float = 0.0,
        execution_count: int = 0,
    ) -> ExecutionSnapshot:
        """Record a cell execution snapshot.

        Args:
            cell_id: The executed cell's ID.
            source: Source code at time of execution.
            outputs: Cell outputs.
            variables_changed: Variables modified, as {name: type_repr}.
            success: Whether execution succeeded.
            duration_s: Execution wall time.
            execution_count: The cell's execution counter.

        Returns:
            The recorded snapshot.
        """
        snapshot = ExecutionSnapshot(
            cell_id=cell_id,
            source=source,
            outputs=[o.to_dict() for o in (outputs or [])],
            variables_changed=variables_changed or {},
            execution_count=execution_count,
            success=success,
            duration_s=duration_s,
        )

        # Add to cell timeline
        if cell_id not in self._timelines:
            self._timelines[cell_id] = CellTimeline(cell_id=cell_id)

        timeline = self._timelines[cell_id]
        timeline.snapshots.append(snapshot)

        # Trim if over limit
        if len(timeline.snapshots) > self._max_snapshots:
            timeline.snapshots = timeline.snapshots[-self._max_snapshots :]

        # Add to global log
        self._global_log.append(snapshot)
        if len(self._global_log) > self._max_snapshots * 10:
            self._global_log = self._global_log[-(self._max_snapshots * 5) :]

        return snapshot

    def get_timeline(self, cell_id: str) -> dict | None:
        """Get the full execution timeline for a cell."""
        timeline = self._timelines.get(cell_id)
        return timeline.to_dict() if timeline else None

    def get_snapshot(self, cell_id: str, run_index: int = -1) -> dict | None:
        """Get a specific execution snapshot.

        Args:
            cell_id: Cell identifier.
            run_index: Index of the run (0 = first, -1 = last).

        Returns:
            Snapshot dict or None.
        """
        timeline = self._timelines.get(cell_id)
        if not timeline or not timeline.snapshots:
            return None
        try:
            return timeline.snapshots[run_index].to_dict()
        except IndexError:
            return None

    def compare_runs(
        self,
        cell_id: str,
        run_a: int = -2,
        run_b: int = -1,
    ) -> dict | None:
        """Compare two execution runs of the same cell.

        Args:
            cell_id: Cell identifier.
            run_a: Index of the first run.
            run_b: Index of the second run.

        Returns:
            Dict with comparison details.
        """
        timeline = self._timelines.get(cell_id)
        if not timeline or len(timeline.snapshots) < 2:
            return None

        try:
            snap_a = timeline.snapshots[run_a]
            snap_b = timeline.snapshots[run_b]
        except IndexError:
            return None

        return {
            "cell_id": cell_id,
            "run_a": {"index": run_a, **snap_a.to_dict()},
            "run_b": {"index": run_b, **snap_b.to_dict()},
            "source_changed": snap_a.source != snap_b.source,
            "outputs_changed": snap_a.outputs != snap_b.outputs,
            "success_changed": snap_a.success != snap_b.success,
            "duration_delta_s": round(snap_b.duration_s - snap_a.duration_s, 4),
            "duration_change_pct": (
                round(
                    ((snap_b.duration_s - snap_a.duration_s) / max(snap_a.duration_s, 0.001)) * 100,
                    1,
                )
            ),
        }

    def get_global_log(self, limit: int = 50) -> list[dict]:
        """Get the most recent N executions across all cells."""
        return [s.to_dict() for s in self._global_log[-limit:]]

    def get_all_timelines(self) -> dict[str, dict]:
        """Get timelines for all cells."""
        return {cell_id: timeline.to_dict() for cell_id, timeline in self._timelines.items()}

    def get_execution_stats(self) -> dict:
        """Get aggregate execution statistics."""
        total_executions = sum(len(t.snapshots) for t in self._timelines.values())
        total_cells = len(self._timelines)
        failures = sum(1 for t in self._timelines.values() for s in t.snapshots if not s.success)
        total_time = sum(s.duration_s for t in self._timelines.values() for s in t.snapshots)

        return {
            "total_executions": total_executions,
            "total_cells_executed": total_cells,
            "total_failures": failures,
            "success_rate_pct": round(
                ((total_executions - failures) / max(1, total_executions)) * 100, 1
            ),
            "total_time_s": round(total_time, 2),
            "avg_time_per_cell_s": round(total_time / max(1, total_executions), 4),
            "most_executed_cell": max(
                self._timelines.items(),
                key=lambda x: len(x[1].snapshots),
                default=(None, None),
            )[0],
            "slowest_cell": max(
                (
                    (cell_id, t.snapshots[-1].duration_s)
                    for cell_id, t in self._timelines.items()
                    if t.snapshots
                ),
                key=lambda x: x[1],
                default=(None, 0),
            )[0],
        }

    def clear(self, cell_id: str | None = None) -> None:
        """Clear execution history.

        Args:
            cell_id: If provided, clear only that cell's history.
                     If None, clear everything.
        """
        if cell_id:
            self._timelines.pop(cell_id, None)
            self._global_log = [s for s in self._global_log if s.cell_id != cell_id]
        else:
            self._timelines.clear()
            self._global_log.clear()


def format_timeline_output(timeline: dict) -> CellOutput:
    """Format a cell timeline as rich HTML for the GUI."""
    snapshots = timeline.get("snapshots", [])
    total = timeline.get("total_executions", 0)

    html_parts = [
        '<div style="font-family:monospace;font-size:0.8rem;padding:12px;'
        'background:#1e293b;border-radius:8px;border:1px solid rgba(255,255,255,0.06)">',
        f'<div style="color:#94a3b8;font-size:0.65rem;text-transform:uppercase;'
        f'letter-spacing:0.05em;margin-bottom:8px">🕰 Execution History — '
        f"{total} runs</div>",
    ]

    # Show last 10 runs as a compact list
    recent = snapshots[-10:]
    for i, snap in enumerate(recent):
        icon = "✅" if snap.get("success") else "❌"
        time_str = snap.get("timestamp", "")[:19]
        duration = snap.get("duration_s", 0)
        exec_num = snap.get("execution_count", 0)

        html_parts.append(
            f'<div style="display:flex;gap:8px;padding:3px 0;'
            f'border-bottom:1px solid rgba(255,255,255,0.03)">'
            f'<span style="color:#64748b;min-width:24px">#{exec_num}</span>'
            f"<span>{icon}</span>"
            f'<span style="color:#94a3b8;flex:1">{time_str}</span>'
            f'<span style="color:#22d3ee">{duration * 1000:.1f}ms</span>'
            f"</div>"
        )

    html_parts.append("</div>")

    return CellOutput(
        output_type="html",
        data="".join(html_parts),
        metadata={"timeline": timeline},
    )
